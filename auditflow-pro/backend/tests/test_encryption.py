# -*- coding: utf-8 -*-
"""
Unit tests for field-level encryption utilities.

Tests encryption/decryption, PII masking, and role-based access control.
"""

import pytest
import base64
from unittest.mock import Mock, patch, MagicMock
from shared.encryption import (
    FieldEncryption,
    mask_pii_value,
    should_mask_pii_for_role,
    apply_pii_masking,
    PII_FIELDS
)


class TestFieldEncryption:
    """Test field-level encryption and decryption."""
    
    @patch('shared.encryption.boto3.client')
    def test_encrypt_field_success(self, mock_boto_client):
        """Test successful field encryption."""
        # Mock KMS client
        mock_kms = Mock()
        mock_boto_client.return_value = mock_kms
        
        # Mock generate_data_key response
        mock_kms.generate_data_key.return_value = {
            'Plaintext': b'0' * 32,  # 256-bit key
            'CiphertextBlob': b'encrypted_dek_data'
        }
        
        encryptor = FieldEncryption()
        result = encryptor.encrypt_field("123-45-6789")
        
        # Verify result structure
        assert 'encrypted_value' in result
        assert 'encrypted_dek' in result
        assert 'encryption_key_id' in result
        assert 'encryption_algorithm' in result
        assert result['encryption_algorithm'] == 'AES-256-GCM'
        
        # Verify KMS was called
        mock_kms.generate_data_key.assert_called_once()
    
    @patch('shared.encryption.boto3.client')
    def test_encrypt_field_empty_value(self, mock_boto_client):
        """Test encryption fails with empty value."""
        mock_kms = Mock()
        mock_boto_client.return_value = mock_kms
        
        encryptor = FieldEncryption()
        
        with pytest.raises(ValueError, match="Cannot encrypt empty value"):
            encryptor.encrypt_field("")
    
    @patch('shared.encryption.boto3.client')
    def test_decrypt_field_success(self, mock_boto_client):
        """Test successful field decryption."""
        # Mock KMS client
        mock_kms = Mock()
        mock_boto_client.return_value = mock_kms
        
        # Create a real encryption/decryption cycle
        plaintext_dek = b'0' * 32
        
        # Mock generate_data_key for encryption
        mock_kms.generate_data_key.return_value = {
            'Plaintext': plaintext_dek,
            'CiphertextBlob': b'encrypted_dek_data'
        }
        
        # Mock decrypt for decryption
        mock_kms.decrypt.return_value = {
            'Plaintext': plaintext_dek
        }
        
        encryptor = FieldEncryption()
        
        # Encrypt
        original_value = "123-45-6789"
        encrypted = encryptor.encrypt_field(original_value)
        
        # Decrypt
        decrypted = encryptor.decrypt_field(encrypted)
        
        # Verify round-trip
        assert decrypted == original_value
    
    @patch('shared.encryption.boto3.client')
    def test_decrypt_field_invalid_data(self, mock_boto_client):
        """Test decryption fails with invalid data."""
        mock_kms = Mock()
        mock_boto_client.return_value = mock_kms
        
        encryptor = FieldEncryption()
        
        with pytest.raises(ValueError, match="Invalid encrypted field data"):
            encryptor.decrypt_field({})
        
        with pytest.raises(ValueError, match="Invalid encrypted field data"):
            encryptor.decrypt_field({'encrypted_value': 'test'})
    
    @patch('shared.encryption.boto3.client')
    def test_encrypt_pii_fields_nested_structure(self, mock_boto_client):
        """Test encrypting PII fields in nested structure."""
        mock_kms = Mock()
        mock_boto_client.return_value = mock_kms
        
        mock_kms.generate_data_key.return_value = {
            'Plaintext': b'0' * 32,
            'CiphertextBlob': b'encrypted_dek_data'
        }
        
        encryptor = FieldEncryption()
        
        data = {
            'employee_name': {'value': 'John Doe', 'confidence': 0.98},
            'employee_ssn': {'value': '123-45-6789', 'confidence': 0.99},
            'wages': {'value': 75000.00, 'confidence': 0.99}
        }
        
        encrypted_data = encryptor.encrypt_pii_fields(data, ['employee_ssn'])
        
        # Verify SSN is encrypted
        assert 'encrypted_value' in encrypted_data['employee_ssn']
        assert 'encrypted_dek' in encrypted_data['employee_ssn']
        assert 'value' not in encrypted_data['employee_ssn']
        assert encrypted_data['employee_ssn']['pii_encrypted'] is True
        
        # Verify other fields unchanged
        assert encrypted_data['employee_name']['value'] == 'John Doe'
        assert encrypted_data['wages']['value'] == 75000.00
    
    @patch('shared.encryption.boto3.client')
    def test_decrypt_pii_fields_nested_structure(self, mock_boto_client):
        """Test decrypting PII fields in nested structure."""
        mock_kms = Mock()
        mock_boto_client.return_value = mock_kms
        
        plaintext_dek = b'0' * 32
        
        mock_kms.generate_data_key.return_value = {
            'Plaintext': plaintext_dek,
            'CiphertextBlob': b'encrypted_dek_data'
        }
        
        mock_kms.decrypt.return_value = {
            'Plaintext': plaintext_dek
        }
        
        encryptor = FieldEncryption()
        
        original_data = {
            'employee_name': {'value': 'John Doe', 'confidence': 0.98},
            'employee_ssn': {'value': '123-45-6789', 'confidence': 0.99}
        }
        
        # Encrypt
        encrypted_data = encryptor.encrypt_pii_fields(original_data, ['employee_ssn'])
        
        # Decrypt
        decrypted_data = encryptor.decrypt_pii_fields(encrypted_data, ['employee_ssn'])
        
        # Verify round-trip
        assert decrypted_data['employee_ssn']['value'] == '123-45-6789'
        assert 'encrypted_value' not in decrypted_data['employee_ssn']
        assert 'encrypted_dek' not in decrypted_data['employee_ssn']


class TestPIIMasking:
    """Test PII masking functions."""
    
    def test_mask_ssn(self):
        """Test SSN masking shows last 4 digits."""
        assert mask_pii_value("123-45-6789", "ssn") == "***-**-6789"
        assert mask_pii_value("123456789", "employee_ssn") == "***-**-6789"
        assert mask_pii_value("123", "taxpayer_ssn") == "***-**-****"
    
    def test_mask_account_number(self):
        """Test account number masking shows last 4 digits."""
        assert mask_pii_value("1234567890", "account_number") == "****7890"
        assert mask_pii_value("9876543210", "bank_account_number") == "****3210"
        assert mask_pii_value("123", "account_number") == "****"
    
    def test_mask_license_number(self):
        """Test license number masking shows last 4 characters."""
        assert mask_pii_value("D123-4567-8901", "license_number") == "****8901"
        assert mask_pii_value("ABC123", "drivers_license_number") == "****C123"
    
    def test_mask_date_of_birth(self):
        """Test date of birth is fully masked."""
        assert mask_pii_value("1985-06-15", "date_of_birth") == "****-**-**"
        assert mask_pii_value("06/15/1985", "dob") == "****-**-**"
    
    def test_mask_empty_value(self):
        """Test masking empty value returns empty."""
        assert mask_pii_value("", "ssn") == ""
        assert mask_pii_value(None, "account_number") is None
    
    def test_should_mask_pii_for_loan_officer(self):
        """Test PII is masked for Loan Officers."""
        assert should_mask_pii_for_role("LoanOfficers") is True
        assert should_mask_pii_for_role("LoanOfficer") is True
    
    def test_should_not_mask_pii_for_administrator(self):
        """Test PII is not masked for Administrators."""
        assert should_mask_pii_for_role("Administrators") is False
        assert should_mask_pii_for_role("Administrator") is False
    
    def test_should_mask_pii_for_unknown_role(self):
        """Test PII is masked for unknown roles (default)."""
        assert should_mask_pii_for_role("UnknownRole") is True
        assert should_mask_pii_for_role("") is True
    
    def test_apply_pii_masking_for_loan_officer(self):
        """Test PII masking is applied for Loan Officers."""
        data = {
            'employee_name': {'value': 'John Doe', 'confidence': 0.98},
            'employee_ssn': {'value': '123-45-6789', 'confidence': 0.99},
            'wages': {'value': 75000.00, 'confidence': 0.99}
        }
        
        masked_data = apply_pii_masking(data, 'LoanOfficers', ['employee_ssn'])
        
        # Verify SSN is masked
        assert masked_data['employee_ssn']['value'] == '***-**-6789'
        
        # Verify other fields unchanged
        assert masked_data['employee_name']['value'] == 'John Doe'
        assert masked_data['wages']['value'] == 75000.00
    
    def test_apply_pii_masking_for_administrator(self):
        """Test PII masking is NOT applied for Administrators."""
        data = {
            'employee_name': {'value': 'John Doe', 'confidence': 0.98},
            'employee_ssn': {'value': '123-45-6789', 'confidence': 0.99}
        }
        
        masked_data = apply_pii_masking(data, 'Administrators', ['employee_ssn'])
        
        # Verify SSN is NOT masked
        assert masked_data['employee_ssn']['value'] == '123-45-6789'
    
    def test_apply_pii_masking_simple_string(self):
        """Test PII masking works with simple string values."""
        data = {
            'name': 'John Doe',
            'ssn': '123-45-6789',
            'income': 75000
        }
        
        masked_data = apply_pii_masking(data, 'LoanOfficers', ['ssn'])
        
        # Verify SSN is masked
        assert masked_data['ssn'] == '***-**-6789'
        
        # Verify other fields unchanged
        assert masked_data['name'] == 'John Doe'
        assert masked_data['income'] == 75000


class TestEncryptionRoundTrip:
    """Test encryption/decryption round-trip properties."""
    
    @patch('shared.encryption.boto3.client')
    def test_round_trip_preserves_data(self, mock_boto_client):
        """Property: decrypt(encrypt(data)) == data"""
        mock_kms = Mock()
        mock_boto_client.return_value = mock_kms
        
        plaintext_dek = b'0' * 32
        
        mock_kms.generate_data_key.return_value = {
            'Plaintext': plaintext_dek,
            'CiphertextBlob': b'encrypted_dek_data'
        }
        
        mock_kms.decrypt.return_value = {
            'Plaintext': plaintext_dek
        }
        
        encryptor = FieldEncryption()
        
        # Test with various values
        test_values = [
            "123-45-6789",
            "simple_text",
            "special!@#$%^&*()chars",
            "unicode_测试_тест",
            "1234567890" * 10  # Long value
        ]
        
        for original_value in test_values:
            encrypted = encryptor.encrypt_field(original_value)
            decrypted = encryptor.decrypt_field(encrypted)
            assert decrypted == original_value, f"Round-trip failed for: {original_value}"
    
    @patch('shared.encryption.boto3.client')
    def test_round_trip_with_pii_fields(self, mock_boto_client):
        """Property: decrypt_pii_fields(encrypt_pii_fields(data)) == data"""
        mock_kms = Mock()
        mock_boto_client.return_value = mock_kms
        
        plaintext_dek = b'0' * 32
        
        mock_kms.generate_data_key.return_value = {
            'Plaintext': plaintext_dek,
            'CiphertextBlob': b'encrypted_dek_data'
        }
        
        mock_kms.decrypt.return_value = {
            'Plaintext': plaintext_dek
        }
        
        encryptor = FieldEncryption()
        
        original_data = {
            'employee_name': {'value': 'John Doe', 'confidence': 0.98},
            'employee_ssn': {'value': '123-45-6789', 'confidence': 0.99},
            'account_number': {'value': '9876543210', 'confidence': 0.99},
            'date_of_birth': {'value': '1985-06-15', 'confidence': 0.99}
        }
        
        pii_fields = ['employee_ssn', 'account_number', 'date_of_birth']
        
        # Encrypt
        encrypted_data = encryptor.encrypt_pii_fields(original_data, pii_fields)
        
        # Decrypt
        decrypted_data = encryptor.decrypt_pii_fields(encrypted_data, pii_fields)
        
        # Verify all PII fields match original
        for field in pii_fields:
            assert decrypted_data[field]['value'] == original_data[field]['value']
        
        # Verify non-PII fields unchanged
        assert decrypted_data['employee_name']['value'] == original_data['employee_name']['value']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
