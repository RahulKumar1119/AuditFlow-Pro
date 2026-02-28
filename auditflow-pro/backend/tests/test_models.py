import pytest
from hypothesis import given, strategies as st
from shared.models import (
    ExtractedField, DocumentMetadata, W2Data, BankStatementData,
    TaxFormData, DriversLicenseData, IDDocumentData, GoldenRecord,
    GoldenRecordField, Inconsistency, RiskFactor, Alert, AuditRecord
)

# Strategy to generate random ExtractedField objects
extracted_field_strategy = st.builds(
    ExtractedField,
    value=st.one_of(st.text(), st.integers(), st.floats(allow_nan=False, allow_infinity=False)),
    confidence=st.one_of(st.none(), st.floats(min_value=0.0, max_value=1.0)),
    requires_manual_review=st.booleans()
)

# Strategy to generate random DocumentMetadata objects
document_metadata_strategy = st.builds(
    DocumentMetadata,
    document_id=st.uuids().map(str),
    loan_application_id=st.uuids().map(str),
    s3_bucket=st.text(min_size=1),
    s3_key=st.text(min_size=1),
    upload_timestamp=st.datetimes().map(lambda d: d.isoformat()),
    file_name=st.text(min_size=1),
    file_size_bytes=st.integers(min_value=1, max_value=50_000_000), # Max 50MB
    file_format=st.sampled_from(["PDF", "JPEG", "PNG", "TIFF"]),
    checksum=st.text(min_size=10),
    extracted_data=st.dictionaries(st.text(min_size=1), extracted_field_strategy, max_size=5)
)

@given(document_metadata_strategy)
def test_round_trip_serialization_preserves_data(doc_metadata):
    """
    Property 1: For all valid document data objects, serializing to JSON 
    and then deserializing back must produce an equivalent object.
    Validates Requirements: 23.4
    """
    # Serialize to JSON string
    json_data = doc_metadata.to_json()
    
    # Deserialize back to object
    parsed_metadata = DocumentMetadata.from_json(json_data)
    
    # Assert equivalence
    assert doc_metadata == parsed_metadata


# Unit tests for document data classes
def test_w2_data_serialization():
    """Test W2Data serialization and deserialization."""
    w2 = W2Data()
    w2.tax_year = ExtractedField(value="2023", confidence=0.99)
    w2.employer_name = ExtractedField(value="Acme Corp", confidence=0.97)
    w2.wages = ExtractedField(value=75000.00, confidence=0.99)
    
    # Convert to dict and back
    data_dict = w2.to_dict()
    w2_restored = W2Data.from_dict(data_dict)
    
    assert w2_restored.tax_year.value == "2023"
    assert w2_restored.employer_name.value == "Acme Corp"
    assert w2_restored.wages.value == 75000.00


def test_bank_statement_data_serialization():
    """Test BankStatementData serialization and deserialization."""
    bank_stmt = BankStatementData()
    bank_stmt.bank_name = ExtractedField(value="First National Bank", confidence=0.98)
    bank_stmt.account_number = ExtractedField(value="****1234", confidence=0.99)
    bank_stmt.ending_balance = ExtractedField(value=6200.00, confidence=0.98)
    
    # Convert to dict and back
    data_dict = bank_stmt.to_dict()
    bank_stmt_restored = BankStatementData.from_dict(data_dict)
    
    assert bank_stmt_restored.bank_name.value == "First National Bank"
    assert bank_stmt_restored.account_number.value == "****1234"
    assert bank_stmt_restored.ending_balance.value == 6200.00


def test_tax_form_data_serialization():
    """Test TaxFormData serialization and deserialization."""
    tax_form = TaxFormData()
    tax_form.form_type = ExtractedField(value="1040", confidence=0.99)
    tax_form.taxpayer_name = ExtractedField(value="John Doe", confidence=0.98)
    tax_form.adjusted_gross_income = ExtractedField(value=75000.00, confidence=0.98)
    
    # Convert to dict and back
    data_dict = tax_form.to_dict()
    tax_form_restored = TaxFormData.from_dict(data_dict)
    
    assert tax_form_restored.form_type.value == "1040"
    assert tax_form_restored.taxpayer_name.value == "John Doe"
    assert tax_form_restored.adjusted_gross_income.value == 75000.00


def test_drivers_license_data_serialization():
    """Test DriversLicenseData serialization and deserialization."""
    dl = DriversLicenseData()
    dl.state = ExtractedField(value="IL", confidence=0.99)
    dl.license_number = ExtractedField(value="D123-4567-8901", confidence=0.98)
    dl.full_name = ExtractedField(value="John Doe", confidence=0.98)
    dl.date_of_birth = ExtractedField(value="1985-06-15", confidence=0.99)
    
    # Convert to dict and back
    data_dict = dl.to_dict()
    dl_restored = DriversLicenseData.from_dict(data_dict)
    
    assert dl_restored.state.value == "IL"
    assert dl_restored.license_number.value == "D123-4567-8901"
    assert dl_restored.full_name.value == "John Doe"
    assert dl_restored.date_of_birth.value == "1985-06-15"


def test_id_document_data_serialization():
    """Test IDDocumentData serialization and deserialization."""
    id_doc = IDDocumentData()
    id_doc.id_type = ExtractedField(value="PASSPORT", confidence=0.95)
    id_doc.document_number = ExtractedField(value="123456789", confidence=0.98)
    id_doc.full_name = ExtractedField(value="John Doe", confidence=0.98)
    id_doc.nationality = ExtractedField(value="USA", confidence=0.98)
    
    # Convert to dict and back
    data_dict = id_doc.to_dict()
    id_doc_restored = IDDocumentData.from_dict(data_dict)
    
    assert id_doc_restored.id_type.value == "PASSPORT"
    assert id_doc_restored.document_number.value == "123456789"
    assert id_doc_restored.full_name.value == "John Doe"
    assert id_doc_restored.nationality.value == "USA"


def test_golden_record_serialization():
    """Test GoldenRecord serialization and deserialization."""
    gr = GoldenRecord(
        loan_application_id="loan-123",
        created_timestamp="2024-01-15T10:35:00Z"
    )
    gr.name = GoldenRecordField(
        value="John Doe",
        source_document="doc-1",
        confidence=0.98,
        alternative_values=["Jon Doe"]
    )
    gr.annual_income = GoldenRecordField(
        value=75000.00,
        source_document="doc-2",
        confidence=0.99,
        verified_by=["doc-3"]
    )
    
    # Convert to JSON and back
    json_str = gr.to_json()
    gr_restored = GoldenRecord.from_json(json_str)
    
    assert gr_restored.loan_application_id == "loan-123"
    assert gr_restored.name.value == "John Doe"
    assert gr_restored.annual_income.value == 75000.00


def test_inconsistency_serialization():
    """Test Inconsistency serialization and deserialization."""
    inc = Inconsistency(
        inconsistency_id="inc-1",
        field="name",
        severity="CRITICAL",
        expected_value="John Doe",
        actual_value="Jon Doe",
        source_documents=["doc-1", "doc-2"],
        description="Name spelling variation",
        detected_by="cross_document_validator"
    )
    
    # Convert to JSON and back
    json_str = inc.to_json()
    inc_restored = Inconsistency.from_json(json_str)
    
    assert inc_restored.inconsistency_id == "inc-1"
    assert inc_restored.field == "name"
    assert inc_restored.severity == "CRITICAL"
    assert inc_restored.expected_value == "John Doe"


def test_audit_record_serialization():
    """Test AuditRecord serialization and deserialization."""
    inc = Inconsistency(
        inconsistency_id="inc-1",
        field="name",
        severity="CRITICAL",
        expected_value="John Doe",
        actual_value="Jon Doe",
        source_documents=["doc-1", "doc-2"],
        description="Name spelling variation",
        detected_by="cross_document_validator"
    )
    
    rf = RiskFactor(
        factor="name_inconsistency",
        points=15,
        description="Name mismatch detected"
    )
    
    alert = Alert(
        alert_type="HIGH_RISK",
        timestamp="2024-01-15T10:35:00Z",
        notification_sent=True
    )
    
    audit = AuditRecord(
        audit_record_id="audit-1",
        loan_application_id="loan-123",
        applicant_name="John Doe",
        audit_timestamp="2024-01-15T10:35:00Z",
        processing_duration_seconds=45,
        status="COMPLETED",
        documents=[{"document_id": "doc-1", "document_type": "W2"}],
        golden_record={"name": "John Doe"},
        inconsistencies=[inc],
        risk_score=45,
        risk_level="MEDIUM",
        risk_factors=[rf],
        alerts_triggered=[alert]
    )
    
    # Convert to JSON and back
    json_str = audit.to_json()
    audit_restored = AuditRecord.from_json(json_str)
    
    assert audit_restored.audit_record_id == "audit-1"
    assert audit_restored.risk_score == 45
    assert audit_restored.risk_level == "MEDIUM"
    assert len(audit_restored.inconsistencies) == 1
    assert len(audit_restored.risk_factors) == 1
    assert len(audit_restored.alerts_triggered) == 1
