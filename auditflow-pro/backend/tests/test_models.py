import pytest
from hypothesis import given, strategies as st
from shared.models import ExtractedField, DocumentMetadata

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
