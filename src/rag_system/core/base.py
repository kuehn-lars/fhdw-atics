import os

from langchain_text_splitters import MarkdownHeaderTextSplitter
from config.settings import settings
from abc import ABC, abstractmethod
from typing import Any, Iterator, List, Optional
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import MarkdownTextSplitter
from pydantic import BaseModel


class Document(BaseModel):
    content: str
    metadata: dict = {}


class DocumentLoader:
    def load(self, source: str) -> List[Document]:
        list_of_docs = os.listdir(source)
        docs = []

        for doc in list_of_docs:
            full_path = os.path.join(source, doc)

            if not os.path.isfile(full_path):
                continue

            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()

            splitter = MarkdownHeaderTextSplitter(
                headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")]
            )
            chunks = splitter.split_text(content)

            for chunk in chunks:
                docs.append(
                    Document(
                        content=chunk.page_content,
                        metadata={"source": doc, **chunk.metadata}
                    )
                )

        return docs


class Embedder():
    def embed_text(self, text: str) -> List[float]:
        client = OllamaEmbeddings(model=settings.embeddings_model)
        return client.embed_query(text)

    def embed_documents(self, documents: List[str]) -> List[List[float]]:
        client = OllamaEmbeddings(model=settings.embeddings_model)
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
    docs = loader.load(os.path.join(os.path.dirname(__file__), "../../../documents"))
    print(docs[0].content)