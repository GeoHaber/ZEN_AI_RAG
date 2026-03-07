#!/bin/bash
# ZEN AI RAG — AI Chat Assistant
cd "$(dirname "$0")"
if [ -f ".venv/bin/python" ]; then
    .venv/bin/python zena_flet.py "$@"
else
    python3 zena_flet.py "$@"
fi
