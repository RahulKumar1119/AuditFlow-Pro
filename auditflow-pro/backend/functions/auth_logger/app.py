# -*- coding: utf-8 -*-
"""
Authentication and Authorization Event Logger
Logs all authentication events to CloudWatch with PII redaction
Requirements: 18.3, 7.3, 20.9
"""

import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, Any

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# PII patterns to redact
PII_PATTERNS = {
    'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
    'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
    'ip_address': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
}


def redact_pii(data: Any) -> Any:
    """
    Recursively redact PII from data structures.
    
    Args:
        data: Data to redact (dict, list, str, or other)
        
    Returns:
        Data with PII redacted
    """
    if isinstance(data, dict):
        return {key: redact_pii(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [redact_pii(item) for item in data]
    elif isinstance(data, str):
        # Redact email addresses
        data = re.sub(PII_PATTERNS['email'], '[EMAIL_REDACTED]', data)
        # Redact SSN
        data = re.sub(PII_PATTERNS['ssn'], '[SSN_REDACTED]', data)
        # Redact phone numbers
        data = re.sub(PII_PATTERNS['phone'], '[PHONE_REDACTED]', data)
        # Partially redact IP addresses (keep first octet)
        data = re.sub(r'\b(\d{1,3}\.)\d{1,3}\.\d{1,3}\.\d{1,3}\b', r'\1xxx.xxx.xxx', data)
        return data
    else:
        return data


def extract_user_info(event: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract user information from Cognito event.
    
    Args:
        event: Cognito trigger event
        
    Returns:
        Dictionary with user information
    """
    user_info = {
        'user_id': event.get('userName', 'unknown'),
        'user_pool_id': event.get('userPoolId', 'unknown'),
        'trigger_source': event.get('triggerSource', 'unknown'),
    }
    
    # Extract user attributes if available
    if 'request' in event and 'userAttributes' in event['request']:
        attributes = event['request']['userAttributes']
        # Only log non-PII attributes
        user_info['email_verified'] = attributes.get('email_verified', 'false')
        user_info['phone_verified'] = attributes.get('phone_number_verified', 'false')
        # Redact actual email/phone
        if 'email' in attributes:
            user_info['email'] = '[EMAIL_REDACTED]'
        if 'phone_number' in attributes:
            user_info['phone'] = '[PHONE_REDACTED]'
    
    return user_info


def log_authentication_event(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Log authentication event with PII redaction.
    
    Args:
        event: Cognito trigger event
        context: Lambda context
        
    Returns:
        Event (unchanged for Cognito triggers)
    """
    try:
        # Extract event type
        trigger_source = event.get('triggerSource', 'unknown')
        
        # Extract user information
        user_info = extract_user_info(event)
        
        # Build log entry
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': 'authentication',
            'trigger_source': trigger_source,
            'user_id': user_info['user_id'],
            'user_pool_id': user_info['user_pool_id'],
            'request_id': context.request_id if context else 'unknown',
        }
        
        # Add event-specific information
        if trigger_source == 'PreAuthentication_Authentication':
            log_entry['action'] = 'pre_authentication'
            log_entry['description'] = 'User attempting to sign in'
            
        elif trigger_source == 'PostAuthentication_Authentication':
            log_entry['action'] = 'post_authentication'
            log_entry['description'] = 'User successfully signed in'
            log_entry['email_verified'] = user_info.get('email_verified', 'unknown')
            
        elif trigger_source == 'PreSignUp_SignUp':
            log_entry['action'] = 'pre_signup'
            log_entry['description'] = 'New user attempting to sign up'
            
        elif trigger_source == 'PostConfirmation_ConfirmSignUp':
            log_entry['action'] = 'post_confirmation'
            log_entry['description'] = 'User confirmed sign up'
            
        elif trigger_source == 'PreTokenGeneration_Authentication':
            log_entry['action'] = 'pre_token_generation'
            log_entry['description'] = 'Generating authentication tokens'
            # Log group membership for authorization tracking
            if 'request' in event and 'groupConfiguration' in event['request']:
                groups = event['request']['groupConfiguration'].get('groupsToOverride', [])
                log_entry['user_groups'] = groups
                log_entry['authorization_level'] = 'administrator' if 'Administrators' in groups else 'loan_officer'
            
        elif trigger_source == 'CustomMessage_ForgotPassword':
            log_entry['action'] = 'forgot_password'
            log_entry['description'] = 'User requested password reset'
            
        elif trigger_source == 'CustomMessage_AdminCreateUser':
            log_entry['action'] = 'admin_create_user'
            log_entry['description'] = 'Administrator created new user'
        
        # Redact any remaining PII
        log_entry = redact_pii(log_entry)
        
        # Log to CloudWatch
        logger.info(json.dumps(log_entry))
        
        # Return event unchanged (required for Cognito triggers)
        return event
        
    except Exception as e:
        logger.error(f"Error logging authentication event: {str(e)}")
        # Return event unchanged even on error
        return event


def log_authorization_decision(user_id: str, resource: str, action: str, decision: str, reason: str = None) -> None:
    """
    Log authorization decision.
    
    Args:
        user_id: User identifier
        resource: Resource being accessed
        action: Action being performed
        decision: Authorization decision (allow/deny)
        reason: Optional reason for decision
    """
    log_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'event_type': 'authorization',
        'user_id': user_id,
        'resource': resource,
        'action': action,
        'decision': decision,
    }
    
    if reason:
        log_entry['reason'] = reason
    
    # Redact any PII
    log_entry = redact_pii(log_entry)
    
    # Log to CloudWatch
    logger.info(json.dumps(log_entry))


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for Cognito triggers.
    
    Args:
        event: Cognito trigger event
        context: Lambda context
        
    Returns:
        Event (unchanged for Cognito triggers)
    """
    return log_authentication_event(event, context)


# For testing
if __name__ == '__main__':
    # Test PII redaction
    test_data = {
        'email': 'user@example.com',
        'ssn': '123-45-6789',
        'phone': '555-123-4567',
        'ip': '192.168.1.1',
        'nested': {
            'email': 'nested@example.com',
            'data': 'some data'
        }
    }
    
    redacted = redact_pii(test_data)
    print(json.dumps(redacted, indent=2))
