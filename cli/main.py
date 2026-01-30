import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

import typer
from typing import Optional
import control

app = typer.Typer()

@app.command()
def setup():
    """
    Download/Pull required Ollama models.
    """
    control.setup()

@app.command()
def query(
    question: str, 
    use_rag: bool = typer.Option(True, help="Toggle RAG on or off"),
    stream: bool = typer.Option(True, help="Toggle streaming output"),
    backend: Optional[str] = typer.Option(None, help="Override backend mode (api, local, nvidia)"),
    model: Optional[str] = typer.Option(None, help="Override model name")
):
    """
    Ask a question to the RAG system via CLI.
    """
    mode = backend or ("RAG" if use_rag else "Direct LLM")
    typer.echo(f"Querying ({mode}) for: {question}")
    
    try:
        response = control.query(
            question=question, 
            use_rag=use_rag, 
            stream=stream, 
            backend=backend, 
            model=model
        )
        
        if stream:
            typer.echo("Answer: ", nl=False)
            for chunk in response:
                typer.echo(chunk, nl=False)
            typer.echo() # Newline at the end
        else:
            typer.echo(f"Answer: {response}")
            
    except Exception as e:
        typer.echo(f"Error: {e}")


@app.command()
def ingest(source: str):
    """
    Ingest a document or directory into the RAG system.
    """
    typer.echo(f"Ingesting source: {source}")

if __name__ == "__main__":
    app()
