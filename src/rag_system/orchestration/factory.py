from typing import Any, Optional

from config.settings import settings
from src.llm_backend.manager import LLMManager
from src.rag_system.modules.embeddings_openai import OpenAIEmbeddingsModule
from src.rag_system.modules.vector_store_chroma import ChromaVectorStore
from src.rag_system.orchestration.pipeline import RAGPipeline


def get_rag_pipeline(
    backend_mode: Optional[str] = None, model_name: Optional[str] = None
) -> RAGPipeline:
    vector_store = ChromaVectorStore(path=settings.vector_db_path)

    # Get LLM via the dedicated backend manager
    llm = LLMManager.get_llm(backend_mode=backend_mode, model_name=model_name)

    # Handle Embeddings
    if settings.backend_mode == "api" or settings.backend_mode == "nvidia":
        if not settings.openai_api_key:
            # Fallback or error if no embedding key
            embedder = None
        else:
            embedder = OpenAIEmbeddingsModule(api_key=settings.openai_api_key)
    else:
        from langchain_ollama import OllamaEmbeddings

        class LocalEmbedderModule:
            def __init__(self):
                self.embedder = OllamaEmbeddings(model=settings.local_model)

            def embed_text(self, text):
                return self.embedder.embed_query(text)

            def embed_documents(self, docs):
                return self.embedder.embed_documents(docs)

        embedder = LocalEmbedderModule()

    return RAGPipeline(embedder=embedder, vector_store=vector_store, llm=llm)
