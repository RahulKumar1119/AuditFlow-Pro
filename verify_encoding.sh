#!/bin/bash
# -*- coding: utf-8 -*-
# Verification script for UTF-8 encoding declarations in Python files

echo "=========================================="
echo "SonarQube Encoding Fix Verification"
echo "=========================================="
echo ""

# Count files with encoding declarations
echo "[1/3] Checking backend Python files for UTF-8 encoding declarations..."
echo ""

BACKEND_PATH="auditflow-pro/backend"
TOTAL_PY_FILES=0
FILES_WITH_ENCODING=0
FILES_WITHOUT_ENCODING=0

# Find all Python files (excluding __pycache__, node_modules, package)
for file in $(find "$BACKEND_PATH" -name "*.py" -type f | grep -v __pycache__ | grep -v "\.pytest_cache" | grep -v "\.hypothesis" | grep -v "/package/"); do
    TOTAL_PY_FILES=$((TOTAL_PY_FILES + 1))
    
    # Check first 3 lines for encoding declaration
    if head -3 "$file" | grep -q "coding.*utf-8"; then
        FILES_WITH_ENCODING=$((FILES_WITH_ENCODING + 1))
    else
        FILES_WITHOUT_ENCODING=$((FILES_WITHOUT_ENCODING + 1))
        echo "  ⚠ Missing encoding: $file"
    fi
done

echo ""
echo "Backend Python Files Summary:"
echo "  Total Python files: $TOTAL_PY_FILES"
echo "  ✓ Files with UTF-8 encoding: $FILES_WITH_ENCODING"
echo "  ✗ Files without UTF-8 encoding: $FILES_WITHOUT_ENCODING"
echo ""

# Check frontend files
echo "[2/3] Checking frontend TypeScript/JavaScript files..."
echo ""

FRONTEND_PATH="auditflow-pro/frontend/src"
TOTAL_TS_JS_FILES=0

if [ -d "$FRONTEND_PATH" ]; then
    TOTAL_TS_JS_FILES=$(find "$FRONTEND_PATH" -type f \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" \) | wc -l)
    echo "  Found $TOTAL_TS_JS_FILES TypeScript/JavaScript files"
    echo "  ℹ Note: TS/JS files don't require explicit encoding declarations"
    echo "         (handled by build system and transpilers)"
else
    echo "  Frontend directory not found"
fi

echo ""
echo "[3/3] Verification Results:"
echo "=========================================="

if [ "$FILES_WITHOUT_ENCODING" -eq 0 ]; then
    echo "✓ SUCCESS: All Python files have UTF-8 encoding declarations!"
    echo ""
    echo "SonarQube should now pass encoding checks."
    exit 0
else
    echo "✗ INCOMPLETE: $FILES_WITHOUT_ENCODING Python files still need encoding declarations"
    exit 1
fi
