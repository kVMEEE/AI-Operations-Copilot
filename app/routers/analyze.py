from fastapi import APIRouter
from app.agents.runner import AgentRunner

router = APIRouter(prefix="/analyze", tags=["Analysis"])

runner = AgentRunner()

@router.post("/")
def analyze(payload: dict):
    return runner.run(payload)
