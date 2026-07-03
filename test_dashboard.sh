#!/bin/bash

# Test script for dashboard functionality

echo "🧪 Testing Dashboard Functionality"
echo "=================================="
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    exit 1
fi

# Activate venv
source venv/bin/activate

# Check if data exists, if not generate it
if [ ! -d "data/raw" ] || [ -z "$(ls -A data/raw 2>/dev/null)" ]; then
    echo "📦 Generating sample data..."
    python scripts/download_datasets.py
    echo "✅ Sample data generated"
else
    echo "✅ Sample data already exists"
fi

# Initialize directories if needed
echo ""
echo "📁 Checking directories..."
python scripts/init_database.py

echo ""
echo "✅ All checks passed!"
echo ""
echo "🚀 Starting dashboard..."
echo "   - Auto-refresh: Enable the checkbox at top-right"
echo "   - ETL Pipeline: Click 'Run ETL Pipeline' button"
echo "   - Upload Files: Go to Threat Detection page"
echo ""

# Start dashboard
streamlit run src/dashboard/app_simple.py
