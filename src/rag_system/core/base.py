import os
from config.settings import settings
from abc import ABC, abstractmethod
from typing import Any, Iterator, List, Optional
from langchain_ollama import OllamaEmbeddings
from pydantic import BaseModel


class Document(BaseModel):
    content: str
    metadata: dict = {}


class DocumentLoader():
    def load(self, source: str) -> List[Document]:
        list_of_docs = os.listdir(source)
        docs = []
        for doc in list_of_docs:
            with open(os.path.join(source, doc), "r", encoding="utf-8") as f:
                content = f.read()
                docs.append(Document(content=content, metadata={"source": doc}))
        return docs


class Embedder():
    def embed_text(self, text: str) -> List[float]:
        client = OllamaEmbeddings(model=settings.local_model)
        return client.embed_query(text)

    def embed_documents(self, documents: List[str]) -> List[List[float]]:
        client = OllamaEmbeddings(model=settings.local_model)
        return client.embed_documents(documents)

class VectorStore(ABC):
    @abstractmethod
    def add_documents(self, documents: List[Document]):
        pass

    @abstractmethod
    def search(
        self, query_vector: List[float], top_k: int = 5
    ) -> List[Document]:
        pass


class LLMInterface(ABC):
    @abstractmethod
    def generate(
        self,
        prompt: str,
        context: Optional[str] = None,
        max_new_tokens: int = 512,
    ) -> str:
        pass

    @abstractmethod
    def stream(
        self,
        prompt: str,
        context: Optional[str] = None,
        max_new_tokens: int = 512,
    ) -> Iterator[str]:
        pass

if __name__ == "__main__":
    # Example usage
    loader = DocumentLoader()
    docs = loader.load("../../../documents")
    print(docs[0].content)