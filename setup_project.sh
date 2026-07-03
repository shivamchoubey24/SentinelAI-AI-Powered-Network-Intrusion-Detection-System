#!/bin/bash

# AI-Powered Network Security System - Setup Script
# This script sets up the Python virtual environment and installs all dependencies

set -e  # Exit on error

echo "=================================="
echo "Network Security System - Setup"
echo "=================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed. Please install Python 3.10 or higher.${NC}"
    exit 1
fi

# Get Python version
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo -e "${BLUE}Found Python version: $PYTHON_VERSION${NC}"

# Check if virtual environment already exists
if [ -d "venv" ]; then
    echo -e "${BLUE}Virtual environment already exists. Skipping creation.${NC}"
else
    echo -e "${BLUE}Creating virtual environment...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source venv/bin/activate

# Upgrade pip
echo -e "${BLUE}Upgrading pip...${NC}"
pip install --upgrade pip

# Install dependencies
echo -e "${BLUE}Installing project dependencies...${NC}"
pip install -r requirements.txt

echo -e "${GREEN}✓ All dependencies installed${NC}"

# Create necessary directories
echo -e "${BLUE}Creating project directories...${NC}"
mkdir -p data/raw data/processed data/models
mkdir -p logs
mkdir -p outputs

echo -e "${GREEN}✓ Directories created${NC}"

# Copy environment file if it doesn't exist
if [ ! -f "config/.env" ]; then
    if [ -f "config/.env.example" ]; then
        cp config/.env.example config/.env
        echo -e "${BLUE}Created config/.env from template. Please edit it with your API keys.${NC}"
    fi
fi

echo ""
echo -e "${GREEN}=================================="
echo "Setup completed successfully!"
echo "==================================${NC}"
echo ""
echo "To activate the virtual environment, run:"
echo -e "${BLUE}source venv/bin/activate${NC}"
echo ""
echo "To start the dashboard, run:"
echo -e "${BLUE}streamlit run src/dashboard/app.py${NC}"
echo ""
echo "Don't forget to configure your API keys in config/.env"
echo ""
