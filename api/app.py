from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from config.settings import settings

from src.rag_system.orchestration.factory import get_rag_pipeline

app = FastAPI(title=settings.app_name)

class QueryRequest(BaseModel):
    question: str
    use_rag: bool = True
    stream: bool = False
    backend: Optional[str] = None
    model: Optional[str] = None

class QueryResponse(BaseModel):
    answer: str
    context: Optional[str] = None

@app.post("/query")
async def query_endpoint(request: QueryRequest):
    """
    FastAPI endpoint for querying the RAG system.
    Supports optional streaming and model/backend overrides.
    """
    try:
        pipeline = get_rag_pipeline(backend_mode=request.backend, model_name=request.model)
        
        if request.stream:
            def stream_generator():
                for chunk in pipeline.stream_query(request.question, use_rag=request.use_rag):
                    yield chunk
            return StreamingResponse(stream_generator(), media_type="text/plain")
        else:
            answer = pipeline.query(request.question, use_rag=request.use_rag)
            return QueryResponse(answer=answer)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
