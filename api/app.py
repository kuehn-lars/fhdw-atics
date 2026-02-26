from typing import Optional, List
import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config.settings import settings
from src.rag_system.orchestration.factory import get_rag_pipeline

app = FastAPI(title=settings.app_name)

# CORS for Next.js Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    Endpoint to upload files (PDFs, TXT, etc.) to the RAG vector store.
    """
    pipeline = get_rag_pipeline()
    try:
        results = []
        for file in files:
            # Read file content
            content = await file.read()
            
            # Pass to your pipeline logic
            # Note: You might need to save to a temp file or pass bytes 
            # depending on how your get_rag_pipeline is implemented.
            status = pipeline.ingest(
                file_name=file.filename,
                content=content,
                collection=collection_name
            )
            results.append({"file": file.filename, "status": "success"})
            
        return {"message": "Ingestion complete", "details": results}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

@app.post("/query")
async def query_endpoint(request: QueryRequest):
    try:
        # Pipeline loads defaults from settings
        pipeline = get_rag_pipeline()

        if request.stream:
            return StreamingResponse(
                pipeline.stream_query(
                    request.question, use_rag=request.use_rag
                ),
                media_type="text/plain",
            )
        else:
            answer = pipeline.query(request.question, use_rag=request.use_rag)
            return {"answer": answer}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
