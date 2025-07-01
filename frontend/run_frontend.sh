#!/bin/bash

# LyBot Frontend Startup Script

echo "Starting LyBot Frontend..."

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Start the development server
echo "Starting development server..."
echo "Frontend will be available at http://localhost:5173"
echo "Make sure the LyBot API is running at http://localhost:8000"
echo "Press Ctrl+C to stop the server"

npm run dev