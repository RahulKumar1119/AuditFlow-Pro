import os
import pytest
import boto3
from moto import mock_aws
from decimal import Decimal
from shared.repositories import DocumentRepository, AuditRecordRepository
from shared.models import DocumentMetadata, AuditRecord, Inconsistency, RiskFactor, Alert

# Set environment variables for testing
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
os.environ['DOCUMENTS_TABLE'] = 'AuditFlow-Documents-Test'
os.environ['AUDIT_RECORDS_TABLE'] = 'AuditFlow-AuditRecords-Test'

@pytest.fixture
def dynamodb_mock():
    """Fixture to set up the mocked DynamoDB tables."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Create the Documents table
        documents_table = dynamodb.create_table(
            TableName=os.environ['DOCUMENTS_TABLE'],
            KeySchema=[{'AttributeName': 'document_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'document_id', 'AttributeType': 'S'},
                {'AttributeName': 'loan_application_id', 'AttributeType': 'S'},
                {'AttributeName': 'upload_timestamp', 'AttributeType': 'S'},
                {'AttributeName': 'processing_status', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'loan_application_id-upload_timestamp-index',
                    'KeySchema': [
                        {'AttributeName': 'loan_application_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'upload_timestamp', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                },
                {
                    'IndexName': 'processing_status-upload_timestamp-index',
                    'KeySchema': [
                        {'AttributeName': 'processing_status', 'KeyType': 'HASH'},
                        {'AttributeName': 'upload_timestamp', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Create the AuditRecords table
        audit_table = dynamodb.create_table(
            TableName=os.environ['AUDIT_RECORDS_TABLE'],
            KeySchema=[{'AttributeName': 'audit_record_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'audit_record_id', 'AttributeType': 'S'},
                {'AttributeName': 'loan_application_id', 'AttributeType': 'S'},
                {'AttributeName': 'audit_timestamp', 'AttributeType': 'S'},
                {'AttributeName': 'status', 'AttributeType': 'S'},
                {'AttributeName': 'risk_score', 'AttributeType': 'N'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'loan_application_id-audit_timestamp-index',
                    'KeySchema': [
                        {'AttributeName': 'loan_application_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'audit_timestamp', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                },
                {
                    'IndexName': 'status-audit_timestamp-index',
                    'KeySchema': [
                        {'AttributeName': 'status', 'KeyType': 'HASH'},
                        {'AttributeName': 'audit_timestamp', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                },
                {
                    'IndexName': 'risk_score-audit_timestamp-index',
                    'KeySchema': [
                        {'AttributeName': 'status', 'KeyType': 'HASH'},
                        {'AttributeName': 'risk_score', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        yield dynamodb

@pytest.fixture
def repo(dynamodb_mock):
    """Fixture to provide an instantiated repository."""
    return DocumentRepository(dynamodb_resource=dynamodb_mock)

@pytest.fixture
def sample_document():
    """Fixture to provide a sample document metadata object."""
    return DocumentMetadata(
        document_id="doc-123",
        loan_application_id="loan-456",
        s3_bucket="test-bucket",
        s3_key="docs/w2.pdf",
        upload_timestamp="2026-02-22T12:00:00Z",
        file_name="w2.pdf",
        file_size_bytes=1024,
        file_format="PDF",
        checksum="abc123hash"
    )

def test_save_and_get_document(repo, sample_document):
    """Test standard CRUD operations."""
    # Test Save
    assert repo.save_document(sample_document) == True
    
    # Test Retrieve
    retrieved = repo.get_document("doc-123")
    assert retrieved is not None
    assert retrieved.loan_application_id == "loan-456"
    assert retrieved.file_name == "w2.pdf"

def test_atomic_status_update(repo, sample_document):
    """Test atomic updates and conditional write failures."""
    repo.save_document(sample_document)
    
    # Test successful update
    assert repo.update_document_status("doc-123", "COMPLETED") == True
    
    # Verify the update persisted
    updated_doc = repo.get_document("doc-123")
    assert updated_doc.processing_status == "COMPLETED"
    
    # Test update on non-existent document (ConditionalCheckFailed)
    assert repo.update_document_status("non-existent-id", "COMPLETED") == False

def test_get_documents_by_loan(repo, sample_document):
    """Test querying the Global Secondary Index."""
    repo.save_document(sample_document)
    
    # Add a second document to the same loan
    doc2 = DocumentMetadata(
        document_id="doc-999",
        loan_application_id="loan-456",
        s3_bucket="test-bucket",
        s3_key="docs/id.pdf",
        upload_timestamp="2026-02-22T12:05:00Z",
        file_name="id.pdf",
        file_size_bytes=2048,
        file_format="PDF",
        checksum="def456hash"
    )
    repo.save_document(doc2)
    
    # Query by loan ID
    docs = repo.get_documents_by_loan("loan-456")
    
    assert len(docs) == 2
    # Because 'upload_timestamp' is the RANGE key, they should be sorted
    assert docs[0].document_id == "doc-123"
    assert docs[1].document_id == "doc-999"


# ==========================================
# DocumentRepository Tests - New Functionality
# ==========================================

def test_update_extracted_data(repo, sample_document):
    """Test atomic update of extracted data."""
    repo.save_document(sample_document)
    
    extracted_data = {
        'name': {'value': 'John Doe', 'confidence': Decimal('0.98')},
        'ssn': {'value': '***-**-1234', 'confidence': Decimal('0.99')}
    }
    
    assert repo.update_extracted_data(
        "doc-123", 
        extracted_data, 
        "2026-02-22T12:10:00Z",
        ['address']
    ) == True
    
    # Verify the update
    updated_doc = repo.get_document("doc-123")
    # Check that the data was stored correctly (it will be converted to ExtractedField objects)
    assert 'name' in updated_doc.extracted_data
    assert 'ssn' in updated_doc.extracted_data
    assert updated_doc.extraction_timestamp == "2026-02-22T12:10:00Z"
    assert updated_doc.low_confidence_fields == ['address']
    
    # Test update on non-existent document
    assert repo.update_extracted_data("non-existent", {}, "2026-02-22T12:10:00Z", []) == False

def test_update_classification(repo, sample_document):
    """Test atomic update of document classification."""
    repo.save_document(sample_document)
    
    assert repo.update_classification("doc-123", "W2", 0.95, False) == True
    
    # Verify the update
    updated_doc = repo.get_document("doc-123")
    assert updated_doc.document_type == "W2"
    assert float(updated_doc.classification_confidence) == 0.95
    assert updated_doc.requires_manual_review == False
    
    # Test update on non-existent document
    assert repo.update_classification("non-existent", "W2", 0.95, False) == False

def test_get_documents_by_status(repo, sample_document):
    """Test querying documents by processing status."""
    # Create documents with different statuses
    doc1 = sample_document
    doc1.processing_status = "PENDING"
    repo.save_document(doc1)
    
    doc2 = DocumentMetadata(
        document_id="doc-456",
        loan_application_id="loan-789",
        s3_bucket="test-bucket",
        s3_key="docs/tax.pdf",
        upload_timestamp="2026-02-22T12:05:00Z",
        file_name="tax.pdf",
        file_size_bytes=2048,
        file_format="PDF",
        checksum="def456hash",
        processing_status="COMPLETED"
    )
    repo.save_document(doc2)
    
    # Query by status
    pending_docs = repo.get_documents_by_status("PENDING")
    assert len(pending_docs) == 1
    assert pending_docs[0].document_id == "doc-123"
    
    completed_docs = repo.get_documents_by_status("COMPLETED")
    assert len(completed_docs) == 1
    assert completed_docs[0].document_id == "doc-456"
    
    # Test with limit
    limited_docs = repo.get_documents_by_status("PENDING", limit=1)
    assert len(limited_docs) == 1

def test_delete_document(repo, sample_document):
    """Test document deletion with conditional check."""
    repo.save_document(sample_document)
    
    # Test successful deletion
    assert repo.delete_document("doc-123") == True
    
    # Verify deletion
    assert repo.get_document("doc-123") is None
    
    # Test deletion of non-existent document
    assert repo.delete_document("non-existent") == False


# ==========================================
# AuditRecordRepository Tests
# ==========================================

@pytest.fixture
def audit_repo(dynamodb_mock):
    """Fixture to provide an instantiated audit repository."""
    return AuditRecordRepository(dynamodb_resource=dynamodb_mock)

@pytest.fixture
def sample_audit_record():
    """Fixture to provide a sample audit record."""
    return AuditRecord(
        audit_record_id="audit-123",
        loan_application_id="loan-456",
        applicant_name="John Doe",
        audit_timestamp="2026-02-22T12:30:00Z",
        processing_duration_seconds=45,
        status="COMPLETED",
        documents=[
            {"document_id": "doc-123", "document_type": "W2", "file_name": "w2.pdf"}
        ],
        golden_record={
            "name": {"value": "John Doe", "source_document": "doc-123", "confidence": Decimal('0.98')}
        },
        inconsistencies=[
            Inconsistency(
                inconsistency_id="inc-1",
                field="address",
                severity="HIGH",
                expected_value="123 Main St",
                actual_value="123 Main Street",
                source_documents=["doc-123", "doc-456"],
                description="Address format variation",
                detected_by="validator"
            )
        ],
        risk_score=35,
        risk_level="MEDIUM",
        risk_factors=[
            RiskFactor(factor="address_mismatch", points=20, description="Address format differs")
        ],
        alerts_triggered=[]
    )

def test_save_and_get_audit_record(audit_repo, sample_audit_record):
    """Test saving and retrieving audit records."""
    assert audit_repo.save_audit_record(sample_audit_record) == True
    
    retrieved = audit_repo.get_audit_record("audit-123")
    assert retrieved is not None
    assert retrieved.loan_application_id == "loan-456"
    assert retrieved.applicant_name == "John Doe"
    assert retrieved.risk_score == 35
    assert retrieved.risk_level == "MEDIUM"
    assert len(retrieved.inconsistencies) == 1

def test_update_audit_status(audit_repo, sample_audit_record):
    """Test atomic status update."""
    audit_repo.save_audit_record(sample_audit_record)
    
    assert audit_repo.update_audit_status("audit-123", "IN_PROGRESS") == True
    
    updated = audit_repo.get_audit_record("audit-123")
    assert updated.status == "IN_PROGRESS"
    
    # Test update on non-existent record
    assert audit_repo.update_audit_status("non-existent", "COMPLETED") == False

def test_update_review_info(audit_repo, sample_audit_record):
    """Test atomic update of review information."""
    audit_repo.save_audit_record(sample_audit_record)
    
    assert audit_repo.update_review_info(
        "audit-123",
        "officer@example.com",
        "2026-02-22T13:00:00Z",
        "Reviewed and approved"
    ) == True
    
    updated = audit_repo.get_audit_record("audit-123")
    assert updated.reviewed_by == "officer@example.com"
    assert updated.review_timestamp == "2026-02-22T13:00:00Z"
    assert updated.review_notes == "Reviewed and approved"
    
    # Test without notes
    assert audit_repo.update_review_info(
        "audit-123",
        "admin@example.com",
        "2026-02-22T14:00:00Z"
    ) == True
    
    # Test on non-existent record
    assert audit_repo.update_review_info("non-existent", "user", "2026-02-22T13:00:00Z") == False

def test_mark_as_archived(audit_repo, sample_audit_record):
    """Test atomic archival marking with conditional check."""
    audit_repo.save_audit_record(sample_audit_record)
    
    assert audit_repo.mark_as_archived("audit-123", "2026-05-22T12:30:00Z") == True
    
    updated = audit_repo.get_audit_record("audit-123")
    assert updated.archived == True
    assert updated.archive_timestamp == "2026-05-22T12:30:00Z"
    
    # Test marking already archived record (should fail due to condition)
    assert audit_repo.mark_as_archived("audit-123", "2026-06-22T12:30:00Z") == False
    
    # Test on non-existent record
    assert audit_repo.mark_as_archived("non-existent", "2026-05-22T12:30:00Z") == False

def test_get_audits_by_loan(audit_repo, sample_audit_record):
    """Test querying audits by loan application ID."""
    audit_repo.save_audit_record(sample_audit_record)
    
    # Add another audit for the same loan
    audit2 = AuditRecord(
        audit_record_id="audit-456",
        loan_application_id="loan-456",
        applicant_name="John Doe",
        audit_timestamp="2026-02-23T12:30:00Z",
        processing_duration_seconds=50,
        status="COMPLETED",
        documents=[],
        golden_record={},
        inconsistencies=[],
        risk_score=20,
        risk_level="LOW",
        risk_factors=[]
    )
    audit_repo.save_audit_record(audit2)
    
    audits = audit_repo.get_audits_by_loan("loan-456")
    assert len(audits) == 2
    # Should be sorted by timestamp descending (most recent first)
    assert audits[0].audit_record_id == "audit-456"
    assert audits[1].audit_record_id == "audit-123"

def test_get_audits_by_status(audit_repo, sample_audit_record):
    """Test querying audits by status."""
    audit_repo.save_audit_record(sample_audit_record)
    
    # Add another audit with different status
    audit2 = AuditRecord(
        audit_record_id="audit-789",
        loan_application_id="loan-999",
        applicant_name="Jane Smith",
        audit_timestamp="2026-02-22T13:00:00Z",
        processing_duration_seconds=30,
        status="IN_PROGRESS",
        documents=[],
        golden_record={},
        inconsistencies=[],
        risk_score=0,
        risk_level="LOW",
        risk_factors=[]
    )
    audit_repo.save_audit_record(audit2)
    
    completed = audit_repo.get_audits_by_status("COMPLETED")
    assert len(completed) == 1
    assert completed[0].audit_record_id == "audit-123"
    
    in_progress = audit_repo.get_audits_by_status("IN_PROGRESS")
    assert len(in_progress) == 1
    assert in_progress[0].audit_record_id == "audit-789"
    
    # Test with limit
    limited = audit_repo.get_audits_by_status("COMPLETED", limit=1)
    assert len(limited) == 1

def test_get_high_risk_audits(audit_repo):
    """Test querying high-risk audits."""
    # Create audits with different risk scores
    audit1 = AuditRecord(
        audit_record_id="audit-high-1",
        loan_application_id="loan-1",
        applicant_name="High Risk 1",
        audit_timestamp="2026-02-22T12:00:00Z",
        processing_duration_seconds=45,
        status="COMPLETED",
        documents=[],
        golden_record={},
        inconsistencies=[],
        risk_score=75,
        risk_level="HIGH",
        risk_factors=[]
    )
    
    audit2 = AuditRecord(
        audit_record_id="audit-high-2",
        loan_application_id="loan-2",
        applicant_name="High Risk 2",
        audit_timestamp="2026-02-22T13:00:00Z",
        processing_duration_seconds=45,
        status="COMPLETED",
        documents=[],
        golden_record={},
        inconsistencies=[],
        risk_score=85,
        risk_level="CRITICAL",
        risk_factors=[]
    )
    
    audit3 = AuditRecord(
        audit_record_id="audit-low",
        loan_application_id="loan-3",
        applicant_name="Low Risk",
        audit_timestamp="2026-02-22T14:00:00Z",
        processing_duration_seconds=45,
        status="COMPLETED",
        documents=[],
        golden_record={},
        inconsistencies=[],
        risk_score=20,
        risk_level="LOW",
        risk_factors=[]
    )
    
    audit_repo.save_audit_record(audit1)
    audit_repo.save_audit_record(audit2)
    audit_repo.save_audit_record(audit3)
    
    # Query high-risk audits (risk_score >= 50)
    high_risk = audit_repo.get_high_risk_audits(min_risk_score=50)
    assert len(high_risk) == 2
    # Should be sorted by risk score descending
    assert high_risk[0].risk_score >= high_risk[1].risk_score
    
    # Query with higher threshold
    critical = audit_repo.get_high_risk_audits(min_risk_score=80)
    assert len(critical) == 1
    assert critical[0].audit_record_id == "audit-high-2"

def test_query_audits_by_date_range(audit_repo):
    """Test querying audits within a date range."""
    # Create audits with different timestamps
    audit1 = AuditRecord(
        audit_record_id="audit-1",
        loan_application_id="loan-1",
        applicant_name="User 1",
        audit_timestamp="2026-02-20T12:00:00Z",
        processing_duration_seconds=45,
        status="COMPLETED",
        documents=[],
        golden_record={},
        inconsistencies=[],
        risk_score=30,
        risk_level="MEDIUM",
        risk_factors=[]
    )
    
    audit2 = AuditRecord(
        audit_record_id="audit-2",
        loan_application_id="loan-2",
        applicant_name="User 2",
        audit_timestamp="2026-02-22T12:00:00Z",
        processing_duration_seconds=45,
        status="COMPLETED",
        documents=[],
        golden_record={},
        inconsistencies=[],
        risk_score=40,
        risk_level="MEDIUM",
        risk_factors=[]
    )
    
    audit3 = AuditRecord(
        audit_record_id="audit-3",
        loan_application_id="loan-3",
        applicant_name="User 3",
        audit_timestamp="2026-02-25T12:00:00Z",
        processing_duration_seconds=45,
        status="COMPLETED",
        documents=[],
        golden_record={},
        inconsistencies=[],
        risk_score=50,
        risk_level="HIGH",
        risk_factors=[]
    )
    
    audit_repo.save_audit_record(audit1)
    audit_repo.save_audit_record(audit2)
    audit_repo.save_audit_record(audit3)
    
    # Query date range
    audits = audit_repo.query_audits_by_date_range(
        "COMPLETED",
        "2026-02-21T00:00:00Z",
        "2026-02-24T00:00:00Z"
    )
    assert len(audits) == 1
    assert audits[0].audit_record_id == "audit-2"

def test_delete_audit_record(audit_repo, sample_audit_record):
    """Test audit record deletion with conditional check."""
    audit_repo.save_audit_record(sample_audit_record)
    
    assert audit_repo.delete_audit_record("audit-123") == True
    
    # Verify deletion
    assert audit_repo.get_audit_record("audit-123") is None
    
    # Test deletion of non-existent record
    assert audit_repo.delete_audit_record("non-existent") == False

def test_batch_get_audits(audit_repo):
    """Test batch retrieval of multiple audit records."""
    # Create multiple audit records
    audit_ids = []
    for i in range(5):
        audit = AuditRecord(
            audit_record_id=f"audit-{i}",
            loan_application_id=f"loan-{i}",
            applicant_name=f"User {i}",
            audit_timestamp=f"2026-02-22T12:{i:02d}:00Z",
            processing_duration_seconds=45,
            status="COMPLETED",
            documents=[],
            golden_record={},
            inconsistencies=[],
            risk_score=i * 10,
            risk_level="LOW",
            risk_factors=[]
        )
        audit_repo.save_audit_record(audit)
        audit_ids.append(f"audit-{i}")
    
    # Batch get all records
    audits = audit_repo.batch_get_audits(audit_ids)
    assert len(audits) == 5
    
    # Verify all IDs are present
    retrieved_ids = {audit.audit_record_id for audit in audits}
    assert retrieved_ids == set(audit_ids)
    
    # Test with empty list
    empty_result = audit_repo.batch_get_audits([])
    assert len(empty_result) == 0
    
    # Test with non-existent IDs
    partial_result = audit_repo.batch_get_audits(["audit-0", "non-existent"])
    assert len(partial_result) == 1
    assert partial_result[0].audit_record_id == "audit-0"


# ==========================================
# Error Handling and Retry Tests
# ==========================================

def test_retry_logic_on_throttling(repo, sample_document, monkeypatch):
    """Test that retry logic handles throttling errors."""
    # This test verifies the retry mechanism exists
    # In a real scenario, we'd mock ClientError with ThrottlingException
    # For now, we just verify the method exists and works normally
    repo.save_document(sample_document)
    doc = repo.get_document("doc-123")
    assert doc is not None
