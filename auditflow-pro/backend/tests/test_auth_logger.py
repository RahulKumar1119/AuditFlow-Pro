"""
Unit tests for authentication logger
Tests PII redaction and event logging
Requirements: 18.3, 7.3
"""

import pytest
import json
from unittest.mock import Mock, patch
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'functions', 'auth_logger'))

from app import (
    redact_pii,
    extract_user_info,
    log_authentication_event,
    log_authorization_decision,
    lambda_handler
)


class TestPIIRedaction:
    """Test PII redaction functionality."""
    
    def test_redact_email(self):
        """Test email address redaction."""
        data = {'email': 'user@example.com', 'other': 'data'}
        redacted = redact_pii(data)
        assert redacted['email'] == '[EMAIL_REDACTED]'
        assert redacted['other'] == 'data'
    
    def test_redact_ssn(self):
        """Test SSN redaction."""
        data = {'ssn': '123-45-6789', 'other': 'data'}
        redacted = redact_pii(data)
        assert redacted['ssn'] == '[SSN_REDACTED]'
        assert redacted['other'] == 'data'
    
    def test_redact_phone(self):
        """Test phone number redaction."""
        test_cases = [
            '555-123-4567',
            '555.123.4567',
            '5551234567'
        ]
        for phone in test_cases:
            data = {'phone': phone}
            redacted = redact_pii(data)
            assert redacted['phone'] == '[PHONE_REDACTED]'
    
    def test_redact_ip_address(self):
        """Test IP address partial redaction."""
        data = {'ip': '192.168.1.1'}
        redacted = redact_pii(data)
        assert redacted['ip'] == '192.xxx.xxx.xxx'
    
    def test_redact_nested_data(self):
        """Test PII redaction in nested structures."""
        data = {
            'user': {
                'email': 'user@example.com',
                'ssn': '123-45-6789',
                'nested': {
                    'phone': '555-123-4567'
                }
            },
            'list': ['email@test.com', 'other data']
        }
        redacted = redact_pii(data)
        assert redacted['user']['email'] == '[EMAIL_REDACTED]'
        assert redacted['user']['ssn'] == '[SSN_REDACTED]'
        assert redacted['user']['nested']['phone'] == '[PHONE_REDACTED]'
        assert redacted['list'][0] == '[EMAIL_REDACTED]'
        assert redacted['list'][1] == 'other data'
    
    def test_redact_preserves_non_pii(self):
        """Test that non-PII data is preserved."""
        data = {
            'name': 'John Doe',
            'age': 30,
            'city': 'New York',
            'data': [1, 2, 3]
        }
        redacted = redact_pii(data)
        assert redacted == data


class TestUserInfoExtraction:
    """Test user information extraction from Cognito events."""
    
    def test_extract_basic_info(self):
        """Test extracting basic user information."""
        event = {
            'userName': 'test-user-123',
            'userPoolId': 'us-east-1_ABC123',
            'triggerSource': 'PostAuthentication_Authentication'
        }
        user_info = extract_user_info(event)
        assert user_info['user_id'] == 'test-user-123'
        assert user_info['user_pool_id'] == 'us-east-1_ABC123'
        assert user_info['trigger_source'] == 'PostAuthentication_Authentication'
    
    def test_extract_with_attributes(self):
        """Test extracting user attributes with PII redaction."""
        event = {
            'userName': 'test-user-123',
            'userPoolId': 'us-east-1_ABC123',
            'triggerSource': 'PostAuthentication_Authentication',
            'request': {
                'userAttributes': {
                    'email': 'user@example.com',
                    'phone_number': '+1234567890',
                    'email_verified': 'true',
                    'phone_number_verified': 'false'
                }
            }
        }
        user_info = extract_user_info(event)
        assert user_info['email'] == '[EMAIL_REDACTED]'
        assert user_info['phone'] == '[PHONE_REDACTED]'
        assert user_info['email_verified'] == 'true'
        assert user_info['phone_verified'] == 'false'
    
    def test_extract_missing_fields(self):
        """Test extraction with missing fields."""
        event = {}
        user_info = extract_user_info(event)
        assert user_info['user_id'] == 'unknown'
        assert user_info['user_pool_id'] == 'unknown'
        assert user_info['trigger_source'] == 'unknown'


class TestAuthenticationEventLogging:
    """Test authentication event logging."""
    
    @patch('app.logger')
    def test_log_pre_authentication(self, mock_logger):
        """Test logging pre-authentication event."""
        event = {
            'userName': 'test-user',
            'userPoolId': 'us-east-1_ABC123',
            'triggerSource': 'PreAuthentication_Authentication'
        }
        context = Mock()
        context.request_id = 'test-request-123'
        
        result = log_authentication_event(event, context)
        
        # Verify event is returned unchanged
        assert result == event
        
        # Verify logging was called
        assert mock_logger.info.called
        log_call = mock_logger.info.call_args[0][0]
        log_data = json.loads(log_call)
        
        assert log_data['event_type'] == 'authentication'
        assert log_data['action'] == 'pre_authentication'
        assert log_data['user_id'] == 'test-user'
        assert log_data['request_id'] == 'test-request-123'
    
    @patch('app.logger')
    def test_log_post_authentication(self, mock_logger):
        """Test logging post-authentication event."""
        event = {
            'userName': 'test-user',
            'userPoolId': 'us-east-1_ABC123',
            'triggerSource': 'PostAuthentication_Authentication',
            'request': {
                'userAttributes': {
                    'email_verified': 'true'
                }
            }
        }
        context = Mock()
        context.request_id = 'test-request-123'
        
        result = log_authentication_event(event, context)
        
        assert result == event
        assert mock_logger.info.called
        log_call = mock_logger.info.call_args[0][0]
        log_data = json.loads(log_call)
        
        assert log_data['action'] == 'post_authentication'
        assert log_data['email_verified'] == 'true'
    
    @patch('app.logger')
    def test_log_token_generation_with_groups(self, mock_logger):
        """Test logging token generation with group membership."""
        event = {
            'userName': 'admin-user',
            'userPoolId': 'us-east-1_ABC123',
            'triggerSource': 'PreTokenGeneration_Authentication',
            'request': {
                'groupConfiguration': {
                    'groupsToOverride': ['Administrators']
                }
            }
        }
        context = Mock()
        context.request_id = 'test-request-123'
        
        result = log_authentication_event(event, context)
        
        assert result == event
        assert mock_logger.info.called
        log_call = mock_logger.info.call_args[0][0]
        log_data = json.loads(log_call)
        
        assert log_data['action'] == 'pre_token_generation'
        assert log_data['user_groups'] == ['Administrators']
        assert log_data['authorization_level'] == 'administrator'
    
    @patch('app.logger')
    def test_log_token_generation_loan_officer(self, mock_logger):
        """Test logging token generation for loan officer."""
        event = {
            'userName': 'loan-officer',
            'userPoolId': 'us-east-1_ABC123',
            'triggerSource': 'PreTokenGeneration_Authentication',
            'request': {
                'groupConfiguration': {
                    'groupsToOverride': ['LoanOfficers']
                }
            }
        }
        context = Mock()
        context.request_id = 'test-request-123'
        
        result = log_authentication_event(event, context)
        
        assert result == event
        log_call = mock_logger.info.call_args[0][0]
        log_data = json.loads(log_call)
        
        assert log_data['authorization_level'] == 'loan_officer'
    
    @patch('app.logger')
    def test_log_password_reset(self, mock_logger):
        """Test logging password reset request."""
        event = {
            'userName': 'test-user',
            'userPoolId': 'us-east-1_ABC123',
            'triggerSource': 'CustomMessage_ForgotPassword'
        }
        context = Mock()
        context.request_id = 'test-request-123'
        
        result = log_authentication_event(event, context)
        
        assert result == event
        log_call = mock_logger.info.call_args[0][0]
        log_data = json.loads(log_call)
        
        assert log_data['action'] == 'forgot_password'
    
    @patch('app.logger')
    def test_log_event_with_pii_redaction(self, mock_logger):
        """Test that PII is redacted from logged events."""
        event = {
            'userName': 'user@example.com',
            'userPoolId': 'us-east-1_ABC123',
            'triggerSource': 'PostAuthentication_Authentication',
            'request': {
                'userAttributes': {
                    'email': 'user@example.com',
                    'phone_number': '555-123-4567'
                }
            }
        }
        context = Mock()
        context.request_id = 'test-request-123'
        
        result = log_authentication_event(event, context)
        
        assert result == event
        log_call = mock_logger.info.call_args[0][0]
        log_data = json.loads(log_call)
        
        # Verify PII was redacted in log
        log_str = json.dumps(log_data)
        assert 'user@example.com' not in log_str
        assert '555-123-4567' not in log_str
    
    @patch('app.logger')
    def test_log_event_error_handling(self, mock_logger):
        """Test that errors in logging don't break the flow."""
        # Malformed event
        event = {'invalid': 'event'}
        context = Mock()
        context.request_id = 'test-request-123'
        
        # Should not raise exception
        result = log_authentication_event(event, context)
        
        # Event should be returned unchanged
        assert result == event


class TestAuthorizationLogging:
    """Test authorization decision logging."""
    
    @patch('app.logger')
    def test_log_authorization_allow(self, mock_logger):
        """Test logging authorization allow decision."""
        log_authorization_decision(
            user_id='test-user',
            resource='s3://bucket/document.pdf',
            action='read',
            decision='allow',
            reason='User has LoanOfficer role'
        )
        
        assert mock_logger.info.called
        log_call = mock_logger.info.call_args[0][0]
        log_data = json.loads(log_call)
        
        assert log_data['event_type'] == 'authorization'
        assert log_data['user_id'] == 'test-user'
        assert log_data['resource'] == 's3://bucket/document.pdf'
        assert log_data['action'] == 'read'
        assert log_data['decision'] == 'allow'
        assert log_data['reason'] == 'User has LoanOfficer role'
    
    @patch('app.logger')
    def test_log_authorization_deny(self, mock_logger):
        """Test logging authorization deny decision."""
        log_authorization_decision(
            user_id='test-user',
            resource='dynamodb://table/item',
            action='write',
            decision='deny',
            reason='User lacks Administrator role'
        )
        
        assert mock_logger.info.called
        log_call = mock_logger.info.call_args[0][0]
        log_data = json.loads(log_call)
        
        assert log_data['decision'] == 'deny'
        assert log_data['reason'] == 'User lacks Administrator role'
    
    @patch('app.logger')
    def test_log_authorization_with_pii_redaction(self, mock_logger):
        """Test that PII is redacted from authorization logs."""
        log_authorization_decision(
            user_id='user@example.com',
            resource='s3://bucket/123-45-6789.pdf',
            action='read',
            decision='allow'
        )
        
        log_call = mock_logger.info.call_args[0][0]
        log_data = json.loads(log_call)
        
        # Verify PII was redacted
        assert log_data['user_id'] == '[EMAIL_REDACTED]'
        assert '[SSN_REDACTED]' in log_data['resource']


class TestLambdaHandler:
    """Test Lambda handler function."""
    
    @patch('app.log_authentication_event')
    def test_lambda_handler(self, mock_log_event):
        """Test Lambda handler delegates to log_authentication_event."""
        event = {'test': 'event'}
        context = Mock()
        
        mock_log_event.return_value = event
        
        result = lambda_handler(event, context)
        
        assert result == event
        mock_log_event.assert_called_once_with(event, context)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
