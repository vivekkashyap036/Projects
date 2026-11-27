"""Central configuration, read from environment variables / .env (12-factor style).

The same image runs locally, in docker-compose and in Kubernetes; only the
environment changes (in k8s it comes from a ConfigMap + Secret).
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM
    llm_provider: str = "auto"
    llm_model: str = ""
    llm_temperature: float = 0.1

    groq_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""
    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_deployment: str = ""
    openai_api_version: str = "2024-10-21"
    ollama_base_url: str = "http://localhost:11434"

    # Embeddings
    embedding_provider: str = "fastembed"
    embedding_model: str = ""

    # Retrieval
    chunk_size: int = 800
    chunk_overlap: int = 120
    top_k: int = 4
    relevance_threshold: float = 0.45
    llm_grader: bool = True
    collection_name: str = "hr_policies"

    # Storage
    docs_dir: str = "data/policies"
    chroma_dir: str = "storage/chroma"
    database_url: str = "sqlite:///storage/hr.db"

    # Conversation memory: how many previous messages to send back to the graph
    history_window: int = 6

    def resolved_llm_provider(self) -> str:
        if self.llm_provider != "auto":
            return self.llm_provider
        if self.groq_api_key:
            return "groq"
        if self.openai_api_key:
            return "openai"
        if self.azure_openai_api_key and self.azure_openai_endpoint:
            return "azure_openai"
        if self.google_api_key:
            return "gemini"
        return "mock"


@lru_cache
def get_settings() -> Settings:
    return Settings()
