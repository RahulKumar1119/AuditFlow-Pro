#!/usr/bin/env python3
"""
Validation script for test fixtures.
Verifies that all fixtures are properly formatted and contain required fields.
"""

import json
from pathlib import Path


def validate_fixture(fixture_path):
    """Validate a single fixture file"""
    with open(fixture_path) as f:
        data = json.load(f)
    
    errors = []
    
    # Check for required top-level fields
    if "extracted_data" in data or "documents" in data:
        # Valid structure
        pass
    else:
        errors.append(f"Missing 'extracted_data' or 'documents' field")
    
    # Check confidence scores if present
    if "extracted_data" in data:
        for field_name, field_data in data["extracted_data"].items():
            if isinstance(field_data, dict) and "confidence" in field_data:
                conf = field_data["confidence"]
                # Allow null confidence for null values
                if conf is not None and not (0.0 <= conf <= 1.0):
                    errors.append(f"Invalid confidence {conf} for field {field_name}")
    
    return errors


def main():
    fixtures_dir = Path(__file__).parent
    
    print("Validating test fixtures...")
    print("=" * 60)
    
    total_files = 0
    total_errors = 0
    
    # Validate all JSON files
    for json_file in fixtures_dir.rglob("*.json"):
        total_files += 1
        relative_path = json_file.relative_to(fixtures_dir)
        
        try:
            errors = validate_fixture(json_file)
            if errors:
                print(f"\n❌ {relative_path}")
                for error in errors:
                    print(f"   - {error}")
                total_errors += len(errors)
            else:
                print(f"✓ {relative_path}")
        except Exception as e:
            print(f"\n❌ {relative_path}")
            print(f"   - Error loading file: {e}")
            total_errors += 1
    
    print("\n" + "=" * 60)
    print(f"Validated {total_files} fixture files")
    
    if total_errors == 0:
        print("✓ All fixtures are valid!")
        return 0
    else:
        print(f"❌ Found {total_errors} errors")
        return 1


if __name__ == "__main__":
    exit(main())
