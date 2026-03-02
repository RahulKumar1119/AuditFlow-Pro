# backend/tests/test_trigger.py
# Task 13.4: Integration tests for S3 event triggers
# Requirements: 20.2

import json
import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import the Lambda handler
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../functions/trigger'))
from app import (
    lambda_handler,
    validate_file_format,
    validate_file_size,
    extract_document_metadata,
    initiate_workflow,
    MAX_FILE_SIZE_BYTES,
    SUPPORTED_EXTENSIONS
)


class TestFileValidation:
    """Test file format and size validation"""
    
    def test_validate_supported_formats(self):
        """Test that all supported file formats are accepted"""
        supported_files = [
            'document.pdf',
            'image.jpeg',
            'photo.jpg',
            'scan.png',
            'document.tiff',
            'scan.tif'
        ]
        
        for filename in supported_files:
            assert validate_file_format(filename), f"Should accept {filename}"
    
    def test_validate_unsupported_formats(self):
        """Test that unsupported file formats are rejected"""
        unsupported_files = [
            'document.docx',
            'spreadsheet.xlsx',
            'text.txt',
            'archive.zip',
            'video.mp4'
        ]
        
        for filename in unsupported_files:
            assert not validate_file_format(filename), f"Should reject {filename}"
    
    def test_validate_case_insensitive_extensions(self):
        """Test that file extension validation is case-insensitive"""
        assert validate_file_format('document.PDF')
        assert validate_file_format('image.JPEG')
        assert validate_file_format('photo.Jpg')
        assert validate_file_format('scan.PNG')
    
    def test_validate_file_size_within_limit(self):
        """Test that files within 50MB limit are accepted"""
        # Test various sizes under the limit
        sizes = [
            1024,  # 1 KB
            1024 * 1024,  # 1 MB
            10 * 1024 * 1024,  # 10 MB
            49 * 1024 * 1024,  # 49 MB
            MAX_FILE_SIZE_BYTES - 1  # Just under limit
        ]
        
        for size in sizes:
            assert validate_file_size(size, 'test.pdf'), f"Should accept size {size}"
    
    def test_validate_file_size_exceeds_limit(self):
        """Test that files exceeding 50MB limit are rejected (Requirement 1.4)"""
        # Test sizes over the limit
        sizes = [
            MAX_FILE_SIZE_BYTES + 1,  # Just over limit
            51 * 1024 * 1024,  # 51 MB
            100 * 1024 * 1024,  # 100 MB
        ]
        
        for size in sizes:
            assert not validate_file_size(size, 'test.pdf'), f"Should reject size {size}"
    
    def test_validate_file_size_exactly_at_limit(self):
        """Test file exactly at 50MB limit"""
        # Exactly 50MB should be accepted (only > 50MB is rejected)
        assert validate_file_size(MAX_FILE_SIZE_BYTES, 'test.pdf')


class TestDocumentMetadataExtraction:
    """Test document metadata extraction from S3 events"""
    
    def test_extract_metadata_from_s3_record(self):
        """Test extracting metadata from S3 event record"""
        s3_record = {
            's3': {
                'bucket': {'name': 'test-bucket'},
                'object': {
                    'key': 'uploads/loan-123/document.pdf',
                    'size': 1024000
                }
            },
            'eventTime': '2024-01-15T10:30:00.000Z'
        }
        
        context = Mock()
        context.aws_request_id = 'test-request-id-12345'
        
        metadata = extract_document_metadata(s3_record, context)
        
        assert metadata['bucket'] == 'test-bucket'
        assert metadata['key'] == 'uploads/loan-123/document.pdf'
        assert metadata['size'] == 1024000
        assert metadata['loan_app_id'] == 'loan-123'
        assert metadata['document_id'].startswith('doc-test-req')
        assert metadata['event_time'] == '2024-01-15T10:30:00.000Z'
    
    def test_extract_metadata_with_url_encoded_key(self):
        """Test handling of URL-encoded S3 keys"""
        s3_record = {
            's3': {
                'bucket': {'name': 'test-bucket'},
                'object': {
                    'key': 'uploads/loan-123/my+document+with+spaces.pdf',
                    'size': 1024000
                }
            },
            'eventTime': '2024-01-15T10:30:00.000Z'
        }
        
        context = Mock()
        context.aws_request_id = 'test-request-id'
        
        metadata = extract_document_metadata(s3_record, context)
        
        # URL-encoded '+' should be decoded to space
        assert 'my document with spaces.pdf' in metadata['key']
    
    def test_extract_metadata_with_missing_loan_id(self):
        """Test handling of S3 keys without loan ID"""
        s3_record = {
            's3': {
                'bucket': {'name': 'test-bucket'},
                'object': {
                    'key': 'document.pdf',  # No uploads/ prefix
                    'size': 1024000
                }
            },
            'eventTime': '2024-01-15T10:30:00.000Z'
        }
        
        context = Mock()
        context.aws_request_id = 'test-request-id'
        
        metadata = extract_document_metadata(s3_record, context)
        
        # Should default to "unknown-loan"
        assert metadata['loan_app_id'] == 'unknown-loan'


class TestWorkflowInitiation:
    """Test Step Functions workflow initiation"""
    
    @patch('app.sfn_client')
    def test_initiate_workflow_success(self, mock_sfn_client):
        """Test successful workflow initiation"""
        mock_sfn_client.start_execution.return_value = {
            'executionArn': 'arn:aws:states:region:account:execution:state-machine:execution-id'
        }
        
        metadata = {
            'bucket': 'test-bucket',
            'key': 'uploads/loan-123/document.pdf',
            'size': 1024000,
            'loan_app_id': 'loan-123',
            'document_id': 'doc-12345',
            'event_time': '2024-01-15T10:30:00.000Z'
        }
        
        response = initiate_workflow(metadata)
        
        # Verify Step Functions was called
        mock_sfn_client.start_execution.assert_called_once()
        call_args = mock_sfn_client.start_execution.call_args
        
        # Verify execution name
        assert call_args[1]['name'] == 'loan-123-doc-12345'
        
        # Verify input payload
        input_payload = json.loads(call_args[1]['input'])
        assert input_payload['loan_application_id'] == 'loan-123'
        assert len(input_payload['documents']) == 1
        assert input_payload['documents'][0]['document_id'] == 'doc-12345'
        assert input_payload['documents'][0]['s3_bucket'] == 'test-bucket'
        assert input_payload['documents'][0]['s3_key'] == 'uploads/loan-123/document.pdf'
        
        # Verify response
        assert 'executionArn' in response


class TestLambdaHandler:
    """Test the main Lambda handler function"""
    
    @patch('app.sfn_client')
    def test_handler_processes_valid_s3_event(self, mock_sfn_client):
        """Test handler processes valid S3 event successfully"""
        mock_sfn_client.start_execution.return_value = {
            'executionArn': 'arn:aws:states:region:account:execution:state-machine:execution-id'
        }
        
        # Create SQS event with S3 notification
        event = {
            'Records': [
                {
                    'messageId': 'msg-123',
                    'body': json.dumps({
                        'Records': [
                            {
                                's3': {
                                    'bucket': {'name': 'test-bucket'},
                                    'object': {
                                        'key': 'uploads/loan-123/document.pdf',
                                        'size': 1024000
                                    }
                                },
                                'eventTime': '2024-01-15T10:30:00.000Z'
                            }
                        ]
                    })
                }
            ]
        }
        
        context = Mock()
        context.aws_request_id = 'test-request-id'
        
        result = lambda_handler(event, context)
        
        # Should process successfully with no failures
        assert result['batchItemFailures'] == []
        
        # Verify Step Functions was called
        mock_sfn_client.start_execution.assert_called_once()
    
    @patch('app.sfn_client')
    def test_handler_rejects_oversized_file(self, mock_sfn_client):
        """Test handler rejects files exceeding 50MB (Requirement 1.4)"""
        # Create event with oversized file
        event = {
            'Records': [
                {
                    'messageId': 'msg-123',
                    'body': json.dumps({
                        'Records': [
                            {
                                's3': {
                                    'bucket': {'name': 'test-bucket'},
                                    'object': {
                                        'key': 'uploads/loan-123/large-document.pdf',
                                        'size': 60 * 1024 * 1024  # 60 MB
                                    }
                                },
                                'eventTime': '2024-01-15T10:30:00.000Z'
                            }
                        ]
                    })
                }
            ]
        }
        
        context = Mock()
        context.aws_request_id = 'test-request-id'
        
        result = lambda_handler(event, context)
        
        # Should process without failures (file rejected, not error)
        assert result['batchItemFailures'] == []
        
        # Step Functions should NOT be called
        mock_sfn_client.start_execution.assert_not_called()
    
    @patch('app.sfn_client')
    def test_handler_rejects_unsupported_format(self, mock_sfn_client):
        """Test handler rejects unsupported file formats"""
        event = {
            'Records': [
                {
                    'messageId': 'msg-123',
                    'body': json.dumps({
                        'Records': [
                            {
                                's3': {
                                    'bucket': {'name': 'test-bucket'},
                                    'object': {
                                        'key': 'uploads/loan-123/document.docx',
                                        'size': 1024000
                                    }
                                },
                                'eventTime': '2024-01-15T10:30:00.000Z'
                            }
                        ]
                    })
                }
            ]
        }
        
        context = Mock()
        context.aws_request_id = 'test-request-id'
        
        result = lambda_handler(event, context)
        
        # Should process without failures (file rejected, not error)
        assert result['batchItemFailures'] == []
        
        # Step Functions should NOT be called
        mock_sfn_client.start_execution.assert_not_called()
    
    def test_handler_handles_s3_test_event(self):
        """Test handler gracefully handles S3 test events"""
        event = {
            'Records': [
                {
                    'messageId': 'msg-123',
                    'body': json.dumps({
                        'Event': 's3:TestEvent'
                    })
                }
            ]
        }
        
        context = Mock()
        context.aws_request_id = 'test-request-id'
        
        result = lambda_handler(event, context)
        
        # Should process successfully
        assert result['batchItemFailures'] == []
    
    @patch('app.sfn_client')
    def test_handler_processes_multiple_records(self, mock_sfn_client):
        """Test handler processes multiple S3 events in batch (Requirement 10.4)"""
        mock_sfn_client.start_execution.return_value = {
            'executionArn': 'arn:aws:states:region:account:execution:state-machine:execution-id'
        }
        
        # Create event with multiple documents
        event = {
            'Records': [
                {
                    'messageId': 'msg-1',
                    'body': json.dumps({
                        'Records': [
                            {
                                's3': {
                                    'bucket': {'name': 'test-bucket'},
                                    'object': {
                                        'key': 'uploads/loan-123/doc1.pdf',
                                        'size': 1024000
                                    }
                                },
                                'eventTime': '2024-01-15T10:30:00.000Z'
                            }
                        ]
                    })
                },
                {
                    'messageId': 'msg-2',
                    'body': json.dumps({
                        'Records': [
                            {
                                's3': {
                                    'bucket': {'name': 'test-bucket'},
                                    'object': {
                                        'key': 'uploads/loan-123/doc2.pdf',
                                        'size': 2048000
                                    }
                                },
                                'eventTime': '2024-01-15T10:31:00.000Z'
                            }
                        ]
                    })
                }
            ]
        }
        
        context = Mock()
        context.aws_request_id = 'test-request-id'
        
        result = lambda_handler(event, context)
        
        # Should process both successfully
        assert result['batchItemFailures'] == []
        
        # Step Functions should be called twice
        assert mock_sfn_client.start_execution.call_count == 2
    
    @patch('app.sfn_client')
    def test_handler_reports_batch_failures(self, mock_sfn_client):
        """Test handler reports batch item failures for retry"""
        # Make Step Functions fail
        mock_sfn_client.start_execution.side_effect = Exception("Step Functions error")
        
        event = {
            'Records': [
                {
                    'messageId': 'msg-123',
                    'body': json.dumps({
                        'Records': [
                            {
                                's3': {
                                    'bucket': {'name': 'test-bucket'},
                                    'object': {
                                        'key': 'uploads/loan-123/document.pdf',
                                        'size': 1024000
                                    }
                                },
                                'eventTime': '2024-01-15T10:30:00.000Z'
                            }
                        ]
                    })
                }
            ]
        }
        
        context = Mock()
        context.aws_request_id = 'test-request-id'
        
        result = lambda_handler(event, context)
        
        # Should report the failed message for retry
        assert len(result['batchItemFailures']) == 1
        assert result['batchItemFailures'][0]['itemIdentifier'] == 'msg-123'


class TestConcurrencyControl:
    """Test concurrent execution limits and queuing behavior"""
    
    def test_max_file_size_constant(self):
        """Verify MAX_FILE_SIZE_BYTES is set to 50MB"""
        assert MAX_FILE_SIZE_BYTES == 50 * 1024 * 1024
    
    def test_supported_extensions_complete(self):
        """Verify all required file formats are supported (Requirement 1.3)"""
        required_extensions = {'.pdf', '.jpeg', '.jpg', '.png', '.tiff', '.tif'}
        assert SUPPORTED_EXTENSIONS == required_extensions


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

