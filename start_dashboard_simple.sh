#!/bin/bash

# Quick Start Script for AI-Powered Network Security System Dashboard
# Uses simplified dashboard for faster loading

echo "=================================================="
echo "AI-Powered Network Security System"
echo "Starting Dashboard (Simplified Version)"
echo "=================================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run ./setup_project.sh first"
    exit 1
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Start the simplified dashboard
echo "🚀 Starting Streamlit dashboard..."
echo ""
echo "Dashboard will open in your browser at http://localhost:8501"
echo "Press Ctrl+C to stop the dashboard"
echo ""

streamlit run src/dashboard/app_simple.py
