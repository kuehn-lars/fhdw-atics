from typing import Optional
import os
from config.settings import settings
from crewai import LLM

def get_crew_llm(backend: Optional[str] = None, model: Optional[str] = None) -> LLM:
    """
    Returns a CrewAI compatible LLM object based on backend and model.
    
    Args:
        backend: 'nim' (NVIDIA), 'local' (Ollama), or 'api' (OpenAI). 
                 Defaults to settings.backend_mode.
        model: Specific model name. Defaults to the respective model in settings.
        
    Returns:
        crewai.LLM: Configured LLM object.
    """
    eff_backend = (backend or settings.backend_mode).lower()
    
    if eff_backend in ["nim", "nvidia"]:
        if not settings.nvidia_api_key:
            raise ValueError("NVIDIA_API_KEY must be set in .env for NIM/NVIDIA mode.")
        
        return LLM(
            model=model or settings.nvidia_model,
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=settings.nvidia_api_key,
            temperature=0.6,
            max_tokens=16384,
            timeout=600,
            extra_body={
                "top_p": 0.95,
                "top_k": 20,
                "chat_template_kwargs": {"enable_thinking": True}
            }
        )
        
    elif eff_backend == "local":
        # Standard configuration for local Ollama instance
        return LLM(
            model=model or settings.local_model,
            base_url="http://localhost:11434/v1"
        )
        
    elif eff_backend == "api":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY must be set in .env for API mode.")
            
        return LLM(
            model=model or settings.openai_model,
            api_key=settings.openai_api_key
        )
        
    else:
        raise ValueError(f"Unsupported backend: {eff_backend}. Use 'nim', 'local', or 'api'.")
