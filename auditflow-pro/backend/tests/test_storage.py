import os
import pytest
import boto3
from moto import mock_aws
from botocore.exceptions import ClientError
from shared.storage import S3DocumentManager

# Setup environment variables for the test
os.environ['AWS_DEFAULT_REGION'] = 'ap-south-1'
os.environ['S3_DOCUMENT_BUCKET'] = 'auditflow-test-bucket'

@pytest.fixture
def s3_mock():
    with mock_aws():
        s3 = boto3.client('s3', region_name='ap-south-1')
        s3.create_bucket(Bucket=os.environ['S3_DOCUMENT_BUCKET'])
        yield s3

@pytest.fixture
def storage_manager(s3_mock):
    return S3DocumentManager(s3_client=s3_mock)

@pytest.fixture
def dummy_file(tmp_path):
    """Creates a temporary file to use for upload testing."""
    file_path = tmp_path / "test_doc.pdf"
    file_path.write_text("Dummy PDF content for testing checksums.")
    return str(file_path)

def test_upload_document_with_checksum(storage_manager, dummy_file, s3_mock):
    """Test that file uploads successfully and generates a valid checksum."""
    object_key = "loans/123/w2.pdf"
    
    # Perform upload
    checksum = storage_manager.upload_document(dummy_file, object_key)
    
    # Assert checksum is returned and is a valid sha256 length (64 chars)
    assert checksum is not None
    assert len(checksum) == 64
    
    # Verify the file actually exists in the mocked S3 bucket
    response = s3_mock.head_object(Bucket=os.environ['S3_DOCUMENT_BUCKET'], Key=object_key)
    assert response['ResponseMetadata']['HTTPStatusCode'] == 200
    assert response['Metadata']['checksum'] == checksum

def test_generate_presigned_url(storage_manager, dummy_file):
    """Test generating a secure download URL."""
    object_key = "loans/123/w2.pdf"
    storage_manager.upload_document(dummy_file, object_key)
    
    # Generate URL
    url = storage_manager.generate_presigned_download_url(object_key, expiration_seconds=600)
    
    # Basic validations
    assert url is not None
    assert url.startswith("https://") or url.startswith("http://") # moto can return http for local mocks
    assert object_key in url
    # Check for signature parameters (moto uses older signature format)
    assert "Signature" in url or "X-Amz-Signature" in url

def test_upload_error_handling(storage_manager, dummy_file):
    """Test error handling for a non-existent bucket."""
    # Force an error by pointing to a bucket that hasn't been created in the mock
    storage_manager.bucket_name = "non-existent-bucket"
    
    # boto3 wraps ClientError in S3UploadFailedError for upload operations
    with pytest.raises(Exception):  # Can be either ClientError or S3UploadFailedError
        storage_manager.upload_document(dummy_file, "test.pdf")

def test_get_document_metadata(storage_manager, dummy_file, s3_mock):
    """Test retrieving document metadata from S3."""
    object_key = "loans/123/w2.pdf"
    checksum = storage_manager.upload_document(dummy_file, object_key)
    
    # Get metadata
    metadata = storage_manager.get_document_metadata(object_key)
    
    # Verify metadata fields
    assert metadata is not None
    assert metadata['content_length'] > 0
    assert metadata['last_modified'] is not None
    assert metadata['storage_class'] == 'STANDARD'
    assert metadata['checksum'] == checksum
    assert metadata['server_side_encryption'] == 'aws:kms'

def test_retrieve_document_as_bytes(storage_manager, dummy_file, s3_mock):
    """Test retrieving document content as bytes."""
    object_key = "loans/123/w2.pdf"
    storage_manager.upload_document(dummy_file, object_key)
    
    # Retrieve as bytes
    content = storage_manager.retrieve_document(object_key)
    
    # Verify content
    assert content is not None
    assert isinstance(content, bytes)
    assert len(content) > 0

def test_retrieve_document_to_file(storage_manager, dummy_file, tmp_path, s3_mock):
    """Test retrieving document and saving to file."""
    object_key = "loans/123/w2.pdf"
    storage_manager.upload_document(dummy_file, object_key)
    
    # Retrieve to file
    download_path = str(tmp_path / "downloaded.pdf")
    result = storage_manager.retrieve_document(object_key, download_path)
    
    # Verify file was created
    assert result is None  # Returns None when saving to file
    assert os.path.exists(download_path)
    assert os.path.getsize(download_path) > 0

def test_archive_document(storage_manager, dummy_file, s3_mock):
    """Test archiving a document to Glacier storage."""
    object_key = "loans/123/w2.pdf"
    storage_manager.upload_document(dummy_file, object_key)
    
    # Archive the document
    result = storage_manager.archive_document(object_key)
    
    # Verify archival
    assert result is True
    metadata = storage_manager.get_document_metadata(object_key)
    assert metadata['storage_class'] == 'GLACIER'

def test_delete_document(storage_manager, dummy_file, s3_mock):
    """Test deleting a document from S3."""
    object_key = "loans/123/w2.pdf"
    storage_manager.upload_document(dummy_file, object_key)
    
    # Delete the document
    result = storage_manager.delete_document(object_key)
    
    # Verify deletion
    assert result is True
    with pytest.raises(ClientError) as exc_info:
        storage_manager.get_document_metadata(object_key)
    assert exc_info.value.response['Error']['Code'] == '404'

def test_restore_archived_document(storage_manager, dummy_file, s3_mock):
    """Test initiating restoration of an archived document."""
    object_key = "loans/123/w2.pdf"
    storage_manager.upload_document(dummy_file, object_key)
    storage_manager.archive_document(object_key)
    
    # Initiate restoration
    result = storage_manager.restore_archived_document(object_key, days=2, tier='Standard')
    
    # Verify restoration initiated
    assert result is True

def test_restore_already_in_progress(storage_manager, dummy_file, s3_mock):
    """Test handling of restoration already in progress."""
    object_key = "loans/123/w2.pdf"
    storage_manager.upload_document(dummy_file, object_key)
    storage_manager.archive_document(object_key)
    
    # Initiate restoration twice
    storage_manager.restore_archived_document(object_key)
    result = storage_manager.restore_archived_document(object_key)
    
    # Should still return True (not an error)
    assert result is True

def test_check_restore_status_not_archived(storage_manager, dummy_file, s3_mock):
    """Test checking restore status for a non-archived document."""
    object_key = "loans/123/w2.pdf"
    storage_manager.upload_document(dummy_file, object_key)
    
    # Check status
    status = storage_manager.check_restore_status(object_key)
    
    # Verify status
    assert status is not None
    assert status['is_archived'] is False
    assert status['is_restored'] is False
    assert status['restore_in_progress'] is False

def test_check_restore_status_archived(storage_manager, dummy_file, s3_mock):
    """Test checking restore status for an archived document."""
    object_key = "loans/123/w2.pdf"
    storage_manager.upload_document(dummy_file, object_key)
    storage_manager.archive_document(object_key)
    
    # Check status
    status = storage_manager.check_restore_status(object_key)
    
    # Verify status
    assert status is not None
    assert status['is_archived'] is True

def test_metadata_error_handling(storage_manager):
    """Test error handling when retrieving metadata for non-existent document."""
    with pytest.raises(ClientError):
        storage_manager.get_document_metadata("non-existent-key")

def test_retrieve_error_handling(storage_manager):
    """Test error handling when retrieving non-existent document."""
    with pytest.raises(ClientError):
        storage_manager.retrieve_document("non-existent-key")

def test_delete_error_handling(storage_manager):
    """Test error handling when deleting non-existent document."""
    # Note: S3 delete is idempotent and doesn't error on non-existent keys
    # But we can test with invalid bucket
    storage_manager.bucket_name = "non-existent-bucket"
    with pytest.raises(ClientError):
        storage_manager.delete_document("test.pdf")
