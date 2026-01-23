from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from config.settings import settings

from src.rag_system.orchestration.factory import get_rag_pipeline

app = FastAPI(title=settings.app_name)

class QueryRequest(BaseModel):
    question: str
    use_rag: bool = True

class QueryResponse(BaseModel):
    answer: str
    context: Optional[str] = None

@app.post("/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    """
    FastAPI endpoint for querying the RAG system.
    """
    try:
        pipeline = get_rag_pipeline()
        answer = pipeline.query(request.question, use_rag=request.use_rag)
        return QueryResponse(answer=answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
