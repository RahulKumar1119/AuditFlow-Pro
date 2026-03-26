# -*- coding: utf-8 -*-
"""
Example property-based tests demonstrating usage of test generators.

These tests validate universal properties that should hold across all inputs.
"""

import pytest
from hypothesis import given, settings, example
from generators import (
    w2_data_strategy,
    bank_statement_data_strategy,
    any_document_strategy,
    name_variation_strategy,
    income_discrepancy_strategy
)


class TestDocumentGenerators:
    """Test that document generators produce valid data"""
    
    @given(w2_data=w2_data_strategy())
    @settings(max_examples=50)
    def test_w2_generator_produces_valid_data(self, w2_data):
        """Property: All generated W2 data has required fields with valid confidence"""
        assert w2_data["document_type"] == "W2"
        assert "employee_name" in w2_data
        assert "wages" in w2_data
        
        # All confidence scores should be in valid range
        for field_name, field_data in w2_data.items():
            if isinstance(field_data, dict) and "confidence" in field_data:
                assert 0.0 <= field_data["confidence"] <= 1.0
    
    @given(bank_data=bank_statement_data_strategy())
    @settings(max_examples=50)
    def test_bank_statement_generator_produces_valid_data(self, bank_data):
        """Property: All generated bank statement data has required fields"""
        assert bank_data["document_type"] == "BANK_STATEMENT"
        assert "account_holder_name" in bank_data
        assert "ending_balance" in bank_data


class TestInconsistencyGenerators:
    """Test that inconsistency generators produce valid variations"""
    
    @given(name_var=name_variation_strategy())
    @settings(max_examples=50)
    def test_name_variations_differ_from_original(self, name_var):
        """Property: Name variations should differ from original"""
        assert name_var["original"] != name_var["variation"]
        assert name_var["edit_distance"] > 0
    
    @given(income_disc=income_discrepancy_strategy())
    @settings(max_examples=50)
    def test_income_discrepancies_have_valid_percentages(self, income_disc):
        """Property: Income discrepancies should have valid percentage differences"""
        original = income_disc["original"]
        discrepant = income_disc["discrepant"]
        percentage = income_disc["percentage_difference"]
        
        # Calculate actual percentage
        actual_pct = abs(discrepant - original) / original * 100
        assert abs(actual_pct - percentage) < 0.1  # Allow small rounding error
