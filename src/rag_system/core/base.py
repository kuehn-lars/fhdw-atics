from abc import ABC, abstractmethod
from typing import List, Any, Optional, Iterator
from pydantic import BaseModel

class Document(BaseModel):
    content: str
    metadata: dict = {}

class DocumentLoader(ABC):
    @abstractmethod
    def load(self, source: str) -> List[Document]:
        pass

class Embedder(ABC):
    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        pass
    
    @abstractmethod
    def embed_documents(self, documents: List[str]) -> List[List[float]]:
        pass

class VectorStore(ABC):
    @abstractmethod
    def add_documents(self, documents: List[Document]):
        pass
    
    @abstractmethod
    def search(self, query_vector: List[float], top_k: int = 5) -> List[Document]:
        pass

class LLMInterface(ABC):
    @abstractmethod
    def generate(self, prompt: str, context: Optional[str] = None) -> str:
        pass

    @abstractmethod
    def stream(self, prompt: str, context: Optional[str] = None) -> Iterator[str]:
        pass
