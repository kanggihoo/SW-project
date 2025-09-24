#!/bin/bash

# Activate virtual environment
. ./.venv/bin/activate

# Run FastAPI server
uv run python3 run_server.py
