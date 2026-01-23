from typing import Optional
from langchain_community.llms import Ollama
from src.rag_system.core.base import LLMInterface

class LocalLLMModule(LLMInterface):
    def __init__(self, model_name: str = "llama3"):
        self.llm = Ollama(model=model_name)
    
    def generate(self, prompt: str, context: Optional[str] = None) -> str:
        full_prompt = f"Context: {context}\n\nQuestion: {prompt}" if context else prompt
        return self.llm.invoke(full_prompt)
