"""Reproducible synthetic evaluation; never calls a model unless --live is explicit."""
import argparse,asyncio,json,tempfile
from pathlib import Path
from app.schemas.incident import IncidentCreate
from app.core.workflow import PlannerAgent
from app.investigation.settings import InvestigationSettings,ROOT
from app.investigation.retrieval import KnowledgeStore

async def evaluate(live=False):
    fixtures=json.loads((ROOT/'tests/fixtures/incidents.json').read_text())
    with tempfile.TemporaryDirectory() as temp:
        settings=InvestigationSettings(database_url=f'sqlite:///{temp}/eval.db',knowledge_db=Path(temp)/'kb.db')
        if live:
            if not settings.key():return {'live':'skipped: no credentials'}
            settings.provider='openai';settings.max_model_calls=2;settings.max_duration=30;fixtures=fixtures[:2]
        KnowledgeStore(settings.knowledge_db).index(settings.knowledge_dir)
        service=PlannerAgent(settings);results=[];hits=queries=0
        for fixture in fixtures:
            incident=IncidentCreate(description=fixture.get('description',fixture['id']),logs=fixture['logs'],metrics=fixture['metrics'],mode='llm' if live else 'deterministic')
            job=await service.analyze(incident)
            if job.status!='completed':raise RuntimeError(job.error)
            inv=job.result.investigation
            if fixture['relevant']:
                queries+=1
                # Retrieval quality evaluated against telemetry, separately from full-context graph query.
                chunks,_=KnowledgeStore(settings.knowledge_db).retrieve(' '.join(e.source for e in inv.evidence),k=4)
                hits+=any(c.source==fixture['relevant'] for c in chunks)
            results.append({'id':fixture['id'],'expected':fixture['category'],'actual':job.result.root_cause.primary_category,'schema_valid':True,'citation_valid':all(c.chunk_id in {v.id for v in inv.chunks} for c in inv.citations),'citation_count':len(inv.citations),'abstained':job.result.root_cause.primary_category=='Unknown','verification':inv.verification.model_dump(),'latency_ms':inv.provider.elapsed_ms,'usage':inv.provider.usage,'provider':inv.provider.active})
        await service.shutdown()
        return {'mode':'live_synthetic' if live else 'offline_deterministic','category_agreement':{'correct':sum(r['actual']==r['expected'] for r in results),'total':len(results)},'lexical_document_recall_at_4':{'hits':hits,'queries':queries,'recall':hits/queries if queries else None},'results':results,'limitations':'Synthetic fixtures are not production accuracy estimates. Empty citations do not establish faithfulness. Semantic embedding quality requires a separately labelled live evaluation.'}
def main():
    p=argparse.ArgumentParser();p.add_argument('--live',action='store_true');p.add_argument('--output');a=p.parse_args();data=json.dumps(asyncio.run(evaluate(a.live)),indent=2)
    if a.output:Path(a.output).write_text(data+'\n')
    print(data)
if __name__=='__main__':main()
