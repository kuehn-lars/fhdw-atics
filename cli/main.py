import sys
import os
import subprocess
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
    models = [
        "qwen2.5:0.5b",
        "llama3.2:1b",
        "llama3:8b",
        "qwen2.5:3b"
    ]
    
    typer.echo("------------------------------------------")
    typer.echo("Starting Ollama model setup...")
    typer.echo("------------------------------------------")
    
    for model in models:
        typer.echo(f">>> Pulling model: {model}")
        try:
            subprocess.run(["ollama", "pull", model], check=True)
        except subprocess.CalledProcessError:
            typer.echo(f"Error: Could not pull model {model}. Is Ollama running?")
        except FileNotFoundError:
            typer.echo("Error: 'ollama' command not found. Please install Ollama first.")
            break

    typer.echo("------------------------------------------")
    typer.echo("Ollama setup complete!")
    typer.echo("------------------------------------------")

@app.command()
def query(
    question: str, 
    use_rag: bool = typer.Option(True, help="Toggle RAG on or off"),
    stream: bool = typer.Option(True, help="Toggle streaming output"),
    backend: Optional[str] = typer.Option(None, help="Override backend mode (api, local, nvidia)"),
    model: Optional[str] = typer.Option(None, help="Override model name"),
    max_tokens: int = typer.Option(512, help="Maximum number of tokens to generate")
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
            model=model,
            max_new_tokens=max_tokens
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
