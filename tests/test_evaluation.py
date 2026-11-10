import json
from pathlib import Path
from app.schemas.incident import IncidentCreate
from app.investigation.analytics import collect, fallback
from app.investigation.retrieval import KnowledgeStore
from app.core.cpp_bridge import cpp_bridge
FIXTURES=json.loads((Path(__file__).parent/'fixtures/incidents.json').read_text())
def test_synthetic_categories_and_retrieval(tmp_path):
    store=KnowledgeStore(tmp_path/'kb.db');store.index(Path(__file__).resolve().parents[1]/'knowledge')
    agreement=hits=queries=0
    for row in FIXTURES:
        incident=IncidentCreate(description=row.get('description',row['id']),logs=row['logs'],metrics=row['metrics'])
        findings,evidence,hypotheses=collect(row['id'],incident,cpp_bridge)
        assert hypotheses[0].category==row['category'],row['id'];agreement+=1
        if row['category'] not in ('None','Unknown'):assert hypotheses[0].supporting
        for h in hypotheses:assert set(h.supporting+h.contradicting)<={e.id for e in evidence}
        fallback_category=fallback(incident.logs,incident.metrics)['correlation']['primary_category']
        assert fallback_category==row['category'] or row['id']=='insufficient' and fallback_category=='None'
        if row['relevant']:
            queries+=1;chunks,mode=store.retrieve(' '.join(e.source for e in evidence),k=4)
            hits+=any(c.source==row['relevant'] for c in chunks)
            assert all(c.content_hash and c.version and c.id for c in chunks)
    assert hits==queries
    print(f'Synthetic category agreement {agreement}/{len(FIXTURES)}; lexical document recall@4 {hits}/{queries}')
