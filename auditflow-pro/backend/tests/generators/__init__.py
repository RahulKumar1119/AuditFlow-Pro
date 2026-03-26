# -*- coding: utf-8 -*-
"""
Property-based test data generators for AuditFlow-Pro.

This module provides Hypothesis strategies for generating random valid document data
and inconsistencies for property-based testing.
"""

from .document_generators import (
    w2_data_strategy,
    bank_statement_data_strategy,
    tax_form_data_strategy,
    drivers_license_data_strategy,
    id_document_data_strategy,
    any_document_strategy
)

from .inconsistency_generators import (
    name_variation_strategy,
    address_mismatch_strategy,
    income_discrepancy_strategy,
    ssn_mismatch_strategy,
    dob_mismatch_strategy,
    any_inconsistency_strategy
)

__all__ = [
    'w2_data_strategy',
    'bank_statement_data_strategy',
    'tax_form_data_strategy',
    'drivers_license_data_strategy',
    'id_document_data_strategy',
    'any_document_strategy',
    'name_variation_strategy',
    'address_mismatch_strategy',
    'income_discrepancy_strategy',
    'ssn_mismatch_strategy',
    'dob_mismatch_strategy',
    'any_inconsistency_strategy'
]
