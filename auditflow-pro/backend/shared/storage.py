import os
import boto3
import hashlib
import logging
from botocore.exceptions import ClientError
from botocore.config import Config

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class S3DocumentManager:
    def __init__(self, s3_client=None):
        # We enforce signature_version='s3v4' which is required for secure pre-signed URLs
        self.s3 = s3_client or boto3.client('s3', config=Config(signature_version='s3v4', region_name=os.environ.get('AWS_REGION', 'us-east-1')))
        self.bucket_name = os.environ.get('S3_DOCUMENT_BUCKET', 'auditflow-documents-prod')

    def upload_document(self, file_path: str, object_key: str) -> str:
        """
        Uploads a document to S3, calculating a SHA-256 checksum for integrity.
        Returns the calculated checksum.
        """
        # Calculate checksum
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        file_hash = sha256_hash.hexdigest()

        try:
            self.s3.upload_file(
                file_path, 
                self.bucket_name, 
                object_key,
                ExtraArgs={
                    'Metadata': {'checksum': file_hash},
                    'ServerSideEncryption': 'aws:kms' # Enforces KMS encryption at rest
                }
            )
            logger.info(f"Successfully uploaded {object_key} to {self.bucket_name} with checksum {file_hash}")
            return file_hash
        except ClientError as e:
            logger.error(f"Failed to upload {object_key}: {e.response['Error']['Message']}")
            raise

    def generate_presigned_download_url(self, object_key: str, expiration_seconds: int = 3600) -> str:
        """
        Generates a secure, temporary URL for the frontend Document Viewer.
        """
        try:
            url = self.s3.generate_presigned_url(
                ClientMethod='get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_key
                },
                ExpiresIn=expiration_seconds
            )
            logger.info(f"Generated pre-signed URL for {object_key}")
            return url
        except ClientError as e:
            logger.error(f"Failed to generate pre-signed URL for {object_key}: {e.response['Error']['Message']}")
            raise

    def archive_document_manually(self, object_key: str) -> bool:
        """
        Explicitly moves a document to S3 Glacier.
        (Note: We also set up automated lifecycle policies for this in step 2).
        """
        try:
            self.s3.copy_object(
                Bucket=self.bucket_name,
                CopySource={'Bucket': self.bucket_name, 'Key': object_key},
                Key=object_key,
                StorageClass='GLACIER'
            )
            logger.info(f"Successfully archived {object_key} to GLACIER storage.")
            return True
        except ClientError as e:
            logger.error(f"Failed to archive {object_key}: {e.response['Error']['Message']}")
            raise
