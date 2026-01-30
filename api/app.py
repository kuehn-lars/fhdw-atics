from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
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
    stream: bool = True
    backend: Optional[str] = None
    model: Optional[str] = None
    max_new_tokens: int = 512


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
