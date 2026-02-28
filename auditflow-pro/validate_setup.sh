#!/bin/bash
# validate_setup.sh
# Validates that the AuditFlow-Pro project structure is correctly set up

set -e

echo "=========================================="
echo "AuditFlow-Pro Setup Validation"
echo "=========================================="
echo ""

ERRORS=0
WARNINGS=0

# Check Python
echo "Checking Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "✓ Python found: $PYTHON_VERSION"
else
    echo "✗ Python 3 not found"
    ERRORS=$((ERRORS + 1))
fi

# Check AWS CLI
echo ""
echo "Checking AWS CLI..."
if command -v aws &> /dev/null; then
    AWS_VERSION=$(aws --version)
    echo "✓ AWS CLI found: $AWS_VERSION"
else
    echo "✗ AWS CLI not found"
    ERRORS=$((ERRORS + 1))
fi

# Check Node.js (optional for backend-only setup)
echo ""
echo "Checking Node.js..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo "✓ Node.js found: $NODE_VERSION"
else
    echo "⚠ Node.js not found (required for frontend development)"
    WARNINGS=$((WARNINGS + 1))
fi

# Check npm (optional for backend-only setup)
echo ""
echo "Checking npm..."
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    echo "✓ npm found: v$NPM_VERSION"
else
    echo "⚠ npm not found (required for frontend development)"
    WARNINGS=$((WARNINGS + 1))
fi

# Check directory structure
echo ""
echo "Checking directory structure..."
REQUIRED_DIRS=(
    "backend"
    "backend/functions"
    "backend/shared"
    "backend/tests"
    "frontend"
    "frontend/src"
    "infrastructure"
)

for DIR in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$DIR" ]; then
        echo "✓ Directory exists: $DIR"
    else
        echo "✗ Directory missing: $DIR"
        ERRORS=$((ERRORS + 1))
    fi
done

# Check required files
echo ""
echo "Checking required files..."
REQUIRED_FILES=(
    "backend/requirements.txt"
    "backend/setup.sh"
    "frontend/package.json"
    "frontend/setup.sh"
    "infrastructure/deploy_all.sh"
    "infrastructure/deploy.sh"
    "infrastructure/iam_policies.sh"
    "infrastructure/cognito_setup.sh"
    ".env"
)

for FILE in "${REQUIRED_FILES[@]}"; do
    if [ -f "$FILE" ]; then
        echo "✓ File exists: $FILE"
    else
        echo "✗ File missing: $FILE"
        ERRORS=$((ERRORS + 1))
    fi
done

# Check if scripts are executable
echo ""
echo "Checking script permissions..."
SCRIPTS=(
    "backend/setup.sh"
    "frontend/setup.sh"
    "infrastructure/deploy_all.sh"
    "infrastructure/deploy.sh"
    "infrastructure/iam_policies.sh"
    "infrastructure/cognito_setup.sh"
    "infrastructure/s3_config.sh"
    "infrastructure/dynamodb_config.sh"
    "infrastructure/teardown.sh"
)

for SCRIPT in "${SCRIPTS[@]}"; do
    if [ -x "$SCRIPT" ]; then
        echo "✓ Executable: $SCRIPT"
    else
        echo "⚠ Not executable: $SCRIPT (run: chmod +x $SCRIPT)"
        WARNINGS=$((WARNINGS + 1))
    fi
done

# Check Python dependencies file
echo ""
echo "Checking Python dependencies..."
if [ -f "backend/requirements.txt" ]; then
    DEPS=$(grep -E "^(boto3|pytest|moto)" backend/requirements.txt | wc -l)
    if [ "$DEPS" -eq 3 ]; then
        echo "✓ Required Python dependencies listed (boto3, pytest, moto)"
    else
        echo "⚠ Some required Python dependencies may be missing"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

# Check frontend dependencies
echo ""
echo "Checking frontend dependencies..."
if [ -f "frontend/package.json" ]; then
    if grep -q "react" frontend/package.json && grep -q "typescript" frontend/package.json; then
        echo "✓ Required frontend dependencies listed (React, TypeScript)"
    else
        echo "⚠ Some required frontend dependencies may be missing"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

# Check environment configuration
echo ""
echo "Checking environment configuration..."
if [ -f ".env" ]; then
    if grep -q "AWS_REGION" .env && grep -q "CONFIDENCE_THRESHOLD" .env; then
        echo "✓ Environment configuration file exists with required variables"
    else
        echo "⚠ Environment configuration may be incomplete"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

# Summary
echo ""
echo "=========================================="
echo "Validation Summary"
echo "=========================================="
echo "Errors: $ERRORS"
echo "Warnings: $WARNINGS"
echo ""

if [ $ERRORS -eq 0 ]; then
    echo "✓ Setup validation passed!"
    echo ""
    echo "Next steps:"
    echo "1. Run 'cd backend && bash setup.sh' to set up Python environment"
    echo "2. Run 'cd frontend && bash setup.sh' to set up Node.js environment (if Node.js is installed)"
    echo "3. Configure AWS CLI with 'aws configure'"
    echo "4. Update .env with your AWS account details"
    echo "5. Run 'cd infrastructure && bash deploy_all.sh' to deploy infrastructure"
    exit 0
else
    echo "✗ Setup validation failed with $ERRORS error(s)"
    echo "Please fix the errors above before proceeding."
    exit 1
fi
