"""Bounded tool investigation. State holds concise decisions, never private reasoning."""
import asyncio, json, time
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from app.investigation.contracts import Decision, Verification, Trace, Investigation, ProviderMetadata, Findings, Evidence, Hypothesis, Chunk, Proposal
from app.investigation.analytics import collect
from app.investigation.security import redact

class State(TypedDict, total=False):
    findings: Findings
    evidence: list[Evidence]
    hypotheses: list[Hypothesis]
    chunks: list[Chunk]
    proposal: Proposal | None
    decision: Decision
    verification: list[str]
    trace: list[Trace]
    revision: int
    tool_results: list
    route: str


def verify(proposal,evidence,hypotheses,chunks,incident_id):
    reasons=[]; by_id={e.id:e for e in evidence}; chunk_ids={c.id for c in chunks}
    if proposal is None: return ['No structured proposal']
    refs=proposal.supporting+proposal.contradicting
    for c in proposal.citations: refs+=c.evidence_ids
    for d in proposal.diagnostics: refs+=d.evidence_ids
    refs += [c.evidence_id for c in proposal.numeric_claims]
    if any(i not in by_id or by_id[i].incident_id!=incident_id for i in refs): reasons.append('Unknown or cross-incident evidence reference')
    if any(c.chunk_id not in chunk_ids for c in proposal.citations): reasons.append('Citation was not supplied to this investigation')
    candidates={h.category:h for h in hypotheses}
    if set(proposal.supporting) & set(proposal.contradicting):
        reasons.append('Evidence cannot both support and contradict the selection')
    if proposal.category == 'Unknown':
        if proposal.uncertainty != 'high':
            reasons.append('Unknown requires high uncertainty')
        if not proposal.missing:
            reasons.append('Unknown requires missing information')
        contradictions = {ref for h in hypotheses for ref in h.contradicting}
        if set(proposal.contradicting) != contradictions:
            reasons.append('Unknown must preserve known contradictions')
    if proposal.category not in candidates and proposal.category!='Unknown': reasons.append('Category lacks deterministic support')
    if proposal.category in candidates and proposal.category != 'Unknown':
        h=candidates[proposal.category]
        if proposal.category not in ('None','Unknown') and not set(proposal.supporting)&set(h.supporting): reasons.append('Hypothesis lacks supporting evidence')
        if not set(proposal.supporting)<=set(h.supporting): reasons.append('Supporting references do not support the selected category')
        if not set(h.contradicting)<=set(proposal.contradicting): reasons.append('Known contradictory evidence omitted')
        if not set(proposal.contradicting)<=set(h.contradicting): reasons.append('Contradicting references are not normal category metrics')
    for claim in proposal.numeric_claims:
        e=by_id.get(claim.evidence_id); actual=e.values.get(claim.field) if e else None
        if not isinstance(actual,(float,int)) or abs(actual-claim.value)>1e-6*max(1,abs(actual)): reasons.append('Numeric claim differs from measured evidence')
    if any(d.action_type!='read_only' for d in proposal.diagnostics): reasons.append('Diagnostic action type mismatch')
    return sorted(set(reasons))

def model_context(incident_id, incident, state, chunks, budget):
    """Pack complete JSON objects; the budget covers the entire untrusted message.

    Return only chunk IDs whose contents are actually included, so retrieval alone
    never authorizes a citation. Earlier delivered chunks remain valid snapshots.
    """
    context = {'incident_id': incident_id, 'revision': state.get('revision', 0),
               'verification_errors': state.get('verification', []),
               'hypotheses': [], 'tool_results': [], 'chunks': [], 'evidence': [],
               'untrusted_description': ''}
    encode = lambda: redact(json.dumps(context, ensure_ascii=False, default=str))
    delivered = set()
    if len(encode()) > budget:
        raise ValueError('Context budget cannot fit investigation metadata')
    def append(key, value):
        context[key].append(value)
        if len(encode()) > budget:
            context[key].pop()
            return False
        return True
    for h in state['hypotheses']:
        append('hypotheses', h.model_dump())
    for result in reversed(state.get('tool_results', [])[-6:]):
        public = {k:v for k,v in result.items() if not k.startswith('_')}
        if append('tool_results', public):
            delivered.update(result.get('_chunk_ids', []))
    for chunk in chunks:
        if append('chunks', chunk.model_dump()):
            delivered.add(chunk.id)
    for evidence in state['evidence']:
        append('evidence', evidence.model_dump())
    # Context is telemetry-first; descriptions are optional untrusted background.
    context['untrusted_description'] = incident.description[:max(0, budget-len(encode())-16)]
    while len(encode()) > budget:
        context['untrusted_description'] = context['untrusted_description'][:len(context['untrusted_description'])//2]
    return encode(), delivered

class Investigator:
    def __init__(self,settings,bridge,retriever,provider=None):
        self.s=settings; self.bridge=bridge;self.retriever=retriever;self.provider=provider
    async def run(self,incident_id,incident,stage=lambda name:None):
        started=time.monotonic(); deadline=started+self.s.max_duration
        metadata=ProviderMetadata(requested=incident.mode,active=getattr(self.provider,'label','disabled'),model=self.s.chat_model if self.provider else None)
        if incident.mode=='llm' and not self.provider: metadata.error='Provider disabled or credentials unavailable'
        seen=set(); supplied={}; available={}; trace=[]; calls=0; tools=0; steps=0
        async def enter(name):
            nonlocal steps
            steps+=1
            if steps>self.s.max_graph_steps: raise TimeoutError('Graph step budget exhausted')
            stage(name);trace.append(Trace(stage=name,outcome='entered'))
        async def collect_node(state):
            await enter('collect_evidence')
            native_task=asyncio.create_task(asyncio.to_thread(collect,incident_id,incident,self.bridge))
            try:
                f,e,h=await asyncio.shield(native_task)
            except asyncio.CancelledError:
                # Keep the concurrency slot until the bounded native call actually exits.
                await native_task
                raise
            return {'findings':f,'evidence':e,'hypotheses':h,'revision':0,'tool_results':[]}
        async def lookup(query):
            # Isolate each request: a timed-out embedding thread must not overwrite
            # the mode or embedder used by its lexical fallback.
            request = self.retriever.model_copy()
            def remaining():
                return max(.001, min(self.s.timeout_seconds, deadline-time.monotonic()))
            try:
                chunks = await asyncio.wait_for(asyncio.to_thread(request.chunks, query), timeout=remaining())
                self.retriever.mode = request.mode
            except Exception:
                lexical = request.model_copy(update={'embedder': None})
                chunks = await asyncio.wait_for(asyncio.to_thread(lexical.chunks, query), timeout=remaining())
                self.retriever.mode = 'lexical_fallback_query_failure'
            return chunks
        async def retrieve(state):
            await enter('retrieve_context')
            query=' '.join(h.title for h in state['hypotheses'])+' '+' '.join(e.source for e in state['evidence'])
            chunks = await lookup(query[:3000])
            available.update({c.id:c for c in chunks})
            return {'chunks':chunks}
        async def investigate(state):
            nonlocal calls
            await enter('investigate')
            if not self.provider or incident.mode!='llm': return {'route':'verify','proposal':None}
            if calls>=self.s.max_model_calls or time.monotonic()>=deadline:
                metadata.error='Investigation call or duration budget exhausted';return {'route':'finalize','proposal':None}
            context, delivered = model_context(incident_id, incident, state, list(available.values()), self.s.context_chars)
            supplied.update({identity:available[identity] for identity in delivered})
            if time.monotonic() >= deadline:
                metadata.error='Investigation duration budget exhausted'
                return {'route':'finalize','proposal':None}
            calls+=1;metadata.calls=calls
            try:
                decision,usage=await asyncio.wait_for(self.provider.decide(redact(context)),timeout=max(.01,min(self.s.timeout_seconds,deadline-time.monotonic())))
                decision=Decision.model_validate(decision)
                metadata.error=None
                for k,v in usage.items(): metadata.usage[k]=metadata.usage.get(k,0)+v
                if bool(decision.tools)==bool(decision.proposal): raise ValueError('Expected tools or proposal exclusively')
                return {'decision':decision,'proposal':decision.proposal,'route':'execute_tools' if decision.tools else 'verify'}
            except asyncio.CancelledError: raise
            except Exception as exc:
                metadata.error='Provider '+type(exc).__name__
                trace.append(Trace(stage='investigate',outcome=metadata.error))
                # One retry at most for each investigation phase, within the global call budget.
                if state.get('revision',0)==0: return {'verification':['Provider output unavailable or invalid'],'route':'revise','proposal':None}
                return {'route':'finalize','proposal':None}
        async def execute(state):
            nonlocal tools
            await enter('execute_tools'); results=[]
            for call in state['decision'].tools:
                key=call.model_dump_json()
                if tools>=self.s.max_tool_calls or time.monotonic()>=deadline:
                    metadata.error='Tool or duration budget exhausted';return {'route':'finalize','proposal':None}
                tools+=1;metadata.tool_calls=tools
                try:
                    if call.incident_id!=incident_id: raise ValueError('Incident ownership mismatch')
                    if call.name!='search_runbooks' and call.query: raise ValueError('Query is only valid for search')
                    if call.name in ('search_runbooks','get_rule_hypotheses') and call.reference_id: raise ValueError('Unexpected reference argument')
                    if key in seen: raise ValueError('Duplicate tool call')
                    seen.add(key)
                    if call.name.startswith('get_') and call.name.endswith('_evidence'):
                        kind='log' if call.name=='get_log_evidence' else 'metric'
                        data=[e.model_dump() for e in state['evidence'] if e.kind==kind and (not call.reference_id or e.id==call.reference_id)][:20]
                        if call.reference_id and not data: raise ValueError('Evidence not found in this incident')
                    elif call.name=='get_rule_hypotheses': data=[h.model_dump() for h in state['hypotheses']]
                    elif call.name=='search_runbooks':
                        if not call.query: raise ValueError('Search query required')
                        chunks=await lookup(call.query)
                        # Total supplied context remains bounded across tool calls.
                        for c in chunks:
                            if c.id not in available and sum(len(v.content) for v in available.values())+len(c.content)<=self.s.context_chars:
                                available[c.id]=c
                        data=[available[c.id].model_dump() for c in chunks if c.id in available]
                    else:
                        if call.reference_id not in supplied: raise ValueError('Chunk was not retrieved for this incident')
                        data=supplied[call.reference_id].model_dump()
                    # Complete items only: never authorize a partially delivered chunk.
                    if isinstance(data, list):
                        while data and len(json.dumps(data)) > min(6000, self.s.context_chars//2):
                            data.pop()
                    text=json.dumps(data,default=str)
                    chunk_ids = []
                    if call.name == 'search_runbooks':
                        chunk_ids = [item['id'] for item in data]
                    elif call.name == 'get_runbook_chunk':
                        chunk_ids = [call.reference_id]
                    if len(text)>6000:
                        text='Response exceeds tool budget; request a narrower reference.'
                        chunk_ids=[]
                    results.append({'tool':call.name,'result':text,'_chunk_ids':chunk_ids})
                    trace.append(Trace(stage='execute_tools',outcome=call.name+' completed',reference=call.reference_id or None))
                except Exception as exc:
                    results.append({'tool':call.name,'error':type(exc).__name__})
                    trace.append(Trace(stage='execute_tools',outcome=call.name+' rejected'))
            return {'tool_results':state.get('tool_results',[])+results,'chunks':list(available.values()),'route':'investigate'}
        async def verify_node(state):
            await enter('verify')
            if state.get('proposal') is None and (not self.provider or incident.mode!='llm'):
                if any(e.incident_id!=incident_id for e in state['evidence']):
                    raise ValueError('Evidence ownership mismatch')
                return {'verification':[], 'route':'finalize'}
            reasons=verify(state['proposal'],state['evidence'],state['hypotheses'],list(supplied.values()),incident_id)
            return {'verification':reasons,'route':'revise' if reasons and state['revision']==0 else 'finalize'}
        async def revise(state):
            await enter('revise');return {'revision':1,'proposal':None,'route':'investigate'}
        async def finalize(state):
            await enter('finalize');return state
        graph=StateGraph(State)
        for name,node in [('collect_evidence',collect_node),('retrieve_context',retrieve),('investigate',investigate),('execute_tools',execute),('verify',verify_node),('revise',revise),('finalize',finalize)]: graph.add_node(name,node)
        graph.add_edge(START,'collect_evidence');graph.add_edge('collect_evidence','retrieve_context');graph.add_edge('retrieve_context','investigate')
        for name in ('investigate','execute_tools','verify','revise'): graph.add_conditional_edges(name,lambda s:s['route'])
        graph.add_edge('finalize',END)
        # Collection is always retained for deterministic fallback if graph budgets expire.
        latest={}
        try:
            async with asyncio.timeout(self.s.max_duration):
                async for update in graph.compile().astream({},config={'recursion_limit':self.s.max_graph_steps}):
                    for value in update.values(): latest.update(value)
        except asyncio.CancelledError: raise
        except Exception as exc:
            metadata.error='Investigation '+type(exc).__name__
        if 'findings' not in latest:
            # Collection itself is bounded by input sizes; no second analysis is attempted.
            raise RuntimeError('Evidence collection did not complete')
        proposal=latest.get('proposal');reasons=verify(proposal,latest['evidence'],latest['hypotheses'],list(supplied.values()),incident_id) if proposal else []
        assisted=bool(proposal and not reasons and not metadata.error)
        if not assisted: proposal=None
        metadata.active=getattr(self.provider,'label','disabled') if assisted else 'deterministic'
        metadata.elapsed_ms=(time.monotonic()-started)*1000
        return Investigation(evidence=latest['evidence'],findings=latest['findings'],hypotheses=latest['hypotheses'],chunks=list(supplied.values()) if self.provider and incident.mode=='llm' else list(available.values()),citations=proposal.citations if proposal else [],proposal=proposal,verification=Verification(status='passed' if assisted or incident.mode=='deterministic' else 'fallback',reasons=reasons+latest.get('verification',[])+([metadata.error] if metadata.error else [])+(['Provider proposal rejected'] if latest.get('verification') and not assisted else [])),provider=metadata,retrieval_mode=self.retriever.mode,trace=trace)
