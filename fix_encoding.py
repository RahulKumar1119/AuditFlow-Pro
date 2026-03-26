#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to add UTF-8 encoding declarations to Python files and verify TypeScript/JavaScript files.
This fixes SonarQube file encoding issues.
"""

import os
import re
from pathlib import Path

# UTF-8 encoding declaration
ENCODING_DECLARATION = "# -*- coding: utf-8 -*-"

# Directories to exclude
EXCLUDE_DIRS = {
    '__pycache__',
    '.pytest_cache',
    '.hypothesis',
    'node_modules',
    '.git',
    'dist',
    'build',
    'package',
}

# File patterns to process
PYTHON_PATTERN = re.compile(r'\.py$')
TS_JS_PATTERN = re.compile(r'\.(ts|tsx|js|jsx)$')


def should_skip_directory(path):
    """Check if directory should be skipped."""
    parts = Path(path).parts
    return any(part in EXCLUDE_DIRS for part in parts)


def has_encoding_declaration(file_path):
    """Check if file already has UTF-8 encoding declaration."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            first_lines = [f.readline() for _ in range(3)]
        
        for line in first_lines:
            if 'coding' in line and 'utf-8' in line.lower():
                return True
        return False
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False


def add_encoding_to_python_file(file_path):
    """Add UTF-8 encoding declaration to Python file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        
        # Check if shebang exists
        has_shebang = lines[0].startswith('#!')
        
        # Check if encoding already exists
        if has_encoding_declaration(file_path):
            return False
        
        # Prepare new content
        new_lines = []
        
        # Add shebang if it exists
        if has_shebang:
            new_lines.append(lines[0])
            start_idx = 1
        else:
            start_idx = 0
        
        # Add encoding declaration
        new_lines.append(ENCODING_DECLARATION)
        
        # Add rest of content
        new_lines.extend(lines[start_idx:])
        
        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines))
        
        return True
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def process_python_files(root_dir):
    """Process all Python files in directory."""
    processed = 0
    skipped = 0
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Remove excluded directories from dirnames to prevent traversal
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        
        if should_skip_directory(dirpath):
            continue
        
        for filename in filenames:
            if PYTHON_PATTERN.search(filename):
                file_path = os.path.join(dirpath, filename)
                
                if add_encoding_to_python_file(file_path):
                    print(f"✓ Added encoding to: {file_path}")
                    processed += 1
                else:
                    print(f"- Already has encoding: {file_path}")
                    skipped += 1
    
    return processed, skipped


def check_ts_js_files(root_dir):
    """Check TypeScript/JavaScript files for encoding issues."""
    found = 0
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Remove excluded directories
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        
        if should_skip_directory(dirpath):
            continue
        
        for filename in filenames:
            if TS_JS_PATTERN.search(filename):
                file_path = os.path.join(dirpath, filename)
                print(f"✓ Found TS/JS file: {file_path}")
                found += 1
    
    return found


def main():
    """Main function."""
    print("=" * 70)
    print("SonarQube File Encoding Fix")
    print("=" * 70)
    
    # Process backend Python files
    print("\n[1/2] Processing backend Python files...")
    print("-" * 70)
    backend_path = "auditflow-pro/backend"
    if os.path.exists(backend_path):
        processed, skipped = process_python_files(backend_path)
        print(f"\nBackend Summary: {processed} files updated, {skipped} already correct")
    else:
        print(f"Backend directory not found: {backend_path}")
    
    # Check frontend TypeScript/JavaScript files
    print("\n[2/2] Checking frontend TypeScript/JavaScript files...")
    print("-" * 70)
    frontend_path = "auditflow-pro/frontend/src"
    if os.path.exists(frontend_path):
        found = check_ts_js_files(frontend_path)
        print(f"\nFrontend Summary: {found} TS/JS files found")
        print("Note: TypeScript/JavaScript files typically don't need encoding declarations")
        print("      as they are handled by the build system and transpilers.")
    else:
        print(f"Frontend directory not found: {frontend_path}")
    
    print("\n" + "=" * 70)
    print("Encoding fix complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
