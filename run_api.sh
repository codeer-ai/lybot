#!/bin/bash

# LyBot API Server Startup Script

echo "Starting LyBot API Server..."

# Check if GOOGLE_API_KEY is set
if [ -z "$GOOGLE_API_KEY" ]; then
    echo "Warning: GOOGLE_API_KEY environment variable is not set"
    echo "The API will not work without it. Please set it with:"
    echo "export GOOGLE_API_KEY='your-api-key'"
    exit 1
fi

# Install dependencies if needed
echo "Checking dependencies..."
uv sync

# Run the API server
echo "Starting server on http://localhost:8000"
echo "API documentation available at http://localhost:8000/docs"
echo "Press Ctrl+C to stop the server"

# Run with uvicorn
uv run uvicorn api:app --host 0.0.0.0 --port 8000 --reload