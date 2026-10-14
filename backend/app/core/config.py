
from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App ---
    app_env: Literal["development", "production", "test"] = "development"
    frontend_origin: str = "http://localhost:3000"

    # --- Database ---
    database_url: str

    # --- Auth ---
    jwt_secret: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    # --- AI providers ---
    llm_provider: Literal["gemini", "anthropic", "openrouter"] = "gemini"
    embedding_provider: Literal["gemini", "openai"] = "gemini"
    embedding_dim: int = 768  # fixed into the DB schema (migration 0001)

    gemini_api_key: str | None = None
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    openrouter_api_key: str | None = None

    gemini_llm_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    anthropic_llm_model: str = "claude-haiku-5-5"
    openai_embedding_model: str = "text-embedding-3-small"
    openrouter_llm_model: str = "openai/gpt-4o-mini"

    # --- RAG tuning ---
    chunk_size: int = 800
    chunk_overlap: int = 100
    retrieval_top_k: int = 5
    relevance_threshold: float = 0.35

    # --- Limits (cost and abuse protection) ---
    max_upload_mb: int = 10
    max_pdf_pages: int = 300
    max_message_chars: int = 1000
    max_history_messages: int = 10
    llm_max_output_tokens: int = 600
    chat_rate_limit_per_minute: int = 20
    auth_rate_limit_per_minute: int = 10
    org_daily_message_limit: int = 500

    @property
    def sqlalchemy_url(self) -> str:
        url = self.database_url
        if url.startswith("postgresql://"):
            return url.replace(
                "postgresql://", "postgresql+psycopg://", 1
            )
        return url

    @model_validator(mode="after")
    def check_provider_keys(self) -> "Settings":
        keys = {
            "gemini": self.gemini_api_key,
            "anthropic": self.anthropic_api_key,
            "openai": self.openai_api_key,
            "openrouter": self.openrouter_api_key,
        }

        for label, provider in (
            ("LLM", self.llm_provider),
            ("EMBEDDING", self.embedding_provider),
        ):
            if not keys[provider]:
                raise ValueError(
                    f"{provider.upper()}_API_KEY is required because "
                    f"{label}_PROVIDER={provider}"
                )

        if self.app_env == "production" and not self.cookie_secure:
            raise ValueError("COOKIE_SECURE must be true in production")

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
