import time
from fastapi.testclient import TestClient
from app.main import app
from app.core.workflow import PlannerAgent
from app.investigation.settings import InvestigationSettings
import app.main as main
import app.routers.incidents as incidents
import app.routers.analyze as analyze

def test_http_lifecycle(tmp_path,monkeypatch):
    s=InvestigationSettings(database_url=f'sqlite:///{tmp_path}/api.db',knowledge_db=tmp_path/'kb.db')
    service=PlannerAgent(s)
    for mod in [main,incidents,analyze]:monkeypatch.setattr(mod,'planner',service)
    with TestClient(app) as client:
        assert client.get('/health/').json()=={'health':'ok'}
        assert client.get('/').status_code==200
        assert client.post('/api/v1/incidents/',json={'description':'bad','metrics':{'cpu':True}}).status_code==422
        assert 'hidden-secret' not in client.post('/api/v1/incidents/',json={'description':'x','metrics':{'cpu':'hidden-secret'}}).text
        payload={'description':'<img src=x onerror=alert(1)> api_key=hiddenvalue','logs':['No space left on device'],'metrics':{'disk_usage_percent':94},'mode':'llm'}
        result=client.post('/analyze/',json=payload);assert result.status_code==200
        data=result.json();assert data['status']=='completed',data
        assert 'hiddenvalue' not in result.text
        assert '<img' not in data['result']['summary_html']
        identity=data['job_id']
        assert client.get(f'/api/v1/incidents/{identity}/evidence').json()
        assert client.get(f'/api/v1/incidents/{identity}/trace').json()
        assert client.get(f'/api/v1/incidents/{identity}/stages').json()
        assert client.get('/api/v1/incidents/00000000-0000-0000-0000-000000000001/evidence').status_code==404
        assert client.get('/api/v1/incidents/not-a-uuid').status_code==422
        submitted=client.post('/api/v1/incidents/',json={'description':'normal','logs':[],'metrics':{}}).json()
        for _ in range(50):
            state=client.get('/api/v1/incidents/'+submitted['job_id']).json()
            if state['status']=='completed':break
            time.sleep(.02)
        assert state['status']=='completed'
        assert len(client.get('/api/v1/incidents/').json())==2
