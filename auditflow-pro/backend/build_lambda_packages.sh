#!/bin/bash
# backend/build_lambda_packages.sh
# Builds deployment packages for all Lambda functions including shared modules

set -e

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FUNCTIONS_DIR="$BACKEND_DIR/functions"

echo "Building Lambda deployment packages..."
echo "========================================"

# Function to build a single Lambda package
build_function_package() {
    local func_name=$1
    local func_dir="$FUNCTIONS_DIR/$func_name"
    
    if [ ! -d "$func_dir" ]; then
        echo "Error: Function directory not found: $func_dir"
        return 1
    fi
    
    echo ""
    echo "Building package for: $func_name"
    
    # Create temporary build directory
    local build_dir=$(mktemp -d)
    
    # Copy function code
    cp "$func_dir/app.py" "$build_dir/"
    
    # Copy any additional Python files in the function directory
    find "$func_dir" -maxdepth 1 -name "*.py" ! -name "app.py" -exec cp {} "$build_dir/" \;
    
    # Copy shared module
    cp -r "$BACKEND_DIR/shared" "$build_dir/"
    
    # Install dependencies to build directory
    if [ -f "$BACKEND_DIR/requirements.txt" ]; then
        pip install -r "$BACKEND_DIR/requirements.txt" -t "$build_dir/" --quiet 2>/dev/null || true
    fi
    
    # Create deployment zip
    local zip_file="$func_dir/deployment_package.zip"
    
    # Remove old zip if exists
    rm -f "$zip_file"
    
    # Create new zip from build directory
    cd "$build_dir"
    zip -r -q "$zip_file" . 2>/dev/null || zip -r "$zip_file" . > /dev/null 2>&1
    cd - > /dev/null
    
    # Cleanup
    rm -rf "$build_dir"
    
    echo "✓ Created: $zip_file ($(du -h "$zip_file" | cut -f1))"
}

# Build packages for all functions that need shared module
FUNCTIONS_WITH_SHARED=("classifier" "extractor" "validator" "risk_scorer" "reporter")

for func in "${FUNCTIONS_WITH_SHARED[@]}"; do
    build_function_package "$func"
done

echo ""
echo "========================================"
echo "Lambda packages built successfully!"
echo ""
echo "Packages created:"
for func in "${FUNCTIONS_WITH_SHARED[@]}"; do
    if [ -f "$FUNCTIONS_DIR/$func/deployment_package.zip" ]; then
        echo "  ✓ $FUNCTIONS_DIR/$func/deployment_package.zip"
    fi
done
echo ""
echo "Next steps:"
echo "1. Deploy packages to AWS Lambda using AWS CLI or Amplify"
echo "2. Verify Lambda functions can import the 'shared' module"
echo "3. Test Step Functions workflow"
