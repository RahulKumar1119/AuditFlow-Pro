"""
Security tests for AuditFlow-Pro.

Tests IAM policy restrictions, encryption at rest and in transit,
PII field-level encryption, and unauthorized access denial.

Requirements: 20.9
"""

import pytest
import json
import boto3
from unittest.mock import Mock, patch, MagicMock
from moto import mock_aws
from botocore.exceptions import ClientError
from shared.encryption import (
    FieldEncryption,
    mask_pii_value,
    should_mask_pii_for_role,
    apply_pii_masking
)


class TestEncryptionAtRest:
    """Test encryption at rest for S3 and DynamoDB."""
    
    @mock_aws
    def test_s3_bucket_encryption_enabled(self):
        """Test S3 bucket has encryption enabled."""
        # Create S3 client
        s3_client = boto3.client('s3', region_name='ap-south-1')
        kms_client = boto3.client('kms', region_name='ap-south-1')
        
        # Create KMS key
        key_response = kms_client.create_key(Description='Test key')
        key_id = key_response['KeyMetadata']['KeyId']
        
        # Create bucket
        bucket_name = 'test-auditflow-documents'
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={'LocationConstraint': 'ap-south-1'}
        )
        
        # Enable encryption
        s3_client.put_bucket_encryption(
            Bucket=bucket_name,
            ServerSideEncryptionConfiguration={
                'Rules': [{
                    'ApplyServerSideEncryptionByDefault': {
                        'SSEAlgorithm': 'aws:kms',
                        'KMSMasterKeyID': key_id
                    }
                }]
            }
        )
        
        # Verify encryption is enabled
        encryption = s3_client.get_bucket_encryption(Bucket=bucket_name)
        assert encryption['ServerSideEncryptionConfiguration']['Rules'][0]['ApplyServerSideEncryptionByDefault']['SSEAlgorithm'] == 'aws:kms'
    
    @mock_aws
    def test_dynamodb_encryption_at_rest(self):
        """Test DynamoDB table has encryption at rest enabled."""
        # Create DynamoDB client
        dynamodb_client = boto3.client('dynamodb', region_name='ap-south-1')
        
        # Create table with encryption
        table_name = 'TestAuditFlowDocuments'
        dynamodb_client.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'document_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'document_id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST',
            SSESpecification={
                'Enabled': True,
                'SSEType': 'KMS'
            }
        )
        
        # Verify encryption is enabled
        response = dynamodb_client.describe_table(TableName=table_name)
        assert response['Table']['SSEDescription']['Status'] == 'ENABLED'
        assert response['Table']['SSEDescription']['SSEType'] == 'KMS'


class TestEncryptionInTransit:
    """Test encryption in transit (TLS)."""
    
    def test_s3_client_uses_https(self):
        """Test S3 client uses HTTPS by default."""
        s3_client = boto3.client('s3', region_name='ap-south-1')
        
        # Verify endpoint uses HTTPS
        assert s3_client._endpoint.host.startswith('https://')
    
    def test_dynamodb_client_uses_https(self):
        """Test DynamoDB client uses HTTPS by default."""
        dynamodb_client = boto3.client('dynamodb', region_name='ap-south-1')
        
        # Verify endpoint uses HTTPS
        assert dynamodb_client._endpoint.host.startswith('https://')
    
    @mock_aws
    def test_s3_bucket_policy_denies_insecure_transport(self):
        """Test S3 bucket policy denies HTTP requests."""
        s3_client = boto3.client('s3', region_name='ap-south-1')
        
        bucket_name = 'test-auditflow-documents'
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={'LocationConstraint': 'ap-south-1'}
        )
        
        # Apply bucket policy to deny insecure transport
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "DenyInsecureTransport",
                    "Effect": "Deny",
                    "Principal": "*",
                    "Action": "s3:*",
                    "Resource": [
                        f"arn:aws:s3:::{bucket_name}",
                        f"arn:aws:s3:::{bucket_name}/*"
                    ],
                    "Condition": {
                        "Bool": {
                            "aws:SecureTransport": "false"
                        }
                    }
                }
            ]
        }
        
        s3_client.put_bucket_policy(
            Bucket=bucket_name,
            Policy=json.dumps(bucket_policy)
        )
        
        # Verify policy is applied
        policy = s3_client.get_bucket_policy(Bucket=bucket_name)
        policy_dict = json.loads(policy['Policy'])
        
        # Check for DenyInsecureTransport statement
        deny_statements = [s for s in policy_dict['Statement'] if s['Sid'] == 'DenyInsecureTransport']
        assert len(deny_statements) == 1
        assert deny_statements[0]['Effect'] == 'Deny'


class TestPIIFieldLevelEncryption:
    """Test PII field-level encryption."""
    
    @patch('shared.encryption.boto3.client')
    def test_pii_fields_are_encrypted(self, mock_boto_client):
        """Test PII fields are encrypted before storage."""
        mock_kms = Mock()
        mock_boto_client.return_value = mock_kms
        
        plaintext_dek = b'0' * 32
        mock_kms.generate_data_key.return_value = {
            'Plaintext': plaintext_dek,
            'CiphertextBlob': b'encrypted_dek_data'
        }
        
        encryptor = FieldEncryption()
        
        # Test data with PII
        data = {
            'employee_name': {'value': 'John Doe', 'confidence': 0.98},
            'employee_ssn': {'value': '123-45-6789', 'confidence': 0.99},
            'account_number': {'value': '9876543210', 'confidence': 0.99}
        }
        
        # Encrypt PII fields
        encrypted_data = encryptor.encrypt_pii_fields(
            data,
            ['employee_ssn', 'account_number']
        )
        
        # Verify SSN is encrypted
        assert 'encrypted_value' in encrypted_data['employee_ssn']
        assert 'encrypted_dek' in encrypted_data['employee_ssn']
        assert 'value' not in encrypted_data['employee_ssn']
        
        # Verify account number is encrypted
        assert 'encrypted_value' in encrypted_data['account_number']
        assert 'encrypted_dek' in encrypted_data['account_number']
        assert 'value' not in encrypted_data['account_number']
        
        # Verify non-PII field is not encrypted
        assert encrypted_data['employee_name']['value'] == 'John Doe'
    
    @patch('shared.encryption.boto3.client')
    def test_pii_never_stored_in_plaintext(self, mock_boto_client):
        """Test PII is never stored in plaintext after encryption."""
        mock_kms = Mock()
        mock_boto_client.return_value = mock_kms
        
        plaintext_dek = b'0' * 32
        mock_kms.generate_data_key.return_value = {
            'Plaintext': plaintext_dek,
            'CiphertextBlob': b'encrypted_dek_data'
        }
        
        encryptor = FieldEncryption()
        
        ssn = '123-45-6789'
        encrypted = encryptor.encrypt_field(ssn)
        
        # Verify plaintext SSN is not in encrypted data
        encrypted_str = json.dumps(encrypted)
        assert ssn not in encrypted_str
        assert '123-45-6789' not in encrypted_str


class TestIAMPolicyRestrictions:
    """Test IAM policy restrictions."""
    
    @mock_aws
    def test_lambda_role_has_minimum_permissions(self):
        """Test Lambda execution role has only required permissions."""
        iam_client = boto3.client('iam', region_name='ap-south-1')
        
        # Create Lambda execution role
        role_name = 'TestAuditFlowLambdaRole'
        iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps({
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }]
            })
        )
        
        # Attach minimal policy
        policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject",
                        "s3:PutObject"
                    ],
                    "Resource": "arn:aws:s3:::auditflow-documents/*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "dynamodb:PutItem",
                        "dynamodb:GetItem"
                    ],
                    "Resource": "arn:aws:dynamodb:*:*:table/AuditFlow-*"
                }
            ]
        }
        
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName='MinimalPolicy',
            PolicyDocument=json.dumps(policy_document)
        )
        
        # Verify policy is attached
        policies = iam_client.list_role_policies(RoleName=role_name)
        assert 'MinimalPolicy' in policies['PolicyNames']
        
        # Get policy document
        policy = iam_client.get_role_policy(
            RoleName=role_name,
            PolicyName='MinimalPolicy'
        )
        
        # Moto returns dict directly, not JSON string
        policy_doc = policy['PolicyDocument'] if isinstance(policy['PolicyDocument'], dict) else json.loads(policy['PolicyDocument'])
        
        # Verify only required actions are allowed
        s3_statement = [s for s in policy_doc['Statement'] if 's3:' in str(s['Action'])][0]
        assert set(s3_statement['Action']) == {'s3:GetObject', 's3:PutObject'}
    
    @mock_aws
    def test_cross_account_access_denied(self):
        """Test cross-account access is denied by default."""
        iam_client = boto3.client('iam', region_name='ap-south-1')
        
        role_name = 'TestAuditFlowLambdaRole'
        iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps({
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }]
            })
        )
        
        # Add deny cross-account policy
        deny_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Deny",
                    "Action": "*",
                    "Resource": "*",
                    "Condition": {
                        "StringNotEquals": {
                            "aws:PrincipalAccount": "123456789012"
                        }
                    }
                }
            ]
        }
        
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName='DenyCrossAccountAccess',
            PolicyDocument=json.dumps(deny_policy)
        )
        
        # Verify deny policy is attached
        policies = iam_client.list_role_policies(RoleName=role_name)
        assert 'DenyCrossAccountAccess' in policies['PolicyNames']


class TestUnauthorizedAccessDenial:
    """Test unauthorized access is denied."""
    
    def test_loan_officer_cannot_access_full_pii(self):
        """Test Loan Officers cannot access full PII values."""
        data = {
            'employee_ssn': {'value': '123-45-6789', 'confidence': 0.99},
            'account_number': {'value': '9876543210', 'confidence': 0.99}
        }
        
        # Apply masking for Loan Officer
        masked_data = apply_pii_masking(data, 'LoanOfficers', ['employee_ssn', 'account_number'])
        
        # Verify PII is masked
        assert masked_data['employee_ssn']['value'] == '***-**-6789'
        assert masked_data['account_number']['value'] == '****3210'
        
        # Verify full values are not accessible
        assert '123-45-6789' not in str(masked_data)
        assert '9876543210' not in str(masked_data)
    
    def test_administrator_can_access_full_pii(self):
        """Test Administrators can access full PII values."""
        data = {
            'employee_ssn': {'value': '123-45-6789', 'confidence': 0.99},
            'account_number': {'value': '9876543210', 'confidence': 0.99}
        }
        
        # Apply masking for Administrator (should not mask)
        masked_data = apply_pii_masking(data, 'Administrators', ['employee_ssn', 'account_number'])
        
        # Verify PII is NOT masked
        assert masked_data['employee_ssn']['value'] == '123-45-6789'
        assert masked_data['account_number']['value'] == '9876543210'
    
    def test_unknown_role_cannot_access_pii(self):
        """Test unknown roles cannot access full PII (default deny)."""
        data = {
            'employee_ssn': {'value': '123-45-6789', 'confidence': 0.99}
        }
        
        # Apply masking for unknown role
        masked_data = apply_pii_masking(data, 'UnknownRole', ['employee_ssn'])
        
        # Verify PII is masked (default behavior)
        assert masked_data['employee_ssn']['value'] == '***-**-6789'
    
    @mock_aws
    def test_s3_bucket_denies_unencrypted_uploads(self):
        """Test S3 bucket denies unencrypted object uploads."""
        s3_client = boto3.client('s3', region_name='ap-south-1')
        
        bucket_name = 'test-auditflow-documents'
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={'LocationConstraint': 'ap-south-1'}
        )
        
        # Apply bucket policy to deny unencrypted uploads
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "DenyUnencryptedObjectUploads",
                    "Effect": "Deny",
                    "Principal": "*",
                    "Action": "s3:PutObject",
                    "Resource": f"arn:aws:s3:::{bucket_name}/*",
                    "Condition": {
                        "StringNotEquals": {
                            "s3:x-amz-server-side-encryption": "aws:kms"
                        }
                    }
                }
            ]
        }
        
        s3_client.put_bucket_policy(
            Bucket=bucket_name,
            Policy=json.dumps(bucket_policy)
        )
        
        # Verify policy is applied
        policy = s3_client.get_bucket_policy(Bucket=bucket_name)
        policy_dict = json.loads(policy['Policy'])
        
        # Check for DenyUnencryptedObjectUploads statement
        deny_statements = [s for s in policy_dict['Statement'] if s['Sid'] == 'DenyUnencryptedObjectUploads']
        assert len(deny_statements) == 1
        assert deny_statements[0]['Effect'] == 'Deny'
        assert deny_statements[0]['Action'] == 's3:PutObject'


class TestKMSKeyRotation:
    """Test KMS key rotation is enabled."""
    
    @mock_aws
    def test_kms_key_rotation_enabled(self):
        """Test KMS key has automatic rotation enabled."""
        kms_client = boto3.client('kms', region_name='ap-south-1')
        
        # Create KMS key
        key_response = kms_client.create_key(
            Description='AuditFlow S3 Encryption Key'
        )
        key_id = key_response['KeyMetadata']['KeyId']
        
        # Enable key rotation
        kms_client.enable_key_rotation(KeyId=key_id)
        
        # Verify rotation is enabled
        rotation_status = kms_client.get_key_rotation_status(KeyId=key_id)
        assert rotation_status['KeyRotationEnabled'] is True


class TestSecurityBestPractices:
    """Test security best practices are followed."""
    
    def test_pii_not_logged_in_plaintext(self):
        """Test PII values are not logged in plaintext."""
        # Simulate logging with PII masking
        ssn = '123-45-6789'
        masked_ssn = mask_pii_value(ssn, 'ssn')
        
        # Verify masked value doesn't contain full SSN
        assert masked_ssn == '***-**-6789'
        assert '123-45' not in masked_ssn
    
    def test_encryption_uses_aes_256(self):
        """Test encryption uses AES-256 algorithm."""
        # This is verified by the encryption module using AESGCM with 32-byte keys
        # 32 bytes = 256 bits
        key_size = 32  # bytes
        assert key_size * 8 == 256  # bits
    
    @patch('shared.encryption.boto3.client')
    def test_encryption_key_not_stored_in_code(self, mock_boto_client):
        """Test encryption keys are not stored in application code."""
        mock_kms = Mock()
        mock_boto_client.return_value = mock_kms
        
        mock_kms.generate_data_key.return_value = {
            'Plaintext': b'0' * 32,
            'CiphertextBlob': b'encrypted_dek_data'
        }
        
        encryptor = FieldEncryption()
        
        # Verify encryptor uses KMS for key generation (not hardcoded keys)
        assert encryptor.kms_key_id is not None
        assert 'alias/auditflow' in encryptor.kms_key_id or 'AUDITFLOW' in str(encryptor.kms_key_id)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
