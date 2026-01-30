from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    app_name: str = "Modular RAG API"
    admin_email: str = "admin@example.com"
    openai_api_key: Optional[str] = None
    
    # Backend Selection: "api", "local", or "nvidia"
    backend_mode: str = "local"
    
    # Model Selection
    openai_model: str = "gpt-3.5-turbo"
    local_model: str = "Qwen/Qwen2.5-0.5B-Instruct"
    nvidia_model: str = "meta/llama-3.2-3b-instruct"
    
    # API Keys
    openai_api_key: Optional[str] = None
    nvidia_api_key: Optional[str] = None
    
    # Vector DB
    vector_db_path: str = "./chroma_db"
    
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
