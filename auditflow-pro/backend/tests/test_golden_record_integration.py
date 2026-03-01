"""
Integration test for Golden Record generation (Task 8.7).
Demonstrates the complete Golden Record generation workflow.
"""

import os
import sys
import pytest
from unittest.mock import Mock, patch

# Add function path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../functions/validator'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../shared'))

from app import lambda_handler
from models import DocumentMetadata


class TestGoldenRecordIntegration:
    """Integration tests for Golden Record generation."""
    
    def test_complete_golden_record_workflow(self):
        """
        Test complete workflow: multiple documents -> validation -> Golden Record.
        
        This test demonstrates:
        1. Loading documents from multiple sources (W2, Tax Form, Driver's License, Bank Statement)
        2. Performing cross-document validation
        3. Generating Golden Record with reliability hierarchy
        4. Storing alternative values and verified_by references
        """
        # Arrange
        event = {
            'loan_application_id': 'loan-456',
            'document_ids': ['doc-w2', 'doc-tax', 'doc-license', 'doc-bank']
        }
        context = {}
        
        # Create comprehensive mock documents
        mock_w2 = DocumentMetadata(
            document_id='doc-w2',
            loan_application_id='loan-456',
            s3_bucket='test-bucket',
            s3_key='test/w2.pdf',
            upload_timestamp='2024-01-15T10:00:00Z',
            file_name='w2_2023.pdf',
            file_size_bytes=1024,
            file_format='PDF',
            checksum='abc123',
            document_type='W2',
            classification_confidence=0.95,
            processing_status='COMPLETED',
            extracted_data={
                'employee_name': {'value': 'John Doe', 'confidence': 0.98},
                'employee_ssn': {'value': '***-**-1234', 'confidence': 0.99},
                'employee_address': {'value': '123 Main St, Springfield, IL 62701', 'confidence': 0.95},
                'employer_name': {'value': 'Acme Corporation', 'confidence': 0.97},
                'employer_ein': {'value': '12-3456789', 'confidence': 0.98},
                'wages': {'value': 75000.00, 'confidence': 0.99}
            }
        )
        
        mock_tax = DocumentMetadata(
            document_id='doc-tax',
            loan_application_id='loan-456',
            s3_bucket='test-bucket',
            s3_key='test/tax.pdf',
            upload_timestamp='2024-01-15T10:05:00Z',
            file_name='1040_2023.pdf',
            file_size_bytes=2048,
            file_format='PDF',
            checksum='def456',
            document_type='TAX_FORM',
            classification_confidence=0.93,
            processing_status='COMPLETED',
            extracted_data={
                'taxpayer_name': {'value': 'John Doe', 'confidence': 0.97},
                'taxpayer_ssn': {'value': '***-**-1234', 'confidence': 0.99},
                'address': {'value': '123 Main St, Springfield, IL 62701', 'confidence': 0.96},
                'adjusted_gross_income': {'value': 75000.00, 'confidence': 0.98}
            }
        )
        
        mock_license = DocumentMetadata(
            document_id='doc-license',
            loan_application_id='loan-456',
            s3_bucket='test-bucket',
            s3_key='test/license.pdf',
            upload_timestamp='2024-01-15T10:10:00Z',
            file_name='drivers_license.pdf',
            file_size_bytes=3072,
            file_format='PDF',
            checksum='ghi789',
            document_type='DRIVERS_LICENSE',
            classification_confidence=0.98,
            processing_status='COMPLETED',
            extracted_data={
                'full_name': {'value': 'John Doe', 'confidence': 0.99},
                'date_of_birth': {'value': '1985-06-15', 'confidence': 0.99},
                'address': {'value': '123 Main St, Springfield, IL 62701', 'confidence': 0.98},
                'license_number': {'value': 'D123-4567-8901', 'confidence': 0.98},
                'state': {'value': 'IL', 'confidence': 0.99}
            }
        )
        
        mock_bank = DocumentMetadata(
            document_id='doc-bank',
            loan_application_id='loan-456',
            s3_bucket='test-bucket',
            s3_key='test/bank.pdf',
            upload_timestamp='2024-01-15T10:15:00Z',
            file_name='bank_statement.pdf',
            file_size_bytes=4096,
            file_format='PDF',
            checksum='jkl012',
            document_type='BANK_STATEMENT',
            classification_confidence=0.94,
            processing_status='COMPLETED',
            extracted_data={
                'account_holder_name': {'value': 'John Doe', 'confidence': 0.96},
                'account_number': {'value': '****1234', 'confidence': 0.99},
                'ending_balance': {'value': 6200.00, 'confidence': 0.98}
            }
        )
        
        # Mock DocumentRepository
        with patch('repositories.DocumentRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_document.side_effect = [mock_w2, mock_tax, mock_license, mock_bank]
            mock_repo_class.return_value = mock_repo
            
            # Act
            response = lambda_handler(event, context)
            
            # Assert - Basic response structure
            assert response['statusCode'] == 200
            assert response['loan_application_id'] == 'loan-456'
            assert len(response['documents']) == 4
            assert response['validation_status'] == 'VALIDATION_COMPLETE_WITH_GOLDEN_RECORD'
            
            # Assert - No inconsistencies (all data matches)
            assert len(response['inconsistencies']) == 0
            
            # Assert - Golden Record exists
            assert 'golden_record' in response
            golden_record = response['golden_record']
            
            # Assert - Golden Record metadata
            assert golden_record['loan_application_id'] == 'loan-456'
            assert 'created_timestamp' in golden_record
            
            # Assert - Name field (should come from DRIVERS_LICENSE - highest reliability)
            assert 'name' in golden_record
            assert golden_record['name']['value'] == 'John Doe'
            assert golden_record['name']['source_document'] == 'doc-license'
            assert golden_record['name']['confidence'] == 0.99
            # Other documents with same name should be in verified_by
            assert 'doc-w2' in golden_record['name']['verified_by']
            assert 'doc-tax' in golden_record['name']['verified_by']
            assert 'doc-bank' in golden_record['name']['verified_by']
            
            # Assert - Date of birth (only in DRIVERS_LICENSE)
            assert 'date_of_birth' in golden_record
            assert golden_record['date_of_birth']['value'] == '1985-06-15'
            assert golden_record['date_of_birth']['source_document'] == 'doc-license'
            
            # Assert - SSN (should come from TAX_FORM or W2, both have same reliability)
            assert 'ssn' in golden_record
            assert golden_record['ssn']['value'] == '***-**-1234'
            # Should be from either W2 or TAX_FORM (both have confidence 0.99)
            assert golden_record['ssn']['source_document'] in ['doc-w2', 'doc-tax']
            
            # Assert - Address (should come from DRIVERS_LICENSE - highest reliability)
            assert 'address' in golden_record
            assert golden_record['address']['value'] == '123 Main St, Springfield, IL 62701'
            assert golden_record['address']['source_document'] == 'doc-license'
            
            # Assert - Employer information (only in W2)
            assert 'employer' in golden_record
            assert golden_record['employer']['value'] == 'Acme Corporation'
            assert golden_record['employer']['source_document'] == 'doc-w2'
            
            assert 'employer_ein' in golden_record
            assert golden_record['employer_ein']['value'] == '12-3456789'
            
            # Assert - Annual income (should come from TAX_FORM - higher reliability than W2)
            assert 'annual_income' in golden_record
            assert golden_record['annual_income']['value'] == 75000.00
            assert golden_record['annual_income']['source_document'] == 'doc-tax'
            # W2 should verify this value
            assert 'doc-w2' in golden_record['annual_income']['verified_by']
            
            # Assert - Bank account information (only in BANK_STATEMENT)
            assert 'bank_account' in golden_record
            assert golden_record['bank_account']['value'] == '****1234'
            assert golden_record['bank_account']['source_document'] == 'doc-bank'
            
            assert 'ending_balance' in golden_record
            assert golden_record['ending_balance']['value'] == 6200.00
            
            # Assert - Driver's license information (only in DRIVERS_LICENSE)
            assert 'drivers_license_number' in golden_record
            assert golden_record['drivers_license_number']['value'] == 'D123-4567-8901'
            
            assert 'drivers_license_state' in golden_record
            assert golden_record['drivers_license_state']['value'] == 'IL'
    
    def test_golden_record_with_conflicting_values(self):
        """
        Test Golden Record generation when documents have conflicting values.
        
        This test demonstrates:
        1. Reliability hierarchy selection (Government ID > Tax Form > W2)
        2. Alternative values storage for conflicting data
        3. Proper source document tracking
        """
        # Arrange
        event = {
            'loan_application_id': 'loan-789',
            'document_ids': ['doc-w2', 'doc-license']
        }
        context = {}
        
        # Create documents with conflicting name values
        mock_w2 = DocumentMetadata(
            document_id='doc-w2',
            loan_application_id='loan-789',
            s3_bucket='test-bucket',
            s3_key='test/w2.pdf',
            upload_timestamp='2024-01-15T10:00:00Z',
            file_name='w2.pdf',
            file_size_bytes=1024,
            file_format='PDF',
            checksum='abc123',
            document_type='W2',
            classification_confidence=0.95,
            processing_status='COMPLETED',
            extracted_data={
                'employee_name': {'value': 'Jon Doe', 'confidence': 0.98},  # Slightly different
                'employee_address': {'value': '123 Main Street, Springfield, IL 62701', 'confidence': 0.95}
            }
        )
        
        mock_license = DocumentMetadata(
            document_id='doc-license',
            loan_application_id='loan-789',
            s3_bucket='test-bucket',
            s3_key='test/license.pdf',
            upload_timestamp='2024-01-15T10:05:00Z',
            file_name='license.pdf',
            file_size_bytes=2048,
            file_format='PDF',
            checksum='def456',
            document_type='DRIVERS_LICENSE',
            classification_confidence=0.98,
            processing_status='COMPLETED',
            extracted_data={
                'full_name': {'value': 'John Doe', 'confidence': 0.99},  # Correct spelling
                'address': {'value': '123 Main St, Springfield, IL 62701', 'confidence': 0.98}  # Abbreviated
            }
        )
        
        # Mock DocumentRepository
        with patch('repositories.DocumentRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_document.side_effect = [mock_w2, mock_license]
            mock_repo_class.return_value = mock_repo
            
            # Act
            response = lambda_handler(event, context)
            
            # Assert
            assert response['statusCode'] == 200
            
            # Assert - Golden Record selects DRIVERS_LICENSE value (higher reliability)
            golden_record = response['golden_record']
            assert golden_record['name']['value'] == 'John Doe'
            assert golden_record['name']['source_document'] == 'doc-license'
            
            # Assert - Alternative value from W2 is stored
            assert 'alternative_values' in golden_record['name']
            assert 'Jon Doe' in golden_record['name']['alternative_values']
            
            # Assert - Address from DRIVERS_LICENSE is selected
            assert golden_record['address']['value'] == '123 Main St, Springfield, IL 62701'
            assert golden_record['address']['source_document'] == 'doc-license'
            
            # Assert - Alternative address from W2 is stored
            assert 'alternative_values' in golden_record['address']
            assert '123 Main Street, Springfield, IL 62701' in golden_record['address']['alternative_values']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
