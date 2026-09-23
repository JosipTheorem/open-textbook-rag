"""Configuration for the local textbook agent."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class AgentSettings(BaseSettings):
    """Settings loaded from environment variables and the repository .env file."""

    database_url: str = (
        "postgresql+psycopg://textbook_rag:local-development-only@127.0.0.1:5432/textbook_rag"
    )
    ollama_llm_url: str = "http://127.0.0.1:11435"
    ollama_llm_model: str = "qwen3.5:9b-q4_K_M"
    ollama_llm_context_length: int = 16384

    model_config = SettingsConfigDict(
        env_file=REPOSITORY_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def psycopg_dsn(self) -> str:
        """Return a psycopg-compatible DSN."""
        return self.database_url.replace("postgresql+psycopg://", "postgresql://", 1)
