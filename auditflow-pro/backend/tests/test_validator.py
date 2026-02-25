# backend/tests/test_validator.py

import pytest
from unittest.mock import patch, MagicMock
from hypothesis import given, strategies as st
import random
import copy

from functions.validator.rules import (
    levenshtein_distance,
    validate_names,
    validate_ssn_dob,
    validate_income,
    validate_addresses
)
from functions.validator.golden_record import generate_golden_record
from functions.validator.app import aggregate_document_data

# --- Task 8.10: Unit Tests for Validation Rules ---

def test_levenshtein_distance():
    """Test the edit distance math."""
    assert levenshtein_distance("John", "John") == 0
    assert levenshtein_distance("John", "Jon") == 1  # 1 deletion
    assert levenshtein_distance("John", "Joan") == 1 # 1 substitution
    assert levenshtein_distance("Jonathan", "Jon") == 5 # 5 deletions

def test_validate_names():
    """Test that name mismatches > 2 edits are flagged."""
    names = [
        {"value": "John Doe", "source": "doc-1"},
        {"value": "Jon Doe", "source": "doc-2"},      # 1 edit (Should pass)
        {"value": "Jonathan Doe", "source": "doc-3"}  # 5 edits (Should flag)
    ]
    
    inconsistencies = validate_names(names)
    
    # We expect inconsistencies between John/Jonathan and Jon/Jonathan
    assert len(inconsistencies) == 2
    assert inconsistencies[0]["severity"] == "HIGH"
    assert "Jonathan Doe" in [inconsistencies[0]["expected_value"], inconsistencies[0]["actual_value"]]

def test_validate_ssn_dob():
    """Test strict zero-tolerance matching."""
    ssns = [
        {"value": "***-**-1234", "source": "doc-1"},
        {"value": "***-**-1234", "source": "doc-2"},
        {"value": "***-**-9999", "source": "doc-3"} # Mismatch
    ]
    
    inconsistencies = validate_ssn_dob(ssns, "ssn")
    
    assert len(inconsistencies) == 1
    assert inconsistencies[0]["severity"] == "CRITICAL"

def test_validate_income():
    """Test income discrepancy math (Summing W2s vs AGI)."""
    w2s = [
        {"value": "50,000", "source": "w2-1"},
        {"value": "25000", "source": "w2-2"}  # Total = 75000
    ]
    
    # 1. Test Match (No discrepancy)
    tax_agi_match = {"value": "$75,000.00", "source": "tax-1"}
    assert len(validate_income(w2s, tax_agi_match)) == 0
    
    # 2. Test Minor Discrepancy (e.g., $75,000 vs $78,000 = 4% difference) -> Should pass
    tax_agi_minor = {"value": "78000", "source": "tax-1"}
    assert len(validate_income(w2s, tax_agi_minor)) == 0
    
    # 3. Test High Discrepancy ($75,000 vs $90,000 = 20% difference) -> Should flag HIGH
    tax_agi_major = {"value": "90000", "source": "tax-1"}
    inconsistencies = validate_income(w2s, tax_agi_major)
    assert len(inconsistencies) == 1
    assert inconsistencies[0]["severity"] == "HIGH"

@patch('functions.validator.rules.semantic_address_check')
def test_validate_addresses_with_mocked_ai(mock_bedrock):
    """Test that the loop correctly utilizes the Bedrock AI."""
    # Mock the AI to say the first two match, but the third does not
    mock_bedrock.side_effect = [True, False, False]
    
    addresses = [
        {"value": "123 Main St", "source": "doc-1"},
        {"value": "123 Main Street", "source": "doc-2"},
        {"value": "456 Broad Ave", "source": "doc-3"}
    ]
    
    inconsistencies = validate_addresses(addresses)
    
    assert len(inconsistencies) == 2
    assert mock_bedrock.call_count == 3


# --- Task 8.9: Property-Based Test for Golden Record ---

# Strategy to generate random lists of extracted fields
extracted_field_strategy = st.lists(
    st.fixed_dictionaries({
        "value": st.text(min_size=1),
        "source": st.uuids().map(str),
        "confidence": st.floats(min_value=0.0, max_value=100.0),
        "document_type": st.sampled_from(["ID_DOCUMENT", "DRIVERS_LICENSE", "W2", "TAX_FORM", "BANK_STATEMENT", "UNKNOWN"])
    }),
    min_size=1,
    max_size=10
)

@given(extracted_field_strategy)
def test_golden_record_is_deterministic(field_values):
    """
    Task 8.9 (Property 2): Golden Record selection is deterministic.
    No matter what order the documents arrive in, the exact same value 
    must be chosen as the single source of truth based on the rules.
    """
    data = {"first_name": field_values}
    
    # Generate golden record from original list
    record1 = generate_golden_record(data)
    
    # Shuffle the input data
    shuffled_values = copy.deepcopy(field_values)
    random.shuffle(shuffled_values)
    shuffled_data = {"first_name": shuffled_values}
    
    # Generate golden record from shuffled list
    record2 = generate_golden_record(shuffled_data)
    
    # The selected "value", "source_document", and "confidence" must be identical
    assert record1["first_name"]["value"] == record2["first_name"]["value"]
    assert record1["first_name"]["source_document"] == record2["first_name"]["source_document"]
    assert record1["first_name"]["confidence"] == record2["first_name"]["confidence"]
