#!/bin/bash

echo "========================================"
echo "  ChatterBot MCP - Starting Server"
echo "========================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "ERROR: .env file not found!"
    echo "Please copy .env.example to .env and add your API keys"
    echo ""
    exit 1
fi

# Check if virtual environment exists
if [ ! -d venv ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo ""
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "Checking dependencies..."
pip install -q -r requirements.txt

echo ""
echo "========================================"
echo "  Starting FastAPI Server"
echo "========================================"
echo ""
echo "Server will start on: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server
python main.py
