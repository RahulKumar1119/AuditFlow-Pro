import os
import pytest
import boto3
from moto import mock_aws
from botocore.exceptions import ClientError
from shared.storage import S3DocumentManager

# Setup environment variables for the test
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
os.environ['S3_DOCUMENT_BUCKET'] = 'auditflow-test-bucket'

@pytest.fixture
def s3_mock():
    with mock_aws():
        s3 = boto3.client('s3', region_name='us-east-1')
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
    assert "X-Amz-Signature" in url

def test_upload_error_handling(storage_manager, dummy_file):
    """Test error handling for a non-existent bucket."""
    # Force an error by pointing to a bucket that hasn't been created in the mock
    storage_manager.bucket_name = "non-existent-bucket"
    
    with pytest.raises(ClientError):
        storage_manager.upload_document(dummy_file, "test.pdf")
