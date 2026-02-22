import os
import pytest
import boto3
from moto import mock_aws
from shared.repositories import DocumentRepository
from shared.models import DocumentMetadata

# Set environment variables for testing
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
os.environ['DOCUMENTS_TABLE'] = 'AuditFlow-Documents-Test'

@pytest.fixture
def dynamodb_mock():
    """Fixture to set up the mocked DynamoDB table."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Create the mock table matching our infrastructure design
        table = dynamodb.create_table(
            TableName=os.environ['DOCUMENTS_TABLE'],
            KeySchema=[{'AttributeName': 'document_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'document_id', 'AttributeType': 'S'},
                {'AttributeName': 'loan_application_id', 'AttributeType': 'S'},
                {'AttributeName': 'upload_timestamp', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'loan_application_id-upload_timestamp-index',
                    'KeySchema': [
                        {'AttributeName': 'loan_application_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'upload_timestamp', 'KeyType': 'RANGE'}
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
