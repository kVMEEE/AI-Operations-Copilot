"""Real LangChain adapter exercised over an explicitly synthetic HTTP transport."""
import json
import httpx
import pytest
from langchain_openai import ChatOpenAI
from app.investigation.settings import InvestigationSettings
from app.llm.client import OpenAIProvider
import app.llm.client as adapter

@pytest.mark.asyncio
async def test_real_adapter_structured_request(monkeypatch):
    captured=[]
    payload={'tools':[],'proposal':{'category':'Unknown','supporting':[],'contradicting':[],'missing':['more_telemetry'],'uncertainty':'high','citations':[],'numeric_claims':[],'diagnostics':[]}}
    def handle(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200,json={'id':'synthetic','object':'chat.completion','created':0,'model':'gpt-4.1-mini','choices':[{'index':0,'message':{'role':'assistant','content':json.dumps(payload)},'finish_reason':'stop'}],'usage':{'prompt_tokens':12,'completion_tokens':20,'total_tokens':32}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        monkeypatch.setattr(adapter,'ChatOpenAI',lambda **kwargs:ChatOpenAI(**kwargs,http_async_client=client))
        provider=OpenAIProvider(InvestigationSettings(api_key='synthetic-test-key'))
        decision,usage=await provider.decide('api_key=secretvalue untrusted context')
        assert decision.proposal.category=='Unknown'
        assert captured[0]['response_format']['type']=='json_schema'
        assert captured[0]['response_format']['json_schema']['strict'] is True
        assert 'secretvalue' not in json.dumps(captured)
        assert usage['total_tokens']==32
        assert provider.chat.max_retries==0

@pytest.mark.asyncio
async def test_real_adapter_rate_limit_no_hidden_retries(monkeypatch):
    calls=[]
    def handle(request):
        calls.append(request)
        return httpx.Response(429,json={'error':{'message':'synthetic rate limit','type':'rate_limit_error','code':'rate_limit_exceeded'}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        monkeypatch.setattr(adapter,'ChatOpenAI',lambda **kwargs:ChatOpenAI(**kwargs,http_async_client=client))
        provider=OpenAIProvider(InvestigationSettings(api_key='synthetic-test-key'))
        from openai import RateLimitError
        with pytest.raises(RateLimitError):await provider.decide('Synthetic input')
        assert len(calls)==1
