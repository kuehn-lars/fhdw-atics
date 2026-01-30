from typing import Optional

import typer

from config.settings import settings
from src.rag_system.orchestration.factory import get_rag_pipeline

app = typer.Typer()


@app.command()
def query(
    question: str,
    use_rag: bool = typer.Option(True, help="Toggle RAG on or off"),
    stream: bool = typer.Option(True, help="Toggle streaming output"),
    backend: Optional[str] = typer.Option(
        None, help="Override backend mode (api, local, nvidia)"
    ),
    model: Optional[str] = typer.Option(None, help="Override model name"),
):
    """
    Ask a question to the RAG system via CLI.
    """
    mode = backend or ("RAG" if use_rag else "Direct LLM")
    typer.echo(f"Querying ({mode}) for: {question}")
    try:
        pipeline = get_rag_pipeline(backend_mode=backend, model_name=model)
        if stream:
            typer.echo("Answer: ", nl=False)
            for chunk in pipeline.stream_query(question, use_rag=use_rag):
                typer.echo(chunk, nl=False)
            typer.echo()  # Newline at the end
        else:
            answer = pipeline.query(question, use_rag=use_rag)
            typer.echo(f"Answer: {answer}")
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
