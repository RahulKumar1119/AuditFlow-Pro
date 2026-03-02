# Test Fixtures Summary

## Overview

This document provides a comprehensive summary of all test fixtures created for the AuditFlow-Pro loan document auditor system.

## Fixture Categories

### 1. Sample Documents (Happy Path)

Located in document-type specific directories. Each contains 3 samples with realistic data.

#### W2 Forms (`w2/`)
- `sample_w2_001.json` - Standard employee with $75K wages
- `sample_w2_002.json` - High earner with $125K wages, Texas resident
- `sample_w2_003.json` - Lower confidence scores on some fields

#### Bank Statements (`bank_statements/`)
- `sample_bank_001.json` - Standard checking account
- `sample_bank_002.json` - Savings account with high balance
- `sample_bank_003.json` - Low confidence on address field

#### Tax Forms (`tax_forms/`)
- `sample_1040_001.json` - Single filer, standard deduction
- `sample_1040_002.json` - High income single filer
- `sample_1040_003.json` - Married filing jointly

#### Driver's Licenses (`drivers_licenses/`)
- `sample_dl_001.json` - Illinois driver's license
- `sample_dl_002.json` - Texas driver's license
- `sample_dl_003.json` - Washington driver's license

#### ID Documents (`id_documents/`)
- `sample_id_001.json` - US Passport
- `sample_id_002.json` - State ID card
- `sample_id_003.json` - Military ID

### 2. Inconsistent Document Sets

Located in `inconsistent_sets/`. Each set contains multiple documents with known inconsistencies.

#### Name Variations (`name_variation_set.json`)
- **Inconsistency**: "Jon Doe" vs "John Doe"
- **Expected Severity**: CRITICAL
- **Documents**: W2, Tax Form, Driver's License
- **Use Case**: Testing name validation with edit distance > 2

#### Address Mismatches (`address_mismatch_set.json`)
- **Inconsistency**: Street number differs (200 vs 201)
- **Expected Severity**: HIGH
- **Documents**: W2, Bank Statement, Driver's License
- **Use Case**: Testing address component comparison

#### Income Discrepancies (`income_discrepancy_set.json`)
- **Inconsistency**: $80K on W2 vs $70K on tax form (12.5% difference)
- **Expected Severity**: HIGH
- **Documents**: W2, Tax Form, Bank Statement
- **Use Case**: Testing income validation with >10% discrepancy

#### SSN Mismatches (`ssn_mismatch_set.json`)
- **Inconsistency**: ***-**-4444 vs ***-**-4445
- **Expected Severity**: CRITICAL
- **Documents**: W2, Tax Form, Driver's License
- **Use Case**: Testing SSN validation with zero tolerance

#### Date of Birth Mismatches (`dob_mismatch_set.json`)
- **Inconsistency**: 1975-12-25 vs 1975-12-26
- **Expected Severity**: CRITICAL
- **Documents**: Driver's License, Passport, W2
- **Use Case**: Testing DOB validation across identification documents

### 3. Edge Cases

Located in `edge_cases/`. Tests system limits and special scenarios.

#### Multi-Page PDF (`multi_page_pdf.json`)
- **Characteristics**: 100 pages, 45MB, 1250 transactions
- **Use Case**: Testing multi-page processing and timeout handling
- **Expected Behavior**: Should split into batches if exceeding 5-minute timeout

#### Low Quality Document (`low_quality_document.json`)
- **Characteristics**: Poor scan quality, multiple low confidence fields
- **Issues**: Faded text, skewed scan, coffee stain, partial blur
- **Low Confidence Fields**: 6 fields below 80% threshold
- **Use Case**: Testing handling of illegible documents and manual review flagging

#### Various Formats (`various_formats.json`)
- **Formats**: PDF, JPEG, PNG, TIFF
- **Layouts**: Standard IRS, photographed, scanned, custom branded
- **Use Case**: Testing format and layout variation handling

#### PII Masking Required (`pii_masking_required.json`)
- **PII Fields**: 11 fields requiring masking
- **Types**: SSN, bank accounts, phone, email, DOB
- **Use Case**: Testing PII detection, masking, and field-level encryption

## Usage in Tests

### Loading Fixtures

```python
import json
from pathlib import Path

fixtures_dir = Path(__file__).parent / "fixtures"

# Load a specific fixture
with open(fixtures_dir / "w2" / "sample_w2_001.json") as f:
    w2_data = json.load(f)

# Load an inconsistent set
with open(fixtures_dir / "inconsistent_sets" / "name_variation_set.json") as f:
    name_var_set = json.load(f)
```

### Testing with Fixtures

```python
def test_w2_extraction():
    w2_data = load_fixture("w2/sample_w2_001.json")
    result = extract_w2_data(w2_data)
    assert result["employee_name"]["value"] == "John Michael Doe"
    assert result["wages"]["value"] == 75000.00

def test_name_inconsistency_detection():
    name_set = load_fixture("inconsistent_sets/name_variation_set.json")
    inconsistencies = validate_documents(name_set["documents"])
    assert len(inconsistencies) > 0
    assert inconsistencies[0]["field"] == "name"
    assert inconsistencies[0]["severity"] == "CRITICAL"
```

## Statistics

- **Total Sample Documents**: 15 (3 per document type × 5 types)
- **Inconsistent Sets**: 5 (covering all major inconsistency types)
- **Edge Case Scenarios**: 4 (multi-page, low quality, formats, PII)
- **Total Fixtures**: 24 JSON files
- **PII Fields Covered**: 11 different PII types
- **Document Types**: 5 (W2, Bank Statement, Tax Form, Driver's License, ID Document)

## Maintenance

### Adding New Fixtures

1. Create JSON file in appropriate directory
2. Follow existing structure with `document_id`, `metadata`, and `extracted_data`
3. Include confidence scores for all extracted fields
4. Add description and use case in metadata
5. Update this summary document

### Updating Existing Fixtures

1. Maintain backward compatibility where possible
2. Update version or add new variant rather than modifying existing
3. Document changes in fixture metadata
4. Update tests that depend on the fixture

## Related Documentation

- `README.md` - Overview of fixtures directory
- `generators/README.md` - Property-based test generators
- `test_property_examples.py` - Example usage of generators
