# backend/tests/test_risk_scorer.py

import pytest
from hypothesis import given, strategies as st
from functions.risk_scorer.scorer import (
    calculate_inconsistency_score,
    calculate_total_risk,
    determine_risk_level
)

# --- Task 9.7: Unit Tests ---

def test_determine_risk_level():
    """Test risk level thresholds."""
    assert determine_risk_level(0) == "LOW"
    assert determine_risk_level(24) == "LOW"
    assert determine_risk_level(25) == "MEDIUM"
    assert determine_risk_level(49) == "MEDIUM"
    assert determine_risk_level(50) == "HIGH"
    assert determine_risk_level(79) == "HIGH"
    assert determine_risk_level(80) == "CRITICAL"
    assert determine_risk_level(100) == "CRITICAL"

def test_inconsistency_scoring_values():
    """Test specific point allocations for different inconsistencies."""
    inconsistencies = [
        {"field": "first_name", "description": "Name mismatch"}, # 15 pts
        {"field": "address", "description": "Address mismatch"},   # 20 pts
        {"field": "income", "severity": "HIGH", "description": ">10% mismatch"}, # 25 pts
        {"field": "ssn", "description": "SSN mismatch"}            # 30 pts
    ]
    
    score, factors = calculate_inconsistency_score(inconsistencies)
    assert score == 90
    assert len(factors) == 4

def test_score_capping_at_100():
    """Test that the final score never exceeds 100."""
    # Create enough inconsistencies to easily surpass 100 points
    inconsistencies = [
        {"field": "ssn", "description": "Mismatch"}, # 30 pts
        {"field": "date_of_birth", "description": "Mismatch"}, # 30 pts
        {"field": "address", "description": "Mismatch"}, # 20 pts
        {"field": "income", "severity": "HIGH", "description": "Mismatch"} # 25 pts
    ] # Total raw: 105
    
    golden_record = {
        "field1": {"confidence": 50.0}, # +10 pts
        "field2": {"confidence": 60.0}  # +10 pts
    } # Total raw: 125
    
    result = calculate_total_risk(inconsistencies, golden_record, [])
    
    assert result["raw_score"] == 125
    assert result["risk_score"] == 100
    assert result["risk_level"] == "CRITICAL"

# --- Task 9.6: Property-Based Testing ---

# Generate random inconsistencies
inconsistency_strategy = st.lists(
    st.sampled_from([
        {"field": "name", "severity": "HIGH"},
        {"field": "address", "severity": "HIGH"},
        {"field": "income", "severity": "MEDIUM"},
        {"field": "ssn", "severity": "CRITICAL"}
    ]),
    min_size=0,
    max_size=20
)

@given(inconsistency_strategy)
def test_risk_score_is_monotonically_increasing(inconsistencies):
    """
    Task 9.6 (Property 3): Risk score is monotonically increasing with inconsistencies.
    If we take a list of inconsistencies, and add one MORE inconsistency to it,
    the raw score MUST be >= the original raw score.
    """
    # Get base score
    base_result = calculate_total_risk(inconsistencies, {}, [])
    base_raw = base_result["raw_score"]
    
    # Add an additional inconsistency
    larger_inconsistencies = inconsistencies + [{"field": "name", "severity": "HIGH"}]
    larger_result = calculate_total_risk(larger_inconsistencies, {}, [])
    larger_raw = larger_result["raw_score"]
    
    # The new raw score must be strictly greater than or equal to the base
    assert larger_raw >= base_raw
