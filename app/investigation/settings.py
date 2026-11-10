from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

ROOT=Path(__file__).resolve().parents[2]
class InvestigationSettings(BaseSettings):
    model_config=SettingsConfigDict(env_prefix='AIOPS_',env_file='.env',extra='ignore')
    database_url: str = 'sqlite:///./ai_ops.db'
    knowledge_dir: Path = ROOT/'knowledge'
    knowledge_db: Path = ROOT/'data/knowledge.sqlite3'
    provider: str = 'disabled'
    chat_model: str = 'gpt-4.1-mini'
    embedding_model: str = 'text-embedding-3-small'
    embedding_dimensions: int = Field(default=1536,ge=1,le=3072)
    api_key: str | None = Field(default=None,repr=False)
    timeout_seconds: float = Field(default=15,gt=0,le=60)
    max_duration: float = Field(default=45,gt=0,le=180)
    max_model_calls: int = Field(default=4,ge=1,le=8)
    max_tool_calls: int = Field(default=6,ge=0,le=12)
    max_graph_steps: int = Field(default=24,ge=8,le=40)
    max_output_tokens: int = Field(default=1800,ge=256,le=4096)
    concurrency: int = Field(default=2,ge=1,le=8)
    max_pending: int = Field(default=32,ge=1,le=100)
    top_k: int = Field(default=4,ge=1,le=8)
    context_chars: int = Field(default=12000,ge=1000,le=20000)

    def key(self):
        import os
        return self.api_key or os.environ.get('OPENAI_API_KEY')
