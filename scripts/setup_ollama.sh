#!/bin/bash

# Ollama Model Setup Script
# This script automates the pulling of models required for the ATICS project.

# Mapping from Hugging Face / requested names to Ollama library tags:
# 1. Qwen/Qwen2.5-0.5B-Instruct -> qwen2.5:0.5b
# 2. meta-llama/Llama-3.2-1B-Instruct -> llama3.2:1b
# 3. meta-llama/Meta-Llama-3-8B-Instruct -> llama3:8b
# 4. Qwen/Qwen3-4B-Instruct-2507 -> qwen2.5:3b (Placeholder for Qwen3)

MODELS=(
    "qwen2.5:0.5b"
    "llama3.2:1b"
    "llama3:8b"
    "qwen2.5:3b"
)

echo "------------------------------------------"
echo "Starting Ollama model setup..."
echo "------------------------------------------"

# Ensure ollama is running (simple check)
if ! pgrep -x "ollama" > /dev/null && ! command -v ollama > /dev/null; then
    echo "Error: Ollama is not installed or not in PATH."
    exit 1
fi

for model in "${MODELS[@]}"; do
    echo ">>> Pulling model: $model"
    ollama pull "$model"
done

echo "------------------------------------------"
echo "Ollama setup complete!"
echo "------------------------------------------"
echo "You can now use these models in the RAG system, for example:"
echo "python cli/main.py query \"Hello\" --backend local --model qwen2.5:0.5b"
