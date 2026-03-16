from typing import Iterator, Optional

from langchain_nvidia_ai_endpoints import ChatNVIDIA

from src.rag_system.core.base import LLMInterface


class NVIDIAModule(LLMInterface):
    def __init__(
        self, api_key: str, model_name: str = "qwen/qwen3.5-122b-a10b"
    ):
        # Update to support NVIDIA NIM API structure
        self.llm = ChatNVIDIA(
            nvidia_api_key=api_key, 
            model=model_name,
            base_url="https://integrate.api.nvidia.com/v1",
            max_tokens=16384,
            temperature=0.6,
            top_p=0.95,
            extra_body={"chat_template_kwargs": {"enable_thinking": True}}
        )

    def generate(
        self,
        prompt: str,
        context: Optional[str] = None,
        max_new_tokens: int = 512,
    ) -> str:
        full_prompt = (
            f"Context: {context}\n\nQuestion: {prompt}" if context else prompt
        )
        return self.llm.invoke(full_prompt, max_tokens=max_new_tokens).content

    def stream(
        self,
        prompt: str,
        context: Optional[str] = None,
        max_new_tokens: int = 512,
    ) -> Iterator[str]:
        full_prompt = (
            f"Context: {context}\n\nQuestion: {prompt}" if context else prompt
        )
        for chunk in self.llm.stream(full_prompt, max_tokens=max_new_tokens):
            yield str(chunk.content)
