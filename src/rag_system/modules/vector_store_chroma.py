from typing import List

import chromadb

from src.rag_system.core.base import Document, VectorStore


class ChromaVectorStore(VectorStore):
    def __init__(self, path: str):
        self.client = chromadb.PersistentClient(path=path)
        self.collection = self.client.get_or_create_collection(
            "rag_collection"
        )

    def add_documents(self, documents: List[Document]):
        for i, doc in enumerate(documents):
            self.collection.add(
                documents=[doc.content],
                metadatas=[doc.metadata],
                ids=[f"id_{i}"],
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
