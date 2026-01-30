from typing import Iterator, List

from src.rag_system.core.base import (
    Document,
    Embedder,
    LLMInterface,
    VectorStore,
)


class RAGPipeline:
    def __init__(
        self, embedder: Embedder, vector_store: VectorStore, llm: LLMInterface
    ):
        self.embedder = embedder
        self.vector_store = vector_store
        self.llm = llm
        
    def query(self, user_query: str, use_rag: bool = True, max_new_tokens: int = 512) -> str:
        if use_rag:
            query_vector = self.embedder.embed_text(user_query)
            relevant_docs = self.vector_store.search(query_vector)
            context = "\n".join([doc.content for doc in relevant_docs])
        else:
            context = None
            
        return self.llm.generate(user_query, context=context, max_new_tokens=max_new_tokens)

    def stream_query(self, user_query: str, use_rag: bool = True, max_new_tokens: int = 512) -> Iterator[str]:
        if use_rag:
            query_vector = self.embedder.embed_text(user_query)
            relevant_docs = self.vector_store.search(query_vector)
            context = "\n".join([doc.content for doc in relevant_docs])
        else:
            context = None
            
        return self.llm.stream(user_query, context=context, max_new_tokens=max_new_tokens)
