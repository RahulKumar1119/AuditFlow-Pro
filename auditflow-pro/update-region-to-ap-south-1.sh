#!/bin/bash
# update-region-to-ap-south-1.sh
# Ensures all configuration files use ap-south-1 region exclusively

set -e

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Updating Region to ap-south-1${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_REGION="ap-south-1"
UPDATED_COUNT=0

# Function to update region in file
update_region() {
    local file=$1
    local pattern=$2
    local replacement=$3
    
    if [ -f "$file" ]; then
        if grep -q "$pattern" "$file" 2>/dev/null; then
            # Check if it's not already ap-south-1
            if ! grep "$pattern" "$file" | grep -q "ap-south-1"; then
                echo -e "${YELLOW}Updating:${NC} $file"
                sed -i.bak "s/$pattern/$replacement/g" "$file"
                rm -f "${file}.bak"
                ((UPDATED_COUNT++))
            else
                echo -e "${GREEN}✓${NC} Already correct: $file"
            fi
        fi
    fi
}

echo "Checking configuration files..."
echo ""

# Update config files
for env_file in config/*.env .env; do
    if [ -f "$env_file" ]; then
        echo "Checking: $env_file"
        
        # Update AWS_REGION
        if grep -q "AWS_REGION=" "$env_file"; then
            if ! grep "AWS_REGION=" "$env_file" | grep -q "ap-south-1"; then
                sed -i.bak 's/AWS_REGION=.*/AWS_REGION=ap-south-1/' "$env_file"
                rm -f "${env_file}.bak"
                echo -e "${YELLOW}  Updated AWS_REGION${NC}"
                ((UPDATED_COUNT++))
            else
                echo -e "${GREEN}  ✓ AWS_REGION already ap-south-1${NC}"
            fi
        fi
        
        # Update VITE_AWS_REGION
        if grep -q "VITE_AWS_REGION=" "$env_file"; then
            if ! grep "VITE_AWS_REGION=" "$env_file" | grep -q "ap-south-1"; then
                sed -i.bak 's/VITE_AWS_REGION=.*/VITE_AWS_REGION=ap-south-1/' "$env_file"
                rm -f "${env_file}.bak"
                echo -e "${YELLOW}  Updated VITE_AWS_REGION${NC}"
                ((UPDATED_COUNT++))
            else
                echo -e "${GREEN}  ✓ VITE_AWS_REGION already ap-south-1${NC}"
            fi
        fi
        
        echo ""
    fi
done

# Update infrastructure scripts
echo "Checking infrastructure scripts..."
echo ""

for script in infrastructure/*.sh; do
    if [ -f "$script" ]; then
        # Check if script has REGION variable
        if grep -q 'REGION=' "$script" 2>/dev/null; then
            if ! grep 'REGION=' "$script" | grep -q "ap-south-1"; then
                echo -e "${YELLOW}Updating:${NC} $script"
                sed -i.bak 's/REGION="[^"]*"/REGION="ap-south-1"/' "$script"
                sed -i.bak 's/REGION=[^ ]*/REGION="ap-south-1"/' "$script"
                rm -f "${script}.bak"
                ((UPDATED_COUNT++))
            else
                echo -e "${GREEN}✓${NC} $script"
            fi
        fi
    fi
done

echo ""

# Update backend Python files if they have region references
echo "Checking backend files..."
echo ""

if [ -d "backend" ]; then
    # Check for region in Python files
    for py_file in $(find backend -name "*.py" -type f); do
        if grep -q "region_name=" "$py_file" 2>/dev/null; then
            if ! grep "region_name=" "$py_file" | grep -q "ap-south-1"; then
                echo -e "${YELLOW}Updating:${NC} $py_file"
                sed -i.bak "s/region_name=['\"][^'\"]*['\"]/region_name='ap-south-1'/g" "$py_file"
                rm -f "${py_file}.bak"
                ((UPDATED_COUNT++))
            fi
        fi
    done
fi

# Update frontend files if they have region references
echo "Checking frontend files..."
echo ""

if [ -d "frontend/src" ]; then
    for ts_file in $(find frontend/src -name "*.ts" -o -name "*.tsx" 2>/dev/null); do
        if grep -q "region:" "$ts_file" 2>/dev/null; then
            if ! grep "region:" "$ts_file" | grep -q "ap-south-1"; then
                echo -e "${YELLOW}Updating:${NC} $ts_file"
                sed -i.bak "s/region: ['\"][^'\"]*['\"]/region: 'ap-south-1'/g" "$ts_file"
                rm -f "${ts_file}.bak"
                ((UPDATED_COUNT++))
            fi
        fi
    done
fi

# Update documentation files
echo "Checking documentation files..."
echo ""

for doc_file in *.md infrastructure/*.md backend/*.md; do
    if [ -f "$doc_file" ]; then
        # Skip if it's a changelog or similar
        if [[ "$doc_file" == *"CHANGELOG"* ]] || [[ "$doc_file" == *"HISTORY"* ]]; then
            continue
        fi
        
        # Check for region references in examples
        if grep -q "us-east-1\|us-west-2\|eu-west-1" "$doc_file" 2>/dev/null; then
            echo -e "${YELLOW}Updating:${NC} $doc_file"
            sed -i.bak 's/us-east-1/ap-south-1/g' "$doc_file"
            sed -i.bak 's/us-west-2/ap-south-1/g' "$doc_file"
            sed -i.bak 's/eu-west-1/ap-south-1/g' "$doc_file"
            rm -f "${doc_file}.bak"
            ((UPDATED_COUNT++))
        fi
    fi
done

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

if [ $UPDATED_COUNT -eq 0 ]; then
    echo -e "${GREEN}✓ All files already configured for ap-south-1${NC}"
else
    echo -e "${YELLOW}Updated $UPDATED_COUNT file(s) to use ap-south-1${NC}"
fi

echo ""
echo "Region configuration complete!"
echo ""
echo "Next steps:"
echo "1. Review changes: git diff"
echo "2. Verify configuration: grep -r 'AWS_REGION' config/"
echo "3. Deploy to ap-south-1: ./deploy-master.sh -e prod"
echo ""
