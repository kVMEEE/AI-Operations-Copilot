"""Shared bounded service for HTTP, desktop and offline use."""
import asyncio, uuid
from app.schemas.incident import IncidentCreate
from app.core.cpp_bridge import cpp_bridge
from app.investigation.settings import InvestigationSettings
from app.investigation.persistence import Store
from app.investigation.retrieval import KnowledgeStore, OperationalRetriever
from app.investigation.graph import Investigator
from app.investigation.report import report
from app.investigation.security import redact

class PlannerAgent:
    def __init__(self,settings=None,provider=None):
        self.settings=settings or InvestigationSettings(); self.store=Store(self.settings.database_url)
        self.tasks={};self.semaphore=None;self.initialized=False;self.provider_override=provider
    def initialize(self):
        if not self.initialized:
            self.store.initialize();self.store.recover();self.semaphore=asyncio.Semaphore(self.settings.concurrency);self.initialized=True
    async def start_analysis(self,incident):
        self.initialize()
        if len(self.tasks)>=self.settings.max_pending: raise RuntimeError('Job queue is full')
        incident=IncidentCreate.model_validate(incident)
        incident=incident.model_copy(update={'description':redact(incident.description),'logs':[redact(l) for l in incident.logs]})
        identity=str(uuid.uuid4());self.store.create(identity,incident)
        task=asyncio.create_task(self.run_workflow(identity,incident));self.tasks[identity]=task
        task.add_done_callback(lambda t:self.tasks.pop(identity,None))
        return identity
    async def run_workflow(self,identity,incident):
        try:
            async with self.semaphore:
                self.store.update(identity,status='processing',step='initializing')
                provider=None;embedder=None;provider_setup_error=None
                if incident.mode=='llm':
                    provider=self.provider_override
                    if provider is None and self.settings.provider=='openai' and self.settings.key():
                        from app.llm.client import OpenAIProvider,embeddings
                        try:
                            provider=OpenAIProvider(self.settings);embedder=embeddings(self.settings)
                        except Exception as exc:
                            provider=None;embedder=None
                            provider_setup_error='Provider initialization '+type(exc).__name__
                retriever=OperationalRetriever(store=KnowledgeStore(self.settings.knowledge_db,self.settings.knowledge_dir),embedder=embedder,model=self.settings.embedding_model,dimensions=self.settings.embedding_dimensions,top_k=self.settings.top_k,budget=self.settings.context_chars)
                inv=await Investigator(self.settings,cpp_bridge,retriever,provider).run(identity,incident,lambda stage:self.store.update(identity,step=stage))
                if provider_setup_error:
                    inv.provider.error=provider_setup_error
                    inv.verification.reasons.append(provider_setup_error)
                self.store.update(identity,status='completed',step='done',result=report(incident,inv))
        except asyncio.CancelledError:
            self.store.update(identity,status='cancelled',step='cancelled');raise
        except Exception as exc:
            # Never persist raw provider exceptions, prompts or credentials.
            self.store.update(identity,status='failed',step='failed',error=type(exc).__name__)
    def get_status(self,identity):self.initialize();return self.store.get(identity)
    def get_all_jobs(self):self.initialize();return self.store.list()
    async def cancel(self,identity):
        task=self.tasks.get(str(identity))
        if task and not task.done():
            task.cancel()
            await asyncio.gather(task,return_exceptions=True)
            # A queued task cancelled before its coroutine begins still needs persisted status.
            self.store.update(str(identity),status='cancelled',step='cancelled')
        return self.get_status(identity)
    async def shutdown(self):
        for task in list(self.tasks.values()): task.cancel()
        await asyncio.gather(*list(self.tasks.values()),return_exceptions=True)
    async def analyze(self,incident):
        identity=await self.start_analysis(incident)
        task=self.tasks.get(identity)
        if task: await task
        return self.get_status(identity)

planner=PlannerAgent()
