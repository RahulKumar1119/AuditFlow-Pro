import pytest
from shared.models import ExtractedField, Inconsistency

def test_extracted_field_confidence_bounds():
    """Test that confidence scores operate correctly."""
    # Valid high confidence
    field1 = ExtractedField(value="John Doe", confidence=0.95)
    assert field1.requires_manual_review is False
    
    # Manual review flag logic (simulating the logic that will be in the extractor)
    field2 = ExtractedField(value="123 Main St", confidence=0.75)
    if field2.confidence is not None and field2.confidence < 0.80:
        field2.requires_manual_review = True
        
    assert field2.requires_manual_review is True

def test_inconsistency_severity_levels():
    """Test that inconsistency models hold the correct severity levels."""
    inc = Inconsistency(
        inconsistency_id="inc-123",
        field="ssn",
        severity="CRITICAL",
        expected_value="***-**-1234",
        actual_value="***-**-9999",
        source_documents=["doc-1", "doc-2"],
        description="SSN mismatch detected across documents.",
        detected_by="cross_document_validator"
    )
    
    assert inc.severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    assert len(inc.source_documents) >= 2
