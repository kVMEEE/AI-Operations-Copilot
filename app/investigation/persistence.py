"""Versioned additive SQLite schema; one process owns job execution."""
import json
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, String, Text, Integer, select, event
from sqlalchemy.orm import declarative_base, sessionmaker

Base=declarative_base()
class Job(Base):
    __tablename__='investigation_jobs'
    id=Column(String,primary_key=True)
    status=Column(String,nullable=False)
    step=Column(String,nullable=False)
    created_at=Column(String,nullable=False)
    description=Column(Text,nullable=False)
    input_json=Column(Text,nullable=False)
    result_json=Column(Text)
    error=Column(String)
class Stage(Base):
    __tablename__='investigation_stages'
    id=Column(Integer,primary_key=True)
    job_id=Column(String,index=True,nullable=False)
    stage=Column(String,nullable=False)
    at=Column(String,nullable=False)
class SchemaVersion(Base):
    __tablename__='investigation_schema'
    version=Column(Integer,primary_key=True)

class Store:
    def __init__(self,url):
        self.engine=create_engine(url,connect_args={'check_same_thread':False,'timeout':20})
        @event.listens_for(self.engine,'connect')
        def configure(dbapi,record):
            dbapi.execute('PRAGMA journal_mode=WAL'); dbapi.execute('PRAGMA busy_timeout=20000')
        self.sessions=sessionmaker(self.engine,expire_on_commit=False)
    def initialize(self):
        Base.metadata.create_all(self.engine)
        with self.sessions.begin() as s:
            versions=list(s.scalars(select(SchemaVersion.version)))
            if any(v>1 for v in versions): raise RuntimeError('Database schema is newer than this application')
            if not versions: s.add(SchemaVersion(version=1))
    def recover(self):
        with self.sessions.begin() as s:
            for job in s.scalars(select(Job).where(Job.status.in_(['queued','processing']))):
                job.status='interrupted';job.step='interrupted';job.error='Process restarted before completion'
                s.add(Stage(job_id=job.id,stage='interrupted',at=datetime.now(timezone.utc).isoformat()))
    def create(self,identity,incident):
        with self.sessions.begin() as s:
            s.add(Job(id=identity,status='queued',step='queued',created_at=datetime.now(timezone.utc).isoformat(),description=incident.description,input_json=incident.model_dump_json()))
            s.add(Stage(job_id=identity,stage='queued',at=datetime.now(timezone.utc).isoformat()))
    def update(self,identity,status=None,step=None,result=None,error=None):
        with self.sessions.begin() as s:
            job=s.get(Job,identity)
            if not job: raise KeyError(identity)
            if status:job.status=status
            if step:
                job.step=step;s.add(Stage(job_id=identity,stage=step,at=datetime.now(timezone.utc).isoformat()))
            if result is not None:job.result_json=result.model_dump_json()
            if error:job.error=error
    def get(self,identity):
        from app.schemas.incident import JobStatus
        with self.sessions() as s:
            job=s.get(Job,str(identity))
            if not job:return None
            return JobStatus(job_id=job.id,status=job.status,step=job.step,created_at=job.created_at,description=job.description,result=json.loads(job.result_json) if job.result_json else None,error=job.error)
    def list(self):
        with self.sessions() as s: ids=list(s.scalars(select(Job.id).order_by(Job.created_at.desc()).limit(200)))
        return {i:self.get(i) for i in ids}
    def stages(self,identity):
        with self.sessions() as s:return [{'stage':r.stage,'at':r.at} for r in s.scalars(select(Stage).where(Stage.job_id==str(identity)).order_by(Stage.id))]
