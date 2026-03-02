# Test Fixtures for AuditFlow-Pro

This directory contains test fixtures and sample data for testing the loan document auditor system.

## Directory Structure

- `w2/` - Sample W2 forms with realistic data
- `bank_statements/` - Sample bank statements
- `tax_forms/` - Sample tax forms (1040)
- `drivers_licenses/` - Sample driver's licenses
- `id_documents/` - Sample ID documents
- `inconsistent_sets/` - Document sets with known inconsistencies
- `edge_cases/` - Edge case test documents
- `generators/` - Property-based test data generators

## Data Characteristics

All test data uses synthetic/fake information generated with the Faker library. No real PII is included.

### Sample Documents (fixtures/)
- At least 3 samples per document type
- Realistic formatting and structure
- Valid data that would pass extraction

### Inconsistent Sets (inconsistent_sets/)
- Name variations (spelling differences)
- Address mismatches
- Income discrepancies
- Identification number mismatches

### Edge Cases (edge_cases/)
- Multi-page PDFs (up to 100 pages)
- Low-quality/illegible documents
- Various formats and layouts
- Documents with PII requiring masking

## Usage

Import fixtures in tests:
```python
import json
from pathlib import Path

fixtures_dir = Path(__file__).parent / "fixtures"
w2_data = json.load(open(fixtures_dir / "w2" / "sample_w2_001.json"))
```
