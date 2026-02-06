from typing import List

import chromadb

from config.settings import settings
from src.rag_system.core.base import Document, VectorStore, Embedder


class ChromaVectorStore(VectorStore):
    def __init__(self, path: str):
        self.client = chromadb.PersistentClient(path=path)
        self.collection = self.client.get_or_create_collection(
            "rag_collection"
        )

    def add_documents(self, documents: List[Document]):
        embedder = Embedder()
        texts = [doc.content for doc in documents]
        embeddings = embedder.embed_documents(texts)

        self.collection.add(
            documents=texts,
            metadatas=[doc.metadata for doc in documents],
            embeddings=embeddings,
            ids=[f"id_{i}" for i in range(len(documents))]
        )

    def search(
        self, query_vector: List[float], top_k: int = 5
    ) -> List[Document]:
        # Note: This is an implementation detail. Chroma can handle vectors or strings.
        # For simplicity, we assume query_vector is used for searching.
        results = self.collection.query(
            query_embeddings=[query_vector], n_results=top_k
        )
        docs = []
        for i in range(len(results["documents"][0])):
            docs.append(
                Document(
                    content=results["documents"][0][i],
                    metadata=results["metadatas"][0][i],
                )
            )
        return docs
