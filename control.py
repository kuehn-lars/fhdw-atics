from typing import Optional, Iterator, Union
from src.rag_system.orchestration.factory import get_rag_pipeline

def query_rag(
    question: str, 
    use_rag: bool = True, 
    stream: bool = False, 
    backend: Optional[str] = None, 
    model: Optional[str] = None
) -> Union[str, Iterator[str]]:
    """
    High-level API to interact with the RAG system programmatically.
    
    This function encapsulates the logic used in the CLI and provides a clean entry point 
    for other scripts or applications.

    Parameters:
    -----------
    question : str
        The query or prompt to send to the LLM.
    
    use_rag : bool, default=True
        If True, the system will perform a vector search to find relevant context 
        and include it in the prompt. If False, the LLM is queried directly.
    
    stream : bool, default=False
        If True, the function returns an iterator that yields chunks of the response 
        in real-time. If False, it returns the complete response as a single string.
    
    backend : str, optional
        Override the default backend mode ('api', 'local', 'nvidia'). 
        If None, the value from `config.settings` is used.
    
    model : str, optional
        Override the default model name or path.
        Example: 'Qwen/Qwen2.5-0.5B-Instruct' or 'gpt-3.5-turbo'.

    Returns:
    --------
    Union[str, Iterator[str]]
        - If stream=False: Returns the complete answer as a string.
        - If stream=True: Returns an iterator yielding response tokens/chunks.

    Example Usage:
    --------------
    # 1. Simple synchronous query
    answer = query_rag("What is RAG?")
    print(answer)

    # 2. Local model with streaming
    for chunk in query_rag("Hello!", backend="local", stream=True):
        print(chunk, end="", flush=True)
    """
    
    # Initialize the pipeline with optional overrides
    pipeline = get_rag_pipeline(backend_mode=backend, model_name=model)
    
    if stream:
        # Returns an Iterator[str]
        return pipeline.stream_query(question, use_rag=use_rag)
    else:
        # Returns a single str
        return pipeline.query(question, use_rag=use_rag)

if __name__ == "__main__":
    # Example for quick testing
    print("Testing control.py API...")
    try:
        # Default behavior (uses config/settings.py)
        # Note: Will fail if OPENAI_API_KEY is not set and backend is 'api'
        response = query_rag("1+1", use_rag=False)
        print(f"Response: {response}")
    except Exception as e:
        print(f"Error during test: {e}")
        print("Tip: Make sure to set BACKEND_MODE=local in your .env or specify backend='local' in the call.")
