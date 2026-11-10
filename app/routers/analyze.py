from fastapi import APIRouter, HTTPException
from app.schemas.incident import IncidentCreate, AnalyzeResponse
from app.core.workflow import planner
router=APIRouter(prefix='/analyze',tags=['Analysis'])
@router.post('/',response_model=AnalyzeResponse)
async def analyze(payload:IncidentCreate):
    try:
        job=await planner.analyze(payload)
        return AnalyzeResponse(**job.model_dump(),plan={"tasks":["collect_evidence","retrieve_context","investigate","verify","finalize"]},root_cause=job.result.root_cause if job.result else None,recommendations=job.result.recommendations if job.result else [],report=job.result)
    except RuntimeError as exc:raise HTTPException(429,'Job queue is full') from exc
