"""Configuration settings for the WMS orchestrator."""
from functools import lru_cache
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    database_url: str = Field("postgresql+psycopg2://wms:wms@db:5432/wms", env="DATABASE_URL")
    github_token: str | None = Field(default=None, env="GITHUB_TOKEN")
    github_repo: str | None = Field(default=None, env="GITHUB_REPO")
    llm_endpoint: str | None = Field(default=None, env="LLM_ENDPOINT")
    worker_poll_interval_seconds: int = Field(default=5, env="WORKER_POLL_INTERVAL_SECONDS")
    max_attempts: int = Field(default=3, env="MAX_ATTEMPTS")
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
