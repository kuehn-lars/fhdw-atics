from typing import List

from langchain_openai import OpenAIEmbeddings

from src.rag_system.core.base import Embedder


class OpenAIEmbeddingsModule(Embedder):
    def __init__(self, api_key: str):
        self.embedder = OpenAIEmbeddings(openai_api_key=api_key)

    def embed_text(self, text: str) -> List[float]:
        return self.embedder.embed_query(text)

    def embed_documents(self, documents: List[str]) -> List[List[float]]:
        return self.embedder.embed_documents(documents)
