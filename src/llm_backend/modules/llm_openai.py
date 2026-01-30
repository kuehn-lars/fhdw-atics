from typing import Iterator, Optional

from langchain_openai import ChatOpenAI

from src.rag_system.core.base import LLMInterface


class OpenAIModule(LLMInterface):
    def __init__(self, api_key: str, model_name: str = "gpt-3.5-turbo"):
        self.llm = ChatOpenAI(openai_api_key=api_key, model=model_name)

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
