import os

# Disable CrewAI telemetry (prevents timeout to app.crewai.com)
os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"

import asyncio
import json
import queue
import sys
import threading
from typing import Optional, List

import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config.settings import settings
from src.rag_system.orchestration.factory import get_rag_pipeline
from api.agents_router import router as agents_router

app = FastAPI(title=settings.app_name)

# CORS for Next.js Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Agents SSE-Router (Challenge 1–4 + JSON) ───────────────────────────────
app.include_router(agents_router)


# ── Bestehender RAG-Endpoint (unverändert) ────────────────────────────────
class QueryRequest(BaseModel):
    question: str
    use_rag: bool = True
    stream: bool = False
    backend: Optional[str] = None
    model: Optional[str] = None
    max_new_tokens: int = 512


@app.post("/ingest")
async def ingest_documents(
    files: List[UploadFile] = File(...),
    collection_name: Optional[str] = Form(None)
):
    """
    Endpoint to upload files (PDFs, TXT, etc.) to the RAG vector store
    and persist them in a specific folder on disk.
    """

    pipeline = get_rag_pipeline()

    # Zielordner definieren (z.B. konfigurierbar machen)
    upload_dir = settings.documents_path
    os.makedirs(upload_dir, exist_ok=True)

    try:
        results = []

        for file in files:
            # Dateiinhalt lesen
            content = await file.read()

            # Speicherpfad erzeugen
            file_path = os.path.join(upload_dir, file.filename)

            # Datei physisch speichern
            with open(file_path, "wb") as f:
                f.write(content)

            # Danach wie bisher in Pipeline ingestieren
            status = pipeline.ingest(
                file_name=file.filename,
                content=content,
                collection=collection_name
            )

            results.append({
                "file": file.filename,
                "saved_to": file_path,
                "status": "success"
            })

        return {
            "message": "Ingestion complete",
            "saved_directory": upload_dir,
            "details": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

@app.post("/query")
async def query_endpoint(request: QueryRequest):
    try:
        pipeline = get_rag_pipeline()
        if request.stream:
            return StreamingResponse(
                pipeline.stream_query(request.question, use_rag=request.use_rag),
                media_type="text/plain",
            )
        else:
            answer = pipeline.query(request.question, use_rag=request.use_rag)
            return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)