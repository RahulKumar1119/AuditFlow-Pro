#!/bin/bash
# frontend/setup.sh
# Sets up Node.js frontend project and installs dependencies

set -e

echo "Setting up AuditFlow-Pro Frontend..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed."
    echo "Please install Node.js 18 or higher from https://nodejs.org/"
    exit 1
fi

NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
echo "Found Node.js version: v$(node --version)"

if [ "$NODE_VERSION" -lt 18 ]; then
    echo "Warning: Node.js version 18 or higher is recommended."
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "Error: npm is not installed."
    exit 1
fi

echo "Found npm version: $(npm --version)"

# Install dependencies
echo "Installing dependencies..."
npm install

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.template .env
    echo ""
    echo "WARNING: Please update .env with your AWS Cognito and API Gateway configuration!"
    echo "Run infrastructure/cognito_setup.sh to get the required values."
fi

echo ""
echo "Frontend setup completed successfully!"
echo "================================================"
echo "To start the development server, run:"
echo "  npm run dev"
echo ""
echo "To build for production, run:"
echo "  npm run build"
echo ""
echo "To run linting, run:"
echo "  npm run lint"
echo ""
echo "Don't forget to update .env with your AWS configuration!"
echo "================================================"
