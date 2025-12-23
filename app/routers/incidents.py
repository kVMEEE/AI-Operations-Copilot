from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List
from app.schemas.incident import IncidentCreate, JobStatus
from app.core.workflow import planner

router = APIRouter()

@router.post("/", response_model=JobStatus)
async def analyze_incident(incident: IncidentCreate):
    job_id = await planner.start_analysis(incident)
    return planner.get_status(job_id)

@router.get("/{job_id}", response_model=JobStatus)
def get_incident_status(job_id: str):
    status = planner.get_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Incident job not found")
    return status

@router.get("/", response_model=List[JobStatus])
def list_incidents():
    # Return all jobs for demo purposes
    return list(planner.get_all_jobs().values())
