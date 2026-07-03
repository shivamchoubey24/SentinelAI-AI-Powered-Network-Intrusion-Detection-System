#!/bin/bash

# Quick Start Script for AI-Powered Network Security System
# Run this script to quickly start the dashboard after initial setup

echo "=================================================="
echo "AI-Powered Network Security System"
echo "Quick Start Script"
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

# Check if .env file exists
if [ ! -f "config/.env" ]; then
    echo "⚠️  Warning: config/.env not found"
    echo "Copying from .env.example..."
    cp config/.env.example config/.env
    echo "⚠️  Please edit config/.env and add your API keys!"
    echo ""
fi

# Check if data directories exist
if [ ! -d "data/raw/firewall" ]; then
    echo "📊 Creating sample data..."
    python scripts/init_database.py
    python scripts/download_datasets.py
fi

echo ""
echo "🚀 Starting Streamlit Dashboard..."
echo "=================================================="
echo ""
echo "Dashboard will open at: http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the dashboard"
echo ""
echo "=================================================="
echo ""

# Start Streamlit dashboard
streamlit run src/dashboard/app.py
