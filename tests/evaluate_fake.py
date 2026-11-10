"""Explicit offline fake-provider evaluation; measures plumbing, not model intelligence."""
import asyncio,json,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_investigation import FakeProvider
from app.investigation.settings import InvestigationSettings,ROOT
from app.investigation.retrieval import KnowledgeStore
from app.core.workflow import PlannerAgent
from app.schemas.incident import IncidentCreate
async def main():
    rows=json.loads((ROOT/'tests/fixtures/incidents.json').read_text());results=[]
    with tempfile.TemporaryDirectory() as temp:
        settings=InvestigationSettings(database_url=f'sqlite:///{temp}/fake.db',knowledge_db=Path(temp)/'kb.db')
        KnowledgeStore(settings.knowledge_db).index(settings.knowledge_dir)
        service=PlannerAgent(settings,FakeProvider('valid'))
        for row in rows:
            job=await service.analyze(IncidentCreate(description=row.get('description',row['id']),logs=row['logs'],metrics=row['metrics'],mode='llm'))
            assert job.status=='completed',job.error
            inv=job.result.investigation
            assert inv.provider.active=='fake_test_only'
            results.append({'id':row['id'],'expected':row['category'],'actual':job.result.root_cause.primary_category,'citation_count':len(inv.citations),'valid_citations':sum(c.chunk_id in {v.id for v in inv.chunks} for c in inv.citations),'schema_valid':True,'verification':inv.verification.status,'abstained':job.result.root_cause.primary_category=='Unknown'})
        await service.shutdown()
    output={'mode':'fake_test_only','category_agreement':{'correct':sum(r['actual']==r['expected'] for r in results),'total':len(rows)},'results':results,'limitations':'Fake provider copies rule hypotheses. This evaluates graph/schema/citation plumbing, not real-model reasoning or semantic faithfulness. Adversarial unsupported-claim rejection is tested separately in pytest.'}
    (ROOT/'docs/fake-evaluation-results.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({k:v for k,v in output.items() if k!='results'}))
asyncio.run(main())
