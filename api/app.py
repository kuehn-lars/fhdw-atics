import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import control
from config.settings import settings

app = FastAPI(title=settings.app_name)

class QueryRequest(BaseModel):
    question: str
    use_rag: bool = True
    stream: bool = False
    backend: Optional[str] = None
    model: Optional[str] = None
    max_new_tokens: int = 512

class QueryResponse(BaseModel):
    answer: str
    context: Optional[str] = None

@app.post("/query")
async def query_endpoint(request: QueryRequest):
    """
    FastAPI endpoint for querying the RAG system.
    
    This endpoint allows clients to send questions to the LLM backend, 
    with optional RAG context retrieval, streaming output, and model/backend overrides.

    Parameters (passed via QueryRequest JSON body):
    -----------------------------------------------
    question : str
        The query string or prompt to send to the assistant.
    
    use_rag : bool, default=True
        Toggle whether the system should search for relevant local documents 
        to provide context to the LLM.
    
    stream : bool, default=False
        If True, the endpoint returns a `StreamingResponse` that yields the LLM 
        output token by token (text/plain).
        If False, it returns a standard JSON `QueryResponse`.
    
    backend : str, optional
        Override the default backend mode ('api', 'local', 'nvidia').
    
    model : str, optional
        Override the default model name or path.

    max_new_tokens : int, default=512
        The maximum number of tokens to generate.

    Returns:
    --------
    - JSON (QueryResponse): If stream=False.
    - Stream (text/plain): If stream=True.
    """
    try:
        response = control.query(
            question=request.question,
            use_rag=request.use_rag,
            stream=request.stream,
            backend=request.backend,
            model=request.model,
            max_new_tokens=request.max_new_tokens
        )
        
        if request.stream:
            def stream_generator():
                for chunk in response:
                    yield chunk
            return StreamingResponse(stream_generator(), media_type="text/plain")
        else:
            return QueryResponse(answer=response)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
