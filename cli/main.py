import json
import sys
import subprocess
from typing import Optional

import typer

from config.settings import settings
from src.rag_system.orchestration.factory import get_rag_pipeline
from src.rag_system.modules.vector_store_chroma import ChromaVectorStore
from src.rag_system.core.base import DocumentLoader

app = typer.Typer()


@app.command()
def setup():
    """
    Download/Pull required Ollama models.
    """
    models = ["qwen2.5:0.5b", "llama3.2:1b", "llama3:8b", "qwen2.5:3b"]

    typer.echo("------------------------------------------")
    typer.echo("Starting Ollama model setup...")
    typer.echo("------------------------------------------")

    for model in models:
        typer.echo(f">>> Pulling model: {model}")
        try:
            subprocess.run(["ollama", "pull", model], check=True)
        except subprocess.CalledProcessError:
            typer.echo(
                f"Error: Could not pull model {model}. Is Ollama running?"
            )
        except FileNotFoundError:
            typer.echo(
                "Error: 'ollama' command not found. Please install Ollama first."
            )
            break

    typer.echo("------------------------------------------")
    typer.echo("Ollama setup complete!")
    typer.echo("------------------------------------------")


@app.command()
def query(
    question: str,
    use_rag: bool = typer.Option(True, help="Toggle RAG on or off"),
    stream: bool = typer.Option(True, help="Toggle streaming output"),
    backend: Optional[str] = typer.Option(
        None, help="Override backend mode (api, local, nvidia)"
    ),
    model: Optional[str] = typer.Option(None, help="Override model name"),
    max_tokens: int = typer.Option(
        512, help="Maximum number of tokens to generate"
    ),
):
    """
    Ask a question to the RAG system via CLI.
    """
    pipeline = get_rag_pipeline()
    mode = backend or ("RAG" if use_rag else "Direct LLM")
    typer.echo(f"Querying ({mode}) for: {question}")

    try:
        if stream:
            typer.echo("Answer: ", nl=False)
            for chunk in pipeline.stream_query(question, use_rag=use_rag):
                typer.echo(chunk, nl=False)
            typer.echo()  # Newline at the end
        else:
            response = pipeline.query(question, use_rag=use_rag)
            typer.echo(f"Answer: {response}")

    except Exception as e:
        typer.echo(f"Error: {e}")


@app.command()
def ingest(source: str):
    """
    Ingest a document or directory into the RAG system.
    """
    typer.echo(f"Ingesting source: {source}")


@app.command()
def setup_vector_store():
    """
    Set up the vector store by ingesting documents from the specified path.
    """
    vector_store = ChromaVectorStore(path=settings.vector_db_path)
    vector_store.add_documents(DocumentLoader().load(settings.documents_path))


@app.command()
def agents(
    question: str = typer.Argument(..., help="Die Frage an die CrewAI-Agenten"),
    json_output: bool = typer.Option(False, "--json", help="Ausgabe als JSON"),
):
    """
    Führe die CrewAI-Agenten aus und gib das Ergebnis als Text oder JSON aus.
    """
    sys.path.insert(0, ".")
    try:
        from workshops.crewai_intro.agents_challenge1 import run_challenge
    except ImportError as e:
        typer.echo(f"Import-Fehler: {e}", err=True)
        raise typer.Exit(1)

    typer.echo(f"🤖 Starte Agenten für: {question}")
    try:
        result = run_challenge(question)
        answer = str(result)

        if json_output:
            payload = json.dumps({"type": "result", "answer": answer}, ensure_ascii=False, indent=2)
            typer.echo(payload)
        else:
            typer.echo("\n" + "="*60)
            typer.echo("📝 ANTWORT DER AGENTEN:")
            typer.echo("-"*60)
            typer.echo(answer)
            typer.echo("="*60)
    except Exception as e:
        if json_output:
            typer.echo(json.dumps({"type": "error", "message": str(e)}))
        else:
            typer.echo(f"Fehler: {e}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
