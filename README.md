# Modular AI RAG Repository

A modular framework for building Retrieval-Augmented Generation (RAG) systems. This repository provides clean abstractions for swapping components like LLMs, Vector Stores, and Embedders.

## Features
- **Modular Design**: Define your own loaders, embedders, and vector stores by inheriting from base classes.
- **CLI Interface**: Command-line tool for ingestion and querying built with Typer.
- **FastAPI Backend**: Ready-to-use API for frontend integration.
- **Pydantic Configuration**: Environment-based configuration management.

## Project Structure
```text
.
├── api/                # FastAPI application
├── cli/                # Command-line interface
├── config/             # Configuration settings
├── src/
│   └── rag_system/
│       ├── core/       # Abstract base classes
│       ├── orchestration/ # RAG logic
│       └── modules/    # Module implementations (Add your own!)
├── requirements.txt
└── README.md
```

## Getting Started

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   Create a `.env` file with your keys:
   ```env
   OPENAI_API_KEY=your_key_here
   ```

3. **Run CLI**:
   ```bash
   python -m cli.main --help
   ```

4. **Run API**:
   ```bash
   uvicorn api.app:app --reload
   ```

## Creating Custom Modules
Inherit from the base classes in `src/rag_system/core/base.py`:
- `DocumentLoader`
- `Embedder`
- `VectorStore`
- `LLMInterface`
