from __future__ import annotations

from functools import lru_cache

from langchain_openai import ChatOpenAI
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    llm_model: str = Field(default="meta/llama-3.1-70b-instruct", alias="LLM_MODEL")
    llm_temperature: float = Field(default=0.2, alias="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=2000, alias="LLM_MAX_TOKENS")
    llm_rpm: int = Field(default=40, alias="LLM_RPM")

    nvidia_api_key: str | None = Field(default=None, alias="NVIDIA_API_KEY")
    nvidia_base_url: str = Field(
        default="https://integrate.api.nvidia.com/v1",
        alias="NVIDIA_BASE_URL",
    )
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def build_llm_client() -> ChatOpenAI:
    """NVIDIA Build API (OpenAI-compatible). Requires NVIDIA_API_KEY only."""
    settings = get_settings()
    if not settings.nvidia_api_key:
        raise ValueError("NVIDIA_API_KEY is required for LLM calls")
    return ChatOpenAI(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        api_key=settings.nvidia_api_key,
        base_url=settings.nvidia_base_url,
    )
