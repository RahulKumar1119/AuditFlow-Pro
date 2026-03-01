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
        self.s3 = s3_client or boto3.client('s3', config=Config(signature_version='s3v4', region_name=os.environ.get('AWS_REGION', 'ap-south-1')))
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

    def get_document_metadata(self, object_key: str) -> dict:
        """
        Retrieves metadata for a document from S3.
        Returns metadata including checksum, size, last modified date, and storage class.
        """
        try:
            response = self.s3.head_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            metadata = {
                'content_length': response.get('ContentLength'),
                'last_modified': response.get('LastModified'),
                'content_type': response.get('ContentType'),
                'storage_class': response.get('StorageClass', 'STANDARD'),
                'checksum': response.get('Metadata', {}).get('checksum'),
                'server_side_encryption': response.get('ServerSideEncryption'),
                'etag': response.get('ETag')
            }
            logger.info(f"Retrieved metadata for {object_key}")
            return metadata
        except ClientError as e:
            logger.error(f"Failed to retrieve metadata for {object_key}: {e.response['Error']['Message']}")
            raise

    def retrieve_document(self, object_key: str, download_path: str = None) -> bytes:
        """
        Retrieves a document from S3.
        If download_path is provided, saves to file. Otherwise returns bytes.
        """
        try:
            if download_path:
                self.s3.download_file(self.bucket_name, object_key, download_path)
                logger.info(f"Downloaded {object_key} to {download_path}")
                return None
            else:
                response = self.s3.get_object(
                    Bucket=self.bucket_name,
                    Key=object_key
                )
                content = response['Body'].read()
                logger.info(f"Retrieved {object_key} content ({len(content)} bytes)")
                return content
        except ClientError as e:
            logger.error(f"Failed to retrieve {object_key}: {e.response['Error']['Message']}")
            raise

    def archive_document(self, object_key: str) -> bool:
        """
        Explicitly moves a document to S3 Glacier storage.
        This supports manual archival in addition to automated lifecycle policies.
        """
        try:
            self.s3.copy_object(
                Bucket=self.bucket_name,
                CopySource={'Bucket': self.bucket_name, 'Key': object_key},
                Key=object_key,
                StorageClass='GLACIER',
                MetadataDirective='COPY'
            )
            logger.info(f"Successfully archived {object_key} to GLACIER storage.")
            return True
        except ClientError as e:
            logger.error(f"Failed to archive {object_key}: {e.response['Error']['Message']}")
            raise

    def delete_document(self, object_key: str) -> bool:
        """
        Deletes a document from S3.
        This operation is permanent and should be used carefully.
        Logs the deletion operation for audit trail compliance.
        """
        try:
            self.s3.delete_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            logger.info(f"Successfully deleted {object_key} from {self.bucket_name}")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete {object_key}: {e.response['Error']['Message']}")
            raise

    def restore_archived_document(self, object_key: str, days: int = 1, tier: str = 'Standard') -> bool:
        """
        Initiates restoration of an archived document from Glacier.
        Supports 24-hour retrieval time as per requirements.
        
        Args:
            object_key: The S3 key of the archived document
            days: Number of days to keep the restored copy (default 1)
            tier: Retrieval tier - 'Expedited' (1-5 min), 'Standard' (3-5 hours), or 'Bulk' (5-12 hours)
        """
        try:
            self.s3.restore_object(
                Bucket=self.bucket_name,
                Key=object_key,
                RestoreRequest={
                    'Days': days,
                    'GlacierJobParameters': {
                        'Tier': tier
                    }
                }
            )
            logger.info(f"Initiated restoration of {object_key} from Glacier with tier {tier}")
            return True
        except ClientError as e:
            # If already restored, this is not an error
            if e.response['Error']['Code'] == 'RestoreAlreadyInProgress':
                logger.info(f"Restoration already in progress for {object_key}")
                return True
            logger.error(f"Failed to restore {object_key}: {e.response['Error']['Message']}")
            raise

    def check_restore_status(self, object_key: str) -> dict:
        """
        Checks the restoration status of an archived document.
        Returns status information including whether restoration is complete.
        """
        try:
            response = self.s3.head_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            restore_status = response.get('Restore')
            
            if restore_status is None:
                status = {
                    'is_archived': response.get('StorageClass') == 'GLACIER',
                    'is_restored': False,
                    'restore_in_progress': False
                }
            elif 'ongoing-request="true"' in restore_status:
                status = {
                    'is_archived': True,
                    'is_restored': False,
                    'restore_in_progress': True
                }
            else:
                status = {
                    'is_archived': True,
                    'is_restored': True,
                    'restore_in_progress': False,
                    'restore_expiry': restore_status
                }
            
            logger.info(f"Checked restore status for {object_key}: {status}")
            return status
        except ClientError as e:
            logger.error(f"Failed to check restore status for {object_key}: {e.response['Error']['Message']}")
            raise
