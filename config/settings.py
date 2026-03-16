from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Modular RAG API"
    admin_email: str = "admin@example.com"
    openai_api_key: Optional[str] = None

    # Backend Selection: "api", "local", or "nvidia"
    backend_mode: str = "nvidia"

    # Model Selection
    openai_model: str = "gpt-3.5-turbo"
    local_model: str = "qwen2.5:0.5b"
    embeddings_model: str = "qwen2.5:0.5b"
    nvidia_model: str = "qwen/qwen3.5-397b-a17b"

    # API Keys
    openai_api_key: Optional[str] = None
    nvidia_api_key: Optional[str] = None
    finnhub_api_key: Optional[str] = None
    newsapi_api_key: Optional[str] = None

    # Vector DB
    vector_db_path: str = "./chroma_db"
    # Documents Path
    documents_path: str = "./documents"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
