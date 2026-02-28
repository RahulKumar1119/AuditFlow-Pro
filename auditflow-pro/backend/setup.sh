#!/bin/bash
# backend/setup.sh
# Sets up Python virtual environment and installs dependencies

set -e

echo "Setting up AuditFlow-Pro Backend..."

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Found Python version: $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists."
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

# Create package directory if it doesn't exist
if [ ! -d "package" ]; then
    echo "Creating package directory for Lambda deployment..."
    mkdir -p package
fi

# Install dependencies to package directory for Lambda deployment
echo "Installing dependencies to package directory..."
pip install -r requirements.txt -t package/

echo ""
echo "Backend setup completed successfully!"
echo "================================================"
echo "To activate the virtual environment, run:"
echo "  source venv/bin/activate"
echo ""
echo "To run tests, run:"
echo "  pytest tests/"
echo ""
echo "To deactivate the virtual environment, run:"
echo "  deactivate"
echo "================================================"
