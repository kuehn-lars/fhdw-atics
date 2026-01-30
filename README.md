# Modular AI RAG Repository

A modular and extensible framework for experimenting with **Large Language Models (LLMs)** in combination with **Retrieval-Augmented Generation (RAG)** techniques.

This project was developed as a proof of concept within the *Advanced Topics in Computer Science* module at the **Fachhochschule der Wirtschaft (FHDW)**. It demonstrates modern LLM-based system design, modular RAG pipelines, and a complete full-stack integration including API, CLI, and web frontend.

---

## Overview

The repository is designed to be **clean, extensible, and experimentation-friendly**.
Core concerns—data ingestion, embeddings, retrieval, orchestration, and user interaction—are clearly separated and can be independently extended or replaced.

This project can be used to:
- Prototype and evaluate RAG pipelines
- Compare embedding models and vector stores
- Integrate LLMs into APIs and web applications
- Explore modern UI patterns for LLM-powered chat interfaces
- Serve as an academic or architectural reference implementation

---

## Features

- **Modular Architecture**
  Implement custom loaders, embedders, retrievers, and vector stores by inheriting from abstract base classes.

- **Command-Line Interface (CLI)**
  Ingest data and query the system using a clean and extensible CLI built with *Typer*.

- **FastAPI Backend**
  A production-ready API layer suitable for frontend integration and programmatic access.

- **Configuration Management**
  Environment-based configuration using *Pydantic Settings*.

- **Modern Web Frontend**
  A polished Next.js application providing a chat-based interface for interacting with the LLM.

---

## Project Structure

```text
.
├── api/                   # FastAPI application
├── cli/                   # Command-line interface
├── config/                # Configuration and settings
├── frontend/              # Next.js / React web application
│   ├── src/app/
│   │   ├── globals.css    # Tailwind v4 & design tokens
│   │   └── page.tsx       # Main chat component
│   └── tailwind.config.ts
├── src/
│   └── rag_system/
│       ├── core/          # Abstract base classes
│       ├── orchestration/ # RAG pipeline logic
│       └── modules/       # Concrete module implementations
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

   Start the FastAPI backend:
   ```bash
   uvicorn api.app:app --reload
   ```
   Interactive API documentation is available at:
   - http://localhost:8000/docs

5. **Run Web Frontend**

   ```bash
   cd frontend

   # Install dependencies
   npm install

   # Start development server
   npm run dev
   ```
   This web application will be available at:
   - http://localhost:3000
