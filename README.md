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

### Prerequisites

- Python 3.13 (required for compatibility)
- Node.js and npm

### Backend Setup

1. **Create Virtual Environment with Python 3.13**:
   ```bash
   rm -rf venv && py -3.13 -m venv venv
   ```

2. **Activate Virtual Environment**:
   ```bash
   # Git Bash / Linux / macOS
   source venv/Scripts/activate
   
   # Windows PowerShell
   .\venv\Scripts\Activate.ps1
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Ollama**:
   - Download from https://ollama.com/download
   - Install and start Ollama

5. **Pull the LLM Model**:
   ```bash
   ollama pull qwen2.5:0.5b
   ```

<!-- 6. **Configure Environment** (optional):
   Create a `.env` file with your API keys if using OpenAI or NVIDIA:
   ```env
   OPENAI_API_KEY=your_key_here
   NVIDIA_API_KEY=your_key_here
   ``` -->

6. **Test CLI**:
   ```bash
   python -m cli.main --help
   ```

7. **Start API Server**:
   ```bash
   uvicorn api.app:app --reload
   ```
   Interactive API documentation: http://localhost:8000/docs

### Frontend Setup

1. **Navigate to Frontend Directory**:
   ```bash
   cd frontend
   ```

2. **Install Dependencies**:
   ```bash
   npm install
   ```

3. **Start Development Server**:
   ```bash
   npm run dev
   ```
   
   Frontend will be available at: http://localhost:3000
   This web application will be available at:
   - http://localhost:3000
