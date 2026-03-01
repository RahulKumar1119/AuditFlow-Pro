#!/bin/bash

# AuditFlow-Pro Deployment Pre-flight Check Script
# This script verifies that the application is ready for deployment

set -e

echo "🚀 AuditFlow-Pro Deployment Pre-flight Check"
echo "=============================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Node.js version
echo "📦 Checking Node.js version..."
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -ge 20 ]; then
    echo -e "${GREEN}✓${NC} Node.js version: $(node -v)"
else
    echo -e "${RED}✗${NC} Node.js version $(node -v) is too old. Required: >= 20.0.0"
    exit 1
fi
echo ""

# Check if dependencies are installed
echo "📚 Checking dependencies..."
if [ -d "node_modules" ]; then
    echo -e "${GREEN}✓${NC} Dependencies installed"
else
    echo -e "${YELLOW}⚠${NC} Dependencies not installed. Running npm ci..."
    npm ci
fi
echo ""

# Run linter
echo "🔍 Running linter..."
if npm run lint; then
    echo -e "${GREEN}✓${NC} Linting passed"
else
    echo -e "${RED}✗${NC} Linting failed. Please fix errors before deploying."
    exit 1
fi
echo ""

# Run tests
echo "🧪 Running tests..."
if npm test; then
    echo -e "${GREEN}✓${NC} All tests passed"
else
    echo -e "${RED}✗${NC} Tests failed. Please fix failing tests before deploying."
    exit 1
fi
echo ""

# Build the application
echo "🏗️  Building application..."
if npm run build; then
    echo -e "${GREEN}✓${NC} Build successful"
else
    echo -e "${RED}✗${NC} Build failed. Please fix build errors before deploying."
    exit 1
fi
echo ""

# Check build output size
echo "📊 Analyzing build output..."
DIST_SIZE=$(du -sh dist | cut -f1)
echo "   Total build size: $DIST_SIZE"

# Check for large chunks
echo "   Checking chunk sizes..."
find dist/assets -name "*.js" -type f -exec ls -lh {} \; | awk '{if ($5 ~ /M/ && $5+0 > 1) print "   ⚠ Large chunk: " $9 " (" $5 ")"}'

# Count files
JS_COUNT=$(find dist/assets -name "*.js" | wc -l)
CSS_COUNT=$(find dist/assets -name "*.css" | wc -l)
echo "   JavaScript files: $JS_COUNT"
echo "   CSS files: $CSS_COUNT"
echo ""

# Check environment variables template
echo "🔐 Checking environment configuration..."
if [ -f ".env.template" ]; then
    echo -e "${GREEN}✓${NC} Environment template exists"
    echo "   Required environment variables:"
    grep -v '^#' .env.template | grep '=' | cut -d'=' -f1 | sed 's/^/   - /'
else
    echo -e "${YELLOW}⚠${NC} No .env.template found"
fi
echo ""

# Check for common issues
echo "🔎 Checking for common issues..."

# Check for console.log statements (should be removed in production)
CONSOLE_COUNT=$(find src -name "*.tsx" -o -name "*.ts" | xargs grep -l "console\." | wc -l)
if [ "$CONSOLE_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}⚠${NC} Found $CONSOLE_COUNT files with console statements (will be removed in production build)"
fi

# Check for TODO comments
TODO_COUNT=$(find src -name "*.tsx" -o -name "*.ts" | xargs grep -i "TODO" | wc -l)
if [ "$TODO_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}⚠${NC} Found $TODO_COUNT TODO comments"
fi

# Check for debugger statements
DEBUGGER_COUNT=$(find src -name "*.tsx" -o -name "*.ts" | xargs grep -l "debugger" | wc -l)
if [ "$DEBUGGER_COUNT" -gt 0 ]; then
    echo -e "${RED}✗${NC} Found $DEBUGGER_COUNT files with debugger statements"
    exit 1
fi

echo ""

# Summary
echo "=============================================="
echo -e "${GREEN}✓ Pre-flight check completed successfully!${NC}"
echo ""
echo "Next steps:"
echo "1. Commit and push your changes to trigger deployment"
echo "2. Monitor the build in AWS Amplify Console"
echo "3. Verify deployment at https://auditflowpro.online"
echo ""
echo "For detailed deployment instructions, see:"
echo "  ../AMPLIFY_DEPLOYMENT.md"
echo ""
