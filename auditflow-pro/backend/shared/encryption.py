"""
Field-level encryption utilities for PII data.

This module provides encryption and decryption functions for sensitive PII fields
using AWS KMS with envelope encryption (AES-256-GCM).

Requirements:
- 7.4: Encrypt all PII fields in DynamoDB using field-level encryption
- 16.1: Encrypt all data at rest using KMS with AES-256 encryption
"""

import base64
import json
import os
from typing import Any, Dict, Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend
import boto3
from botocore.exceptions import ClientError


class FieldEncryption:
    """
    Handles field-level encryption and decryption for PII data using AWS KMS.
    
    Uses envelope encryption:
    1. Generate data encryption key (DEK) using KMS
    2. Encrypt field value with DEK using AES-256-GCM
    3. Encrypt DEK with KMS CMK
    4. Store encrypted value + encrypted DEK
    """
    
    def __init__(self, kms_key_id: Optional[str] = None, region: str = 'ap-south-1'):
        """
        Initialize field encryption with KMS key.
        
        Args:
            kms_key_id: KMS key ID or alias (defaults to alias/auditflow-dynamodb-encryption)
            region: AWS region
        """
        self.kms_client = boto3.client('kms', region_name=region)
        self.kms_key_id = kms_key_id or os.environ.get(
            'AUDITFLOW_DYNAMODB_KMS_KEY_ID',
            'alias/auditflow-dynamodb-encryption'
        )
        self.region = region
    
    def encrypt_field(self, plaintext_value: str) -> Dict[str, str]:
        """
        Encrypt a field value using envelope encryption.
        
        Args:
            plaintext_value: The plaintext value to encrypt
            
        Returns:
            Dictionary containing:
            - encrypted_value: Base64-encoded encrypted data
            - encrypted_dek: Base64-encoded encrypted data encryption key
            - encryption_key_id: KMS key ID used
            - encryption_algorithm: Algorithm used (AES-256-GCM)
            
        Raises:
            ClientError: If KMS operation fails
            ValueError: If plaintext_value is empty
        """
        if not plaintext_value:
            raise ValueError("Cannot encrypt empty value")
        
        try:
            # Generate data encryption key (DEK) using KMS
            response = self.kms_client.generate_data_key(
                KeyId=self.kms_key_id,
                KeySpec='AES_256'
            )
            
            # Extract plaintext DEK and encrypted DEK
            plaintext_dek = response['Plaintext']
            encrypted_dek = response['CiphertextBlob']
            
            # Encrypt the field value using AES-256-GCM with the DEK
            aesgcm = AESGCM(plaintext_dek)
            nonce = os.urandom(12)  # 96-bit nonce for GCM
            
            # Encrypt plaintext
            ciphertext = aesgcm.encrypt(
                nonce,
                plaintext_value.encode('utf-8'),
                None  # No additional authenticated data
            )
            
            # Combine nonce + ciphertext for storage
            encrypted_data = nonce + ciphertext
            
            # Return encrypted field data
            return {
                'encrypted_value': base64.b64encode(encrypted_data).decode('utf-8'),
                'encrypted_dek': base64.b64encode(encrypted_dek).decode('utf-8'),
                'encryption_key_id': self.kms_key_id,
                'encryption_algorithm': 'AES-256-GCM'
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            raise RuntimeError(f"KMS encryption failed: {error_code} - {error_msg}") from e
    
    def decrypt_field(self, encrypted_field: Dict[str, str]) -> str:
        """
        Decrypt a field value using envelope encryption.
        
        Args:
            encrypted_field: Dictionary containing encrypted_value and encrypted_dek
            
        Returns:
            Decrypted plaintext value
            
        Raises:
            ClientError: If KMS operation fails
            ValueError: If encrypted_field is invalid
        """
        if not encrypted_field or 'encrypted_value' not in encrypted_field or 'encrypted_dek' not in encrypted_field:
            raise ValueError("Invalid encrypted field data")
        
        try:
            # Decode base64-encoded data
            encrypted_data = base64.b64decode(encrypted_field['encrypted_value'])
            encrypted_dek = base64.b64decode(encrypted_field['encrypted_dek'])
            
            # Decrypt the DEK using KMS
            response = self.kms_client.decrypt(
                CiphertextBlob=encrypted_dek
            )
            plaintext_dek = response['Plaintext']
            
            # Extract nonce and ciphertext
            nonce = encrypted_data[:12]  # First 12 bytes are the nonce
            ciphertext = encrypted_data[12:]  # Rest is the ciphertext
            
            # Decrypt the field value using AES-256-GCM
            aesgcm = AESGCM(plaintext_dek)
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            
            return plaintext.decode('utf-8')
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            raise RuntimeError(f"KMS decryption failed: {error_code} - {error_msg}") from e
        except Exception as e:
            raise RuntimeError(f"Decryption failed: {str(e)}") from e
    
    def encrypt_pii_fields(self, data: Dict[str, Any], pii_field_names: list) -> Dict[str, Any]:
        """
        Encrypt specified PII fields in a data dictionary.
        
        Args:
            data: Dictionary containing field data
            pii_field_names: List of field names to encrypt
            
        Returns:
            Dictionary with PII fields encrypted
        """
        encrypted_data = data.copy()
        
        for field_name in pii_field_names:
            if field_name in encrypted_data and encrypted_data[field_name]:
                # Handle nested field structure (e.g., {"value": "...", "confidence": 0.99})
                if isinstance(encrypted_data[field_name], dict) and 'value' in encrypted_data[field_name]:
                    original_value = encrypted_data[field_name]['value']
                    if original_value and not self._is_already_encrypted(encrypted_data[field_name]):
                        encrypted_field = self.encrypt_field(original_value)
                        encrypted_data[field_name].update(encrypted_field)
                        # Remove plaintext value
                        del encrypted_data[field_name]['value']
                        encrypted_data[field_name]['pii_encrypted'] = True
                # Handle simple string values
                elif isinstance(encrypted_data[field_name], str):
                    encrypted_field = self.encrypt_field(encrypted_data[field_name])
                    encrypted_data[field_name] = encrypted_field
        
        return encrypted_data
    
    def decrypt_pii_fields(self, data: Dict[str, Any], pii_field_names: list) -> Dict[str, Any]:
        """
        Decrypt specified PII fields in a data dictionary.
        
        Args:
            data: Dictionary containing encrypted field data
            pii_field_names: List of field names to decrypt
            
        Returns:
            Dictionary with PII fields decrypted
        """
        decrypted_data = data.copy()
        
        for field_name in pii_field_names:
            if field_name in decrypted_data and decrypted_data[field_name]:
                # Handle nested field structure
                if isinstance(decrypted_data[field_name], dict):
                    if self._is_already_encrypted(decrypted_data[field_name]):
                        decrypted_value = self.decrypt_field(decrypted_data[field_name])
                        decrypted_data[field_name]['value'] = decrypted_value
                        # Remove encrypted fields
                        decrypted_data[field_name].pop('encrypted_value', None)
                        decrypted_data[field_name].pop('encrypted_dek', None)
                        decrypted_data[field_name].pop('encryption_key_id', None)
                        decrypted_data[field_name].pop('encryption_algorithm', None)
                        decrypted_data[field_name].pop('pii_encrypted', None)
                # Handle encrypted dict (not nested)
                elif isinstance(decrypted_data[field_name], dict) and 'encrypted_value' in decrypted_data[field_name]:
                    decrypted_data[field_name] = self.decrypt_field(decrypted_data[field_name])
        
        return decrypted_data
    
    def _is_already_encrypted(self, field_data: Dict[str, Any]) -> bool:
        """Check if field data is already encrypted."""
        return 'encrypted_value' in field_data and 'encrypted_dek' in field_data


# PII field names that require encryption
PII_FIELDS = [
    'ssn',
    'employee_ssn',
    'taxpayer_ssn',
    'account_number',
    'bank_account_number',
    'license_number',
    'drivers_license_number',
    'document_number',
    'passport_number',
    'credit_card_number',
    'date_of_birth',
    'dob'
]


def mask_pii_value(value: str, pii_type: str) -> str:
    """
    Mask PII value for display based on type.
    
    Args:
        value: The PII value to mask
        pii_type: Type of PII (ssn, account_number, etc.)
        
    Returns:
        Masked value
    """
    if not value:
        return value
    
    # SSN: Show last 4 digits (***-**-1234)
    if pii_type in ['ssn', 'employee_ssn', 'taxpayer_ssn']:
        if len(value) >= 4:
            return f"***-**-{value[-4:]}"
        return "***-**-****"
    
    # Account numbers: Show last 4 digits (****1234)
    if pii_type in ['account_number', 'bank_account_number', 'credit_card_number']:
        if len(value) >= 4:
            return f"****{value[-4:]}"
        return "****"
    
    # License numbers: Show last 4 characters
    if pii_type in ['license_number', 'drivers_license_number', 'document_number', 'passport_number']:
        if len(value) >= 4:
            return f"****{value[-4:]}"
        return "****"
    
    # Date of birth: Fully mask (****-**-**)
    if pii_type in ['date_of_birth', 'dob']:
        return "****-**-**"
    
    # Default: Mask all but last 4 characters
    if len(value) >= 4:
        return f"****{value[-4:]}"
    return "****"


def should_mask_pii_for_role(user_role: str) -> bool:
    """
    Determine if PII should be masked based on user role.
    
    Args:
        user_role: User's role (LoanOfficers or Administrators)
        
    Returns:
        True if PII should be masked, False otherwise
    """
    # Loan Officers see masked PII
    if 'LoanOfficers' in user_role or 'LoanOfficer' in user_role:
        return True
    
    # Administrators see full PII
    if 'Administrators' in user_role or 'Administrator' in user_role:
        return False
    
    # Default: mask PII for unknown roles
    return True


def apply_pii_masking(data: Dict[str, Any], user_role: str, pii_field_names: list = None) -> Dict[str, Any]:
    """
    Apply PII masking to data based on user role.
    
    Args:
        data: Dictionary containing field data
        user_role: User's role
        pii_field_names: List of PII field names (defaults to PII_FIELDS)
        
    Returns:
        Dictionary with PII fields masked if required
    """
    if not should_mask_pii_for_role(user_role):
        return data
    
    if pii_field_names is None:
        pii_field_names = PII_FIELDS
    
    masked_data = data.copy()
    
    for field_name in pii_field_names:
        if field_name in masked_data and masked_data[field_name]:
            # Handle nested field structure
            if isinstance(masked_data[field_name], dict) and 'value' in masked_data[field_name]:
                original_value = masked_data[field_name]['value']
                if original_value:
                    masked_data[field_name]['value'] = mask_pii_value(original_value, field_name)
            # Handle simple string values
            elif isinstance(masked_data[field_name], str):
                masked_data[field_name] = mask_pii_value(masked_data[field_name], field_name)
    
    return masked_data
