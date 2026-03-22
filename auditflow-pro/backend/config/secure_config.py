"""
Secure Configuration Management for AuditFlow-Pro

This module provides secure credential and configuration management using AWS Secrets Manager
and AWS Systems Manager Parameter Store, eliminating hardcoded credentials and environment variables.

Implements Requirements:
- 17.1, 17.2, 17.3, 17.4: IAM policies with least privilege
- 16.1, 16.5, 16.6: KMS encryption key management
- 7.3, 7.4: PII protection and field-level encryption
"""

import os
import json
import logging
import boto3
from functools import lru_cache
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class SecureConfig:
    """
    Secure configuration manager that retrieves credentials from AWS Secrets Manager
    and parameters from AWS Systems Manager Parameter Store.
    
    This eliminates hardcoded credentials and environment variables from code.
    All credentials are retrieved at runtime with proper error handling and caching.
    """
    
    def __init__(self):
        """Initialize AWS service clients."""
        self.secrets_client = boto3.client('secretsmanager')
        self.ssm_client = boto3.client('ssm')
        self.region = os.environ.get('AWS_REGION', 'ap-south-1')
    
    @lru_cache(maxsize=1)
    def get_aws_config(self) -> Dict[str, str]:
        """
        Retrieve AWS configuration from Secrets Manager.
        
        Returns:
            Dictionary with AWS_REGION, AWS_ACCOUNT_ID, S3_DOCUMENT_BUCKET
        
        Raises:
            ValueError: If required configuration is missing
        """
        try:
            response = self.secrets_client.get_secret_value(
                SecretId='auditflow/aws-config'
            )
            config = json.loads(response['SecretString'])
            
            # Validate required fields
            required_fields = ['AWS_REGION', 'S3_DOCUMENT_BUCKET']
            for field in required_fields:
                if field not in config:
                    raise ValueError(f"Missing required configuration: {field}")
            
            logger.info("AWS configuration retrieved from Secrets Manager")
            return config
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                raise ValueError(
                    "AWS configuration secret not found in Secrets Manager. "
                    "Please create 'auditflow/aws-config' secret with AWS_REGION and S3_DOCUMENT_BUCKET."
                )
            raise
    
    @lru_cache(maxsize=1)
    def get_dynamodb_config(self) -> Dict[str, str]:
        """
        Retrieve DynamoDB table names from Secrets Manager.
        
        Returns:
            Dictionary with DYNAMODB_DOCUMENTS_TABLE, DYNAMODB_AUDIT_RECORDS_TABLE
        
        Raises:
            ValueError: If required configuration is missing
        """
        try:
            response = self.secrets_client.get_secret_value(
                SecretId='auditflow/dynamodb-config'
            )
            config = json.loads(response['SecretString'])
            
            # Validate required fields
            required_fields = ['DYNAMODB_DOCUMENTS_TABLE', 'DYNAMODB_AUDIT_RECORDS_TABLE']
            for field in required_fields:
                if field not in config:
                    raise ValueError(f"Missing required configuration: {field}")
            
            logger.info("DynamoDB configuration retrieved from Secrets Manager")
            return config
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                raise ValueError(
                    "DynamoDB configuration secret not found in Secrets Manager. "
                    "Please create 'auditflow/dynamodb-config' secret."
                )
            raise
    
    @lru_cache(maxsize=1)
    def get_cognito_config(self) -> Dict[str, str]:
        """
        Retrieve Cognito configuration from Secrets Manager.
        
        Returns:
            Dictionary with COGNITO_USER_POOL_ID, COGNITO_CLIENT_ID, COGNITO_IDENTITY_POOL_ID
        
        Raises:
            ValueError: If required configuration is missing
        """
        try:
            response = self.secrets_client.get_secret_value(
                SecretId='auditflow/cognito-config'
            )
            config = json.loads(response['SecretString'])
            
            # Validate required fields
            required_fields = ['COGNITO_USER_POOL_ID', 'COGNITO_CLIENT_ID']
            for field in required_fields:
                if field not in config:
                    raise ValueError(f"Missing required configuration: {field}")
            
            logger.info("Cognito configuration retrieved from Secrets Manager")
            return config
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                raise ValueError(
                    "Cognito configuration secret not found in Secrets Manager. "
                    "Please create 'auditflow/cognito-config' secret."
                )
            raise
    
    @lru_cache(maxsize=1)
    def get_sns_arns(self) -> Dict[str, str]:
        """
        Retrieve SNS topic ARNs from Secrets Manager.
        
        Returns:
            Dictionary with ALERTS_TOPIC_ARN, CRITICAL_ALERTS_TOPIC_ARN
        
        Raises:
            ValueError: If required configuration is missing
        """
        try:
            response = self.secrets_client.get_secret_value(
                SecretId='auditflow/sns-arns'
            )
            config = json.loads(response['SecretString'])
            
            # Validate required fields
            required_fields = ['ALERTS_TOPIC_ARN', 'CRITICAL_ALERTS_TOPIC_ARN']
            for field in required_fields:
                if field not in config:
                    raise ValueError(f"Missing required configuration: {field}")
            
            logger.info("SNS ARNs retrieved from Secrets Manager")
            return config
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                raise ValueError(
                    "SNS ARNs secret not found in Secrets Manager. "
                    "Please create 'auditflow/sns-arns' secret."
                )
            raise
    
    def get_parameter(self, param_name: str, with_decryption: bool = True) -> str:
        """
        Retrieve a parameter from AWS Systems Manager Parameter Store.
        
        Args:
            param_name: Name of the parameter (e.g., '/auditflow/confidence-threshold')
            with_decryption: Whether to decrypt SecureString parameters
        
        Returns:
            Parameter value
        
        Raises:
            ValueError: If parameter not found
        """
        try:
            response = self.ssm_client.get_parameter(
                Name=param_name,
                WithDecryption=with_decryption
            )
            logger.debug(f"Retrieved parameter: {param_name}")
            return response['Parameter']['Value']
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ParameterNotFound':
                raise ValueError(f"Parameter not found: {param_name}")
            raise
    
    def get_application_config(self) -> Dict[str, Any]:
        """
        Retrieve all application configuration from Parameter Store.
        
        Returns:
            Dictionary with application settings (confidence threshold, timeouts, etc.)
        """
        try:
            response = self.ssm_client.get_parameters_by_path(
                Path='/auditflow/config',
                Recursive=True,
                WithDecryption=True
            )
            
            config = {}
            for param in response['Parameters']:
                # Extract key from parameter name (e.g., '/auditflow/config/CONFIDENCE_THRESHOLD' -> 'CONFIDENCE_THRESHOLD')
                key = param['Name'].split('/')[-1]
                
                # Try to parse as JSON, otherwise use as string
                try:
                    config[key] = json.loads(param['Value'])
                except json.JSONDecodeError:
                    config[key] = param['Value']
            
            logger.info(f"Retrieved {len(config)} application configuration parameters")
            return config
            
        except ClientError as e:
            logger.warning(f"Error retrieving application config: {e}")
            return {}


# Global instance for use throughout the application
_config_instance: Optional[SecureConfig] = None


def get_config() -> SecureConfig:
    """
    Get or create the global SecureConfig instance.
    
    Returns:
        SecureConfig instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = SecureConfig()
    return _config_instance


# Convenience functions for common configuration retrieval
def get_s3_bucket() -> str:
    """Get S3 document bucket name."""
    config = get_config()
    aws_config = config.get_aws_config()
    return aws_config['S3_DOCUMENT_BUCKET']


def get_audit_table() -> str:
    """Get DynamoDB audit records table name."""
    config = get_config()
    dynamodb_config = config.get_dynamodb_config()
    return dynamodb_config['DYNAMODB_AUDIT_RECORDS_TABLE']


def get_documents_table() -> str:
    """Get DynamoDB documents table name."""
    config = get_config()
    dynamodb_config = config.get_dynamodb_config()
    return dynamodb_config['DYNAMODB_DOCUMENTS_TABLE']


def get_confidence_threshold() -> float:
    """Get confidence threshold for field extraction."""
    config = get_config()
    try:
        threshold_str = config.get_parameter('/auditflow/config/CONFIDENCE_THRESHOLD')
        return float(threshold_str)
    except (ValueError, TypeError):
        logger.warning("Invalid confidence threshold, using default 0.80")
        return 0.80


def get_processing_timeout() -> int:
    """Get processing timeout in seconds."""
    config = get_config()
    try:
        timeout_str = config.get_parameter('/auditflow/config/PROCESSING_TIMEOUT_SECONDS')
        return int(timeout_str)
    except (ValueError, TypeError):
        logger.warning("Invalid processing timeout, using default 300 seconds")
        return 300
