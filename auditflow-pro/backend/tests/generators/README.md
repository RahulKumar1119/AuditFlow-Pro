# Property-Based Test Generators

This directory contains Hypothesis strategies for generating random test data for property-based testing.

## Overview

Property-based testing validates that certain properties hold true across a wide range of inputs, rather than testing specific examples. These generators create random valid document data and inconsistencies to test the system's behavior comprehensively.

## Available Generators

### Document Generators (`document_generators.py`)

Generate random valid document data for all document types:

- `w2_data_strategy()` - Generate W2 form data
- `bank_statement_data_strategy()` - Generate bank statement data
- `tax_form_data_strategy()` - Generate 1040 tax form data
- `drivers_license_data_strategy()` - Generate driver's license data
- `id_document_data_strategy()` - Generate ID document data
- `any_document_strategy` - Generate any document type randomly

### Inconsistency Generators (`inconsistency_generators.py`)

Generate random inconsistencies for testing validation logic:

- `name_variation_strategy()` - Generate name spelling variations
- `address_mismatch_strategy()` - Generate address mismatches
- `income_discrepancy_strategy()` - Generate income discrepancies
- `ssn_mismatch_strategy()` - Generate SSN mismatches
- `dob_mismatch_strategy()` - Generate date of birth mismatches
- `any_inconsistency_strategy` - Generate any inconsistency type randomly

## Usage Examples

### Basic Document Generation

```python
from hypothesis import given
from generators import w2_data_strategy

@given(w2_data=w2_data_strategy())
def test_w2_extraction(w2_data):
    # Test that W2 data can be processed
    assert w2_data["document_type"] == "W2"
    assert "employee_name" in w2_data
    assert w2_data["employee_name"]["confidence"] >= 0.70
```

### Testing with Inconsistencies

```python
from hypothesis import given
from generators import name_variation_strategy

@given(name_var=name_variation_strategy())
def test_name_validation_detects_variations(name_var):
    # Test that name variations are detected
    original = name_var["original"]
    variation = name_var["variation"]
    edit_distance = name_var["edit_distance"]
    
    # Should flag if edit distance > 2
    if edit_distance > 2:
        assert should_flag_inconsistency(original, variation)
```

### Round-Trip Testing

```python
from hypothesis import given
from generators import any_document_strategy

@given(document=any_document_strategy)
def test_serialization_round_trip(document):
    # Property: parse(serialize(data)) == data
    serialized = serialize_document(document)
    parsed = parse_document(serialized)
    assert parsed == document
```

## Configuration

### Adjusting Confidence Ranges

Confidence scores can be adjusted by modifying the `field_with_confidence` calls:

```python
# Default: 0.70 to 0.99
field_with_confidence(value_strategy, min_conf=0.70, max_conf=0.99)

# High confidence only
field_with_confidence(value_strategy, min_conf=0.90, max_conf=0.99)

# Include low confidence
field_with_confidence(value_strategy, min_conf=0.50, max_conf=0.99)
```

### Customizing Value Ranges

Modify the strategy parameters to adjust value ranges:

```python
# Default wages: $20,000 to $200,000
st.floats(min_value=20000.0, max_value=200000.0)

# Higher income range
st.floats(min_value=50000.0, max_value=500000.0)
```

## Testing Best Practices

1. **Run with sufficient examples**: Use at least 100 examples per property test
   ```python
   @given(data=w2_data_strategy())
   @settings(max_examples=100)
   def test_property(data):
       ...
   ```

2. **Use deterministic seeds**: For reproducibility
   ```python
   @given(data=w2_data_strategy())
   @seed(12345)
   def test_property(data):
       ...
   ```

3. **Leverage shrinking**: Hypothesis automatically finds minimal failing examples
   - Let tests fail naturally to see the simplest counterexample
   - Don't catch exceptions unless testing error handling

4. **Test universal properties**: Focus on properties that should always hold
   - Idempotency: `f(f(x)) == f(x)`
   - Round-trip: `parse(serialize(x)) == x`
   - Monotonicity: `x <= y => f(x) <= f(y)`
   - Invariants: Properties that never change

## Integration with CI/CD

Add property-based tests to your test suite:

```bash
# Run all tests including property-based tests
pytest backend/tests/

# Run only property-based tests
pytest backend/tests/ -k "property"

# Run with verbose output
pytest backend/tests/ -v --hypothesis-show-statistics
```

## Troubleshooting

### Tests are too slow
- Reduce `max_examples` for faster feedback during development
- Use `@example()` decorator to add specific test cases alongside property tests

### Flaky tests
- Ensure tests are deterministic (no random.random(), use draw() instead)
- Use `@seed()` decorator to reproduce failures
- Check for time-dependent behavior

### Hypothesis finds unexpected failures
- This is good! It means the property test found a real issue
- Examine the minimal failing example Hypothesis provides
- Fix the code or adjust the property if the assumption was wrong

## References

- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- [Property-Based Testing Guide](https://hypothesis.works/articles/what-is-property-based-testing/)
- [Hypothesis Strategies](https://hypothesis.readthedocs.io/en/latest/data.html)
