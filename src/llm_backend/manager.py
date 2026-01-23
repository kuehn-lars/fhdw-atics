from config.settings import settings
from src.rag_system.core.base import LLMInterface
from src.llm_backend.modules.llm_openai import OpenAIModule
from src.llm_backend.modules.llm_local import LocalLLMModule
from src.llm_backend.modules.llm_nvidia import NVIDIAModule

class LLMManager:
    @staticmethod
    def get_llm() -> LLMInterface:
        if settings.backend_mode == "api":
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY must be set for API mode.")
            return OpenAIModule(api_key=settings.openai_api_key, model_name=settings.openai_model)
        
        elif settings.backend_mode == "nvidia":
            if not settings.nvidia_api_key:
                raise ValueError("NVIDIA_API_KEY must be set for NVIDIA mode.")
            return NVIDIAModule(api_key=settings.nvidia_api_key, model_name=settings.nvidia_model)
            
        else:
            return LocalLLMModule(model_name=settings.local_model)
