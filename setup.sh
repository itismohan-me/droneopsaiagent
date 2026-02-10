#!/bin/bash
# Quick start script for Drone Operations Coordinator

set -e

echo "🚁 Skylark Drones - Operations Coordinator"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "✓ Python $python_version"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python -m venv venv
    echo "✓ Virtual environment created"
fi

# Activate venv
echo ""
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -q -r requirements.txt
echo "✓ Dependencies installed"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo ""
    echo "Creating .env file..."
    cp .env.example .env
    echo "✓ .env file created - review and update as needed"
fi

# Display instructions
echo ""
echo "=========================================="
echo "✓ Setup complete!"
echo ""
echo "To start the application:"
echo ""
echo "  Terminal 1 - Backend:"
echo "    python main.py"
echo ""
echo "  Terminal 2 - Frontend:"
echo "    streamlit run app.py"
echo ""
echo "Then open:"
echo "  - Backend API docs: http://localhost:8000/docs"
echo "  - Frontend: http://localhost:8501"
echo ""
echo "=========================================="
