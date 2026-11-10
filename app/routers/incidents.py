from uuid import UUID
from fastapi import APIRouter, HTTPException
from app.schemas.incident import IncidentCreate,JobStatus
from app.investigation.contracts import Evidence,Chunk,Trace
from app.core.workflow import planner
router=APIRouter()
def job(identity):
    result=planner.get_status(str(identity))
    if result is None:raise HTTPException(404,'Incident not found')
    return result
@router.post('/',response_model=JobStatus)
async def submit(incident:IncidentCreate):
    try:return planner.get_status(await planner.start_analysis(incident))
    except RuntimeError as exc:raise HTTPException(429,'Job queue is full') from exc
@router.get('/',response_model=list[JobStatus])
def list_incidents():return list(planner.get_all_jobs().values())
@router.get('/{identity}',response_model=JobStatus)
def get_incident(identity:UUID):return job(identity)
@router.post('/{identity}/cancel',response_model=JobStatus)
async def cancel(identity:UUID):
    job(identity);return await planner.cancel(str(identity))
@router.get('/{identity}/evidence',response_model=list[Evidence])
def evidence(identity:UUID):
    r=job(identity).result;return r.investigation.evidence if r and r.investigation else []
@router.get('/{identity}/citations',response_model=list[Chunk])
def citations(identity:UUID):
    r=job(identity).result;return r.investigation.chunks if r and r.investigation else []
@router.get('/{identity}/trace',response_model=list[Trace])
def trace(identity:UUID):
    r=job(identity).result;return r.investigation.trace if r and r.investigation else []
@router.get('/{identity}/stages')
def stages(identity:UUID):
    job(identity);return planner.store.stages(str(identity))
