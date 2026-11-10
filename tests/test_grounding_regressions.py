"""Regression coverage for indexing provenance, report grounding and graph boundaries."""
import asyncio
import json
import time
from pathlib import Path

import pytest

from app.core.cpp_bridge import cpp_bridge
from app.core.workflow import PlannerAgent
from app.investigation.analytics import collect
from app.investigation.contracts import Citation, Decision, Proposal, ToolCall
from app.investigation.graph import Investigator, verify
from app.investigation.report import report
from app.investigation.retrieval import KnowledgeStore, OperationalRetriever
from app.schemas.incident import IncidentCreate
from test_investigation import FakeEmbeddings, FakeProvider, incident, proposal, retriever, settings


class RecordingEmbeddings(FakeEmbeddings):
    def __init__(self):
        super().__init__()
        self.inputs = []

    def embed_documents(self, texts):
        self.inputs.extend(texts)
        return super().embed_documents(texts)


def indexed_rows(store):
    with store.connect() as db:
        return {r[0]: r for r in db.execute('SELECT * FROM chunks')}


def test_heading_body_version_deletion_and_vector_reuse(tmp_path):
    root = tmp_path / 'docs'
    root.mkdir()
    source = root / 'database.md'
    source.write_text('# Database\nOriginal body.\n## Timing\nUnchanged body.')
    store = KnowledgeStore(tmp_path / 'kb.db', root)
    embeddings = RecordingEmbeddings()
    assert store.index(root, embeddings, 'test', 3) == {'chunks': 2, 'updated': 2, 'embedded': 2}
    original = indexed_rows(store)
    assert store.index(root, embeddings, 'test', 3)['updated'] == 0
    assert len(embeddings.inputs) == 2

    source.write_text('# Database contention\nOriginal body.\n## Timing\nUnchanged body.')
    assert store.index(root, embeddings, 'test', 3) == {'chunks': 2, 'updated': 2, 'embedded': 1}
    heading_edit = indexed_rows(store)
    assert original.keys() == heading_edit.keys()
    assert embeddings.inputs[-1] == 'Database contention\nOriginal body.'
    for identity, row in heading_edit.items():
        assert row[4] != original[identity][4]  # whole-document version refreshed
        if row[3] == 'Timing':
            assert row[7:] == original[identity][7:]  # compatible vector retained
    assert not store.retrieve('contention')[1].endswith('stale_documents')

    source.write_text('# Database contention\nEdited body.\n## Timing\nUnchanged body.')
    assert store.index(root, embeddings, 'test', 3)['embedded'] == 1
    assert embeddings.inputs[-1] == 'Database contention\nEdited body.'
    unchanged = indexed_rows(store)
    assert store.index(root, embeddings, 'test', 3)['embedded'] == 0
    assert indexed_rows(store) == unchanged
    source.unlink()
    assert store.index(root, embeddings, 'test', 3)['chunks'] == 0
    assert indexed_rows(store) == {}


def test_lexical_refresh_invalidates_only_changed_embedding_input(tmp_path):
    root = tmp_path / 'docs'
    root.mkdir()
    source = root / 'cpu.md'
    source.write_text('# CPU\nObserve usage.\n## Timing\nCompare timestamps.')
    store = KnowledgeStore(tmp_path / 'kb.db')
    embeddings = RecordingEmbeddings()
    store.index(root, embeddings, 'test', 3)
    source.write_text('# CPU saturation\nObserve usage.\n## Timing\nCompare timestamps.')
    assert store.index(root)['embedded'] == 0
    rows = indexed_rows(store)
    assert next(r for r in rows.values() if r[3] == 'CPU saturation')[7:] == (None, None, None)
    assert next(r for r in rows.values() if r[3] == 'Timing')[7] is not None
    assert store.index(root, embeddings, 'test', 3)['embedded'] == 1
    assert store.index(root, embeddings, 'other-model', 3)['embedded'] == 2


@pytest.mark.parametrize('uncertainty,missing', [('low', ['timing']), ('moderate', ['timing']), ('high', [])])
def test_unknown_requires_high_uncertainty_and_missing_context(incident, uncertainty, missing):
    _, evidence, hypotheses = collect('one', incident, cpp_bridge)
    p = Proposal(category='Unknown', supporting=[], contradicting=[], missing=missing,
                 uncertainty=uncertainty, citations=[], numeric_claims=[], diagnostics=[])
    assert verify(p, evidence, hypotheses, [], 'one')


def test_verifier_support_ownership_citations_and_contradictions():
    incident = IncidentCreate(description='conflict', logs=['OutOfMemoryError'], metrics={'memory_usage': 20})
    _, evidence, hypotheses = collect('one', incident, cpp_bridge)
    base = proposal({'hypotheses': [h.model_dump() for h in hypotheses], 'chunks': []})
    assert not verify(base, evidence, hypotheses, [], 'one')
    for patch in [dict(category='Database'), dict(supporting=[]), dict(contradicting=[]),
                  dict(supporting=['another:log:0']), dict(citations=[Citation(chunk_id='another-chunk')]),
                  dict(citations=[Citation(chunk_id='fake', evidence_ids=['another:metric:0'])])]:
        assert verify(base.model_copy(update=patch), evidence, hypotheses, [], 'one')
    foreign = [e.model_copy(update={'incident_id': 'another'}) for e in evidence]
    assert verify(base, foreign, hypotheses, [], 'one')
    unknown = base.model_copy(update={'category': 'Unknown', 'supporting': [], 'uncertainty': 'high', 'missing': ['timing']})
    assert not verify(unknown, evidence, hypotheses, [], 'one')
    assert verify(unknown.model_copy(update={'contradicting': []}), evidence, hypotheses, [], 'one')


@pytest.mark.asyncio
@pytest.mark.parametrize('category,logs,metrics,phrase', [
    ('Database', ['Deadlock detected'], {'latency_ms': 3200}, 'blocking-query'),
    ('Memory', ['OutOfMemoryError'], {'memory_usage': 98}, 'memory'),
    ('Network', ['Connection timed out'], {'network_drop_rate': .1}, 'timeout'),
    ('Disk', [], {'disk_usage_percent': 94}, 'inode'),
    ('CPU', ['Thread pool exhausted'], {'cpu_usage': 95}, 'queue'),
])
async def test_incident_specific_deterministic_recommendations(settings, category, logs, metrics, phrase):
    KnowledgeStore(settings.knowledge_db).index(settings.knowledge_dir)
    service = PlannerAgent(settings)
    job = await service.analyze(IncidentCreate(description='misleading unrelated description', logs=logs, metrics=metrics))
    assert job.status == 'completed', job.error
    output = job.result
    assert output.root_cause.primary_category == category
    assert phrase in output.recommendations[0].description.lower()
    evidence_ids = {e.id for e in output.investigation.evidence}
    chunks = {c.id: c for c in output.investigation.chunks}
    for rec in output.recommendations:
        assert rec.evidence_ids and set(rec.evidence_ids) <= evidence_ids
        assert rec.prerequisites and rec.operational_impact
        assert not rec.is_safe and rec.action_type == 'read_only'
        for citation in rec.citations:
            assert citation.chunk_id in chunks
            assert chunks[citation.chunk_id].source == category.lower() + '.md'
            assert set(citation.evidence_ids) <= evidence_ids
    assert any(rec.citations for rec in output.recommendations)
    # All structured recommendations also reach the Markdown/HTML dashboard path.
    assert output.recommendations[0].action in output.summary_html
    assert 'Operational impact:' in output.summary
    if category == 'Disk':
        assert 'observed peak 94' in output.summary
        assert 'reached 100%' not in output.summary
    await service.shutdown()


@pytest.mark.asyncio
async def test_missing_or_irrelevant_runbooks_do_not_invent_citations(settings, incident):
    service = PlannerAgent(settings)
    job = await service.analyze(incident)
    assert job.status == 'completed'
    assert all(not r.citations for r in job.result.recommendations)
    assert 'No applicable retrieved runbook' in job.result.summary
    unrelated = settings.knowledge_db.parent / 'irrelevant-docs'
    unrelated.mkdir()
    (unrelated / 'cpu.md').write_text('# CPU diagnostics\nInspect CPU and latency metrics; profiling adds overhead.')
    KnowledgeStore(settings.knowledge_db).index(unrelated)
    irrelevant = await service.analyze(incident)
    assert irrelevant.result.investigation.chunks
    assert all(not r.citations for r in irrelevant.result.recommendations)
    empty = await service.analyze(IncidentCreate(description='unknown', logs=[], metrics={}))
    assert empty.result.root_cause.primary_category == 'Unknown'
    assert all(not r.evidence_ids and not r.citations for r in empty.result.recommendations)
    assert 'Collect discriminating telemetry' in empty.result.summary
    await service.shutdown()


class ScriptedProvider:
    label = 'fake_test_only'
    def __init__(self, actions):
        self.actions = actions
        self.contexts = []
    async def decide(self, text):
        self.contexts.append(text)
        action = self.actions[min(len(self.contexts)-1, len(self.actions)-1)]
        if isinstance(action, Exception):
            raise action
        return action(json.loads(text)), {}


def choose(category):
    def decision(context):
        h = next(h for h in context['hypotheses'] if h['category'] == category)
        return Decision(proposal=proposal({'hypotheses': [h], 'chunks': context['chunks']}))
    return decision


@pytest.mark.asyncio
async def test_report_follows_verified_nonleading_selection(settings):
    incident = IncidentCreate(description='conflict', logs=['OutOfMemoryError', 'Thread pool exhausted'], metrics={'cpu_usage': 95}, mode='llm')
    inv = await Investigator(settings, cpp_bridge, retriever(settings), ScriptedProvider([choose('CPU')])).run('selection', incident)
    assert inv.hypotheses[0].category == 'Memory'
    assert inv.verification.status == 'passed'
    output = report(incident, inv)
    assert output.root_cause.primary_category == 'CPU'
    assert '## Investigation conclusion\nCPU / Thread Saturation' in output.summary
    assert 'CPU' in output.recommendations[0].action
    assert set(output.root_cause.contributing_factors) == set(inv.proposal.supporting)


@pytest.mark.asyncio
@pytest.mark.parametrize('second', ['failure', 'invalid', 'timeout'])
async def test_failed_revision_discards_old_proposal(settings, incident, second):
    incident.mode = 'llm'
    def invalid(context):
        p = proposal(context).model_copy(update={'category': 'Unknown', 'uncertainty': 'low', 'missing': []})
        return Decision(proposal=p)
    provider = ScriptedProvider([invalid, RuntimeError('synthetic failure') if second == 'failure' else invalid])
    if second == 'timeout':
        original = provider.decide
        async def slow(text):
            if provider.contexts:
                await asyncio.sleep(1)
            return await original(text)
        provider.decide = slow
        settings.timeout_seconds = .03
    inv = await Investigator(settings, cpp_bridge, retriever(settings), provider).run('repair', incident)
    assert inv.proposal is None and not inv.citations
    assert inv.verification.status == 'fallback' and inv.verification.reasons
    assert inv.provider.active == 'deterministic' and inv.provider.calls == 2
    assert sum(t.stage == 'revise' for t in inv.trace) == 1
    assert report(incident, inv).root_cause.primary_category == 'Database'


@pytest.mark.asyncio
async def test_unknown_repaired_once(settings, incident):
    incident.mode = 'llm'
    def invalid(context):
        return Decision(proposal=proposal(context).model_copy(update={'category': 'Unknown', 'uncertainty': 'low'}))
    provider = ScriptedProvider([invalid, choose('Database')])
    inv = await Investigator(settings, cpp_bridge, retriever(settings), provider).run('repaired', incident)
    assert inv.verification.status == 'passed' and inv.proposal.category == 'Database'
    assert inv.provider.calls == 2
    assert sum(t.stage == 'revise' for t in inv.trace) == 1


class FailingQueryEmbeddings(RecordingEmbeddings):
    def __init__(self):
        super().__init__()
        self.fail = False
    def embed_query(self, text):
        if self.fail:
            raise RuntimeError('synthetic semantic outage')
        return super().embed_query(text)


@pytest.mark.asyncio
async def test_semantic_failure_initial_and_tool_search_keep_lexical(settings, incident):
    embed = FailingQueryEmbeddings()
    store = KnowledgeStore(settings.knowledge_db)
    store.index(settings.knowledge_dir, embed, 'test', 3)
    embed.fail = True
    r = OperationalRetriever(store=store, embedder=embed, model='test', dimensions=3)
    incident.mode = 'llm'
    provider = ScriptedProvider([
        lambda c: Decision(tools=[ToolCall(name='search_runbooks', incident_id=c['incident_id'], query='database contention')]),
        choose('Database'),
    ])
    inv = await Investigator(settings, cpp_bridge, r, provider).run('semantic-failure', incident)
    assert inv.retrieval_mode == 'lexical_fallback_query_failure'
    assert inv.verification.status == 'passed' and inv.chunks
    tool_context = json.loads(provider.contexts[1])['tool_results']
    assert tool_context and 'error' not in tool_context[0]
    assert json.loads(tool_context[0]['result'])


@pytest.mark.asyncio
async def test_full_model_context_and_call_budgets(settings, incident):
    settings.context_chars = 1400
    settings.max_model_calls = 2
    incident.mode = 'llm'
    incident.description = '"\\ long untrusted text ' * 300
    def request(c):
        return Decision(tools=[ToolCall(name='get_log_evidence', incident_id=c['incident_id'])])
    provider = ScriptedProvider([request])
    inv = await Investigator(settings, cpp_bridge, retriever(settings), provider).run('budget', incident)
    assert provider.contexts and all(len(c) <= settings.context_chars for c in provider.contexts)
    assert len(provider.contexts) == inv.provider.calls == 2
    assert inv.verification.status == 'fallback' and inv.proposal is None
    assert inv.provider.tool_calls <= settings.max_tool_calls
    assert inv.findings.logs['error_count'] == 1


@pytest.mark.asyncio
async def test_unseen_retrieved_chunk_cannot_be_cited(settings, incident):
    settings.context_chars = 1000
    r = retriever(settings)
    all_chunks, _ = r.store.retrieve('database', k=8)
    # A correct global chunk ID is insufficient; it must have reached this model.
    incident.mode = 'llm'
    seen = set()
    def unseen(c):
        seen.update(v['id'] for v in c['chunks'])
        identity = next(v.id for v in all_chunks if v.id not in seen)
        return Decision(proposal=proposal(c).model_copy(update={'citations': [Citation(chunk_id=identity)]}))
    inv = await Investigator(settings, cpp_bridge, r, ScriptedProvider([unseen])).run('unseen', incident)
    assert inv.proposal is None and inv.verification.status == 'fallback'
    assert any('Citation was not supplied' in reason for reason in inv.verification.reasons)

@pytest.mark.asyncio
async def test_semantic_timeout_fallback_respects_deadline(settings, incident):
    class SlowQuery(FailingQueryEmbeddings):
        def embed_query(self, text):
            if self.fail:
                time.sleep(.15)
            return FakeEmbeddings.embed_query(self, text)
    embed = SlowQuery()
    store = KnowledgeStore(settings.knowledge_db)
    store.index(settings.knowledge_dir, embed, 'test', 3)
    embed.fail = True
    settings.timeout_seconds = .03
    settings.max_duration = 1
    incident.mode = 'llm'
    r = OperationalRetriever(store=store, embedder=embed, model='test', dimensions=3)
    inv = await Investigator(settings, cpp_bridge, r, ScriptedProvider([choose('Database')])).run('slow-query', incident)
    assert inv.retrieval_mode == 'lexical_fallback_query_failure'
    assert inv.proposal is not None and inv.chunks
    assert inv.provider.elapsed_ms < 500
    await asyncio.sleep(.17)  # completion of the old thread must not replace the fallback mode
    assert r.mode == 'lexical_fallback_query_failure'


def test_http_verified_selection_and_diagnostic_contract(settings, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    import app.main as main
    import app.routers.incidents as incidents
    import app.routers.analyze as analyze
    KnowledgeStore(settings.knowledge_db).index(settings.knowledge_dir)
    service = PlannerAgent(settings, ScriptedProvider([choose('CPU')]))
    for module in (main, incidents, analyze):
        monkeypatch.setattr(module, 'planner', service)
    with TestClient(app) as client:
        response = client.post('/analyze/', json={
            'description': 'Do not trust this database diagnosis', 'mode': 'llm',
            'logs': ['OutOfMemoryError', 'Thread pool exhausted'], 'metrics': {'cpu_usage': 95}})
        assert response.status_code == 200
        job = response.json()
        assert job['status'] == 'completed', job
        assert job['root_cause']['primary_category'] == 'CPU'
        assert job['report']['root_cause'] == job['result']['root_cause']
        assert job['report']['investigation']['hypotheses'][0]['category'] == 'Memory'
        refs = {e['id'] for e in client.get(f"/api/v1/incidents/{job['job_id']}/evidence").json()}
        chunks = {c['id'] for c in client.get(f"/api/v1/incidents/{job['job_id']}/citations").json()}
        for rec in job['recommendations']:
            assert set(rec['evidence_ids']) <= refs
            assert all(c['chunk_id'] in chunks for c in rec['citations'])
            assert rec['prerequisites'] and rec['operational_impact']
        assert 'CPU' in job['recommendations'][0]['action']

@pytest.mark.asyncio
async def test_provider_initialization_failure_preserves_deterministic_report(settings, incident, monkeypatch):
    import app.llm.client as adapter
    def broken_provider(_settings):
        raise ValueError('synthetic initialization failure; must not be persisted verbatim')
    monkeypatch.setattr(adapter, 'OpenAIProvider', broken_provider)
    settings.provider = 'openai'
    settings.api_key = 'synthetic-test-key'
    incident.mode = 'llm'
    service = PlannerAgent(settings)
    job = await service.analyze(incident)
    assert job.status == 'completed'
    inv = job.result.investigation
    assert inv.provider.calls == 0 and inv.provider.active == 'deterministic'
    assert inv.verification.status == 'fallback'
    assert 'Provider initialization ValueError' in inv.verification.reasons
    assert 'persisted verbatim' not in job.model_dump_json()
    assert job.result.root_cause.primary_category == 'Database'
    assert job.result.recommendations[0].evidence_ids
    await service.shutdown()
