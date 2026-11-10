import asyncio, json
from pathlib import Path
import pytest
from pydantic import ValidationError
from app.schemas.incident import IncidentCreate
from app.investigation.contracts import Decision,Proposal,ToolCall,Citation,NumericClaim
from app.investigation.settings import InvestigationSettings
from app.investigation.retrieval import KnowledgeStore,OperationalRetriever
from app.investigation.graph import Investigator,verify
from app.investigation.security import redact,safe_html
from app.investigation.analytics import collect,fallback
from app.core.cpp_bridge import cpp_bridge
from app.core.workflow import PlannerAgent

ROOT=Path(__file__).resolve().parents[1]
@pytest.fixture
def settings(tmp_path):
    return InvestigationSettings(database_url=f'sqlite:///{tmp_path}/jobs.db',knowledge_db=tmp_path/'kb.db',knowledge_dir=ROOT/'knowledge',max_duration=5,timeout_seconds=1)
@pytest.fixture
def incident():return IncidentCreate(description='Synthetic database incident',logs=['ERROR: Deadlock detected in database transaction'],metrics={'latency_ms':[100,3200]})
def retriever(s):
    store=KnowledgeStore(s.knowledge_db);store.index(s.knowledge_dir)
    return OperationalRetriever(store=store)
def proposal(context):
    h=context['hypotheses'][0]
    return Proposal(category=h['category'],supporting=h['supporting'],contradicting=h['contradicting'],missing=['timing'],uncertainty='high',citations=[{'chunk_id':c['id'],'evidence_ids':h['supporting']} for c in context['chunks'][:1]],numeric_claims=[],diagnostics=[{'action':'inspect_logs','action_type':'read_only','evidence_ids':h['supporting']}])
class FakeProvider:
    """Explicitly test-only. Never imported by production code."""
    label='fake_test_only'
    def __init__(self,behavior='valid'):self.calls=0;self.behavior=behavior
    async def decide(self,text):
        self.calls+=1;c=json.loads(text)
        if self.behavior=='timeout':await asyncio.sleep(10)
        if self.behavior=='failure':raise RuntimeError('synthetic rate limit')
        if self.behavior=='malformed' and self.calls==1:return {'unexpected':True},{}
        if self.behavior in ('tool','duplicate','cross','bad_tool') and (self.calls==1 or self.behavior in ('duplicate','bad_tool')):
            if self.behavior=='bad_tool':return {'tools':[{'name':'shell','incident_id':c['incident_id']}],'proposal':None},{}
            return Decision(tools=[ToolCall(name='get_log_evidence',incident_id='another' if self.behavior=='cross' else c['incident_id'])]),{}
        p=proposal(c)
        if self.behavior=='fabricated' or self.behavior=='repair' and self.calls==1:p.citations=[Citation(chunk_id='fabricated',evidence_ids=[])]
        return Decision(proposal=p),{'input_tokens':10,'output_tokens':10}

@pytest.mark.parametrize('value',[True,'12',{},[],[float('nan')],[1,'bad'],float('inf'),1e101])
def test_validation(value):
    with pytest.raises(ValidationError):IncidentCreate(description='x',metrics={'cpu':value})

def test_redaction_html():
    text='api_key=secretvalue Authorization: Bearer abc123 sk-abcdefghijklmnopqrst ghp_abcdefghijklmnop'
    redacted=redact(text)
    assert all(v not in redacted for v in ['secretvalue','abc123','sk-abcdefghijklmnopqrst','ghp_abcdefghijklmnop'])
    html=safe_html('<img src=x onerror=alert(1)> [bad](javascript:alert(1))')
    assert '<img' not in html and 'href="javascript:' not in html

def test_single_pass_and_fallback(incident):
    native,mode=cpp_bridge.analyze_incident(incident.logs,incident.metrics)
    assert mode=='native';py=fallback(incident.logs,incident.metrics)
    assert native['logs']['error_count']==py['logs']['error_count']
    assert native['correlation']['primary_category']==py['correlation']['primary_category']=='Database'
    assert native['metrics']['anomalies'][0]['peak_value']==3200
    assert cpp_bridge.analyze_incident([],{'error_rate':[1e-3,2e-3]})[0]['metrics']['anomalies']==[]
    assert cpp_bridge.analyze_incident([],{})[0]['logs']['total_logs']==0

@pytest.mark.asyncio
@pytest.mark.parametrize('behavior',['valid','tool','cross','repair','malformed'])
async def test_graph_success(settings,incident,behavior):
    incident.mode='llm';fake=FakeProvider(behavior)
    result=await Investigator(settings,cpp_bridge,retriever(settings),fake).run('test',incident)
    assert result.provider.calls<=settings.max_model_calls
    assert sum(t.stage=='revise' for t in result.trace)<=1
    if behavior in ('repair','malformed'):
        assert fake.calls==2
    assert result.proposal is not None, result.model_dump()
    assert result.verification.status=='passed'
    if behavior=='cross':assert any(t.outcome.endswith('rejected') for t in result.trace)

@pytest.mark.asyncio
@pytest.mark.parametrize('behavior',['failure','timeout','fabricated','duplicate','bad_tool'])
async def test_graph_fallback(settings,incident,behavior):
    incident.mode='llm';settings.timeout_seconds=.05
    result=await Investigator(settings,cpp_bridge,retriever(settings),FakeProvider(behavior)).run('test',incident)
    assert result.provider.active=='deterministic'
    assert result.verification.status=='fallback'
    assert result.provider.calls<=settings.max_model_calls
    assert result.provider.tool_calls<=settings.max_tool_calls
    assert sum(t.stage=='revise' for t in result.trace)<=1

def test_verifier(settings,incident):
    f,e,h=collect('one',incident,cpp_bridge);chunks=retriever(settings).chunks('database')
    p=proposal({'hypotheses':[x.model_dump() for x in h],'chunks':[x.model_dump() for x in chunks]})
    assert not verify(p,e,h,chunks,'one')
    p.supporting=['other:log:0'];assert verify(p,e,h,chunks,'one')
    p.supporting=h[0].supporting;p.numeric_claims=[NumericClaim(evidence_id=e[-1].id,field='peak',value=100)]
    assert 'Numeric claim differs from measured evidence' in verify(p,e,h,chunks,'one')

class FakeEmbeddings:
    """Deterministic test vectors exercise persistence/fusion, not semantic quality."""
    def __init__(self):self.calls=0
    def embed_documents(self,texts):self.calls+=1;return [self.embed_query(t) for t in texts]
    def embed_query(self,text):return [float('database' in text.lower()),float('memory' in text.lower()),1.]

def test_index_incremental_and_mismatch(tmp_path):
    root=tmp_path/'docs';root.mkdir();p=root/'db.md';p.write_text('# Database\nDeadlock database contention.')
    store=KnowledgeStore(tmp_path/'kb.db');embed=FakeEmbeddings()
    assert store.index(root,embed,'test',3)['embedded']==1
    assert store.index(root,embed,'test',3)['updated']==0
    chunks,mode=store.retrieve('database',embedder=embed,model='test',dimensions=3);assert chunks and mode=='hybrid'
    assert store.retrieve('database',embedder=embed,model='other',dimensions=3)[1]=='lexical_fallback_incompatible_index'
    p.write_text('# Database\nChanged database evidence.')
    assert store.index(root,embed,'test',3)['updated']==1
    p.unlink();assert store.index(root)['chunks']==0
    assert store.retrieve('database')==([],'unavailable')

@pytest.mark.asyncio
async def test_persistence_cancel_recovery(settings,incident):
    service=PlannerAgent(settings);job=await service.analyze(incident)
    assert job.status=='completed';identity=str(job.job_id)
    assert service.store.stages(identity)[-1]['stage']=='done'
    restarted=PlannerAgent(settings);assert restarted.get_status(identity).result.investigation.evidence
    restarted.store.create('interrupted-test',incident)
    again=PlannerAgent(settings);again.initialize()
    # Recovery is verified directly because the public job contract requires UUID IDs.
    from app.investigation.persistence import Job
    with again.store.sessions() as session:assert session.get(Job,'interrupted-test').status=='interrupted'
    slow=PlannerAgent(settings,FakeProvider('timeout'));incident.mode='llm';identity=await slow.start_analysis(incident)
    await slow.cancel(identity);assert slow.get_status(identity).status=='cancelled'
    await service.shutdown();await restarted.shutdown();await again.shutdown();await slow.shutdown()

@pytest.mark.asyncio
async def test_missing_credentials(settings,incident):
    settings.provider='disabled';incident.mode='llm'
    service=PlannerAgent(settings);result=await service.analyze(incident)
    assert result.status=='completed'
    assert result.result.investigation.verification.status=='fallback'
    await service.shutdown()

@pytest.mark.asyncio
async def test_all_read_only_tools(settings,incident):
    class ToolProvider(FakeProvider):
        async def decide(self,text):
            c=json.loads(text);self.calls+=1
            if self.calls==1:
                return Decision(tools=[ToolCall(name='get_metric_evidence',incident_id=c['incident_id']),ToolCall(name='get_rule_hypotheses',incident_id=c['incident_id']),ToolCall(name='search_runbooks',incident_id=c['incident_id'],query='database deadlock')]),{}
            if self.calls==2:
                return Decision(tools=[ToolCall(name='get_runbook_chunk',incident_id=c['incident_id'],reference_id=c['chunks'][0]['id'])]),{}
            return Decision(proposal=proposal(c)),{}
    incident.mode='llm'
    result=await Investigator(settings,cpp_bridge,retriever(settings),ToolProvider()).run('tools',incident)
    assert result.verification.status=='passed'
    assert result.provider.tool_calls==4
    assert len([t for t in result.trace if t.outcome.endswith('completed')])==4

@pytest.mark.asyncio
async def test_graph_duration_and_step_limits(settings,incident):
    incident.mode='llm';settings.max_duration=.05;settings.timeout_seconds=.04
    result=await Investigator(settings,cpp_bridge,retriever(settings),FakeProvider('timeout')).run('timeout',incident)
    assert result.provider.active=='deterministic'
    assert result.provider.elapsed_ms<1000
    settings.max_duration=5;settings.max_graph_steps=8
    result=await Investigator(settings,cpp_bridge,retriever(settings),FakeProvider('duplicate')).run('steps',incident)
    assert result.provider.active=='deterministic'
    assert len(result.trace)<20

def test_stale_index(tmp_path):
    root=tmp_path/'docs';root.mkdir();p=root/'runbook.md';p.write_text('# CPU\nCPU pressure')
    store=KnowledgeStore(tmp_path/'kb.db',root);store.index(root)
    p.write_text('# CPU\nChanged pressure')
    assert store.retrieve('cpu')[1].endswith('stale_documents')

def test_unsupported_claim_schema():
    with pytest.raises(ValidationError):Proposal.model_validate({'category':'CPU','supporting':[],'contradicting':[],'missing':[],'uncertainty':'high','citations':[],'numeric_claims':[],'diagnostics':[],'remediation_executed':True})

@pytest.mark.asyncio
async def test_queue_bound(settings,incident):
    settings.max_pending=1;service=PlannerAgent(settings,FakeProvider('timeout'));incident.mode='llm'
    identity=await service.start_analysis(incident)
    with pytest.raises(RuntimeError,match='queue'):await service.start_analysis(incident)
    await service.cancel(identity);await service.shutdown()

@pytest.mark.asyncio
async def test_full_python_fallback(settings,incident,monkeypatch):
    monkeypatch.setattr(cpp_bridge,'_is_native',False)
    service=PlannerAgent(settings);job=await service.analyze(incident)
    assert job.status=='completed'
    assert job.result.investigation.findings.engine=='python_fallback'
    assert job.result.root_cause.primary_category=='Database'
    await service.shutdown()

@pytest.mark.asyncio
async def test_service_analyzes_once(settings,incident,monkeypatch):
    original=cpp_bridge.analyze_incident;calls=[]
    def count(logs,metrics):calls.append(1);return original(logs,metrics)
    monkeypatch.setattr(cpp_bridge,'analyze_incident',count)
    service=PlannerAgent(settings);job=await service.analyze(incident)
    assert job.status=='completed';assert len(calls)==1
    await service.shutdown()

def test_nonfinite_proposal_and_huge_integer():
    with pytest.raises(ValidationError):NumericClaim(evidence_id='x',field='peak',value=float('nan'))
    with pytest.raises(ValidationError):IncidentCreate(description='x',metrics={'cpu':10**1000})
