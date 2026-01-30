from typing import Optional

from config.settings import settings
from src.llm_backend.modules.llm_local import LocalLLMModule
from src.llm_backend.modules.llm_nvidia import NVIDIAModule
from src.llm_backend.modules.llm_openai import OpenAIModule
from src.rag_system.core.base import LLMInterface


class LLMManager:
    @staticmethod
    def get_llm(
        backend_mode: Optional[str] = None, model_name: Optional[str] = None
    ) -> LLMInterface:
        effective_backend = backend_mode or settings.backend_mode

        if effective_backend == "api":
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY must be set for API mode.")
            effective_model = model_name or settings.openai_model
            return OpenAIModule(
                api_key=settings.openai_api_key, model_name=effective_model
            )

        elif effective_backend == "nvidia":
            if not settings.nvidia_api_key:
                raise ValueError("NVIDIA_API_KEY must be set for NVIDIA mode.")
            effective_model = model_name or settings.nvidia_model
            return NVIDIAModule(
                api_key=settings.nvidia_api_key, model_name=effective_model
            )

        else:
            effective_model = model_name or settings.local_model
            return LocalLLMModule(model_name=effective_model)
