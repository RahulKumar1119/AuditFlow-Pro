# backend/functions/reporter/app.py

import os
import json
import uuid
import logging
import re
from datetime import datetime, timezone
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError

# Configure CloudWatch logging (Task 10.4)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def convert_floats_to_decimals(obj):
    """Convert all floats in a nested structure to Decimal for DynamoDB compatibility."""
    if isinstance(obj, dict):
        return {k: convert_floats_to_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimals(item) for item in obj]
    elif isinstance(obj, float):
        return Decimal(str(obj))
    else:
        return obj

def clean_applicant_name(name):
    """
    Clean applicant name by removing address data.
    Extracts just the name part (before street address).
    """
    if not name:
        return "Unknown Applicant"
    
    # Pattern: Name followed by numbers (street address)
    # Extract everything before the first digit that starts a street number
    match = re.match(r'^([A-Za-z\s\.]+?)(?:\s+\d+\s+|$)', name)
    if match:
        cleaned = match.group(1).strip()
        if cleaned:
            return cleaned
    
    # If no pattern match, return original
    return name.strip()

# Initialize AWS clients (will be reinitialized in tests with mocked resources)
def get_aws_clients():
    """Get AWS clients - allows for easier mocking in tests."""
    aws_region = os.environ.get('AWS_REGION', 'ap-south-1')
    return (
        boto3.resource('dynamodb', region_name=aws_region),
        boto3.client('sns', region_name=aws_region)
    )

# Default clients
dynamodb, sns = get_aws_clients()

AUDIT_TABLE_NAME = os.environ.get('AUDIT_RECORDS_TABLE', 'AuditFlow-AuditRecords')
DOCS_TABLE_NAME = os.environ.get('DOCUMENTS_TABLE', 'AuditFlow-Documents')
ALERTS_TOPIC_ARN = os.environ.get('ALERTS_TOPIC_ARN', '')

def save_audit_record(record_data: dict):
    """Task 10.2: Store audit record in DynamoDB."""
    table_name = os.environ.get('AUDIT_RECORDS_TABLE', 'AuditFlow-AuditRecords')
    table = dynamodb.Table(table_name)
    try:
        # Convert all floats to Decimals for DynamoDB compatibility
        record_data = convert_floats_to_decimals(record_data)
        table.put_item(Item=record_data)
        logger.info(f"Successfully saved audit record {record_data['audit_record_id']} to DynamoDB.")
    except ClientError as e:
        logger.error(f"Failed to save audit record: {e.response['Error']['Message']}")
        raise

def update_document_statuses(documents: list, status: str):
    """Task 10.2: Update document processing status in DynamoDB."""
    table_name = os.environ.get('DOCUMENTS_TABLE', 'AuditFlow-Documents')
    table = dynamodb.Table(table_name)
    for doc in documents:
        doc_id = doc.get('document_id')
        try:
            table.update_item(
                Key={'document_id': doc_id},
                UpdateExpression="SET processing_status = :s",
                ExpressionAttributeValues={':s': status}
            )
            logger.info(f"Updated document {doc_id} status to {status}")
        except ClientError as e:
            logger.error(f"Failed to update document {doc_id}: {e.response['Error']['Message']}")
            # We log but don't fail the whole workflow if a single status update fails
            pass

def trigger_alerts(record_data: dict) -> list:
    """Task 10.3: Implement alert triggering via SNS."""
    alerts_topic_arn = os.environ.get('ALERTS_TOPIC_ARN', '')
    
    if not alerts_topic_arn:
        logger.warning("ALERTS_TOPIC_ARN not configured. Skipping SNS alerts.")
        return []

    risk_score = record_data.get('risk_score', 0)
    alerts_triggered = []
    
    # Get dashboard URL from environment or use default
    dashboard_url = os.environ.get('DASHBOARD_URL', 'https://auditflowpro.online')
    audit_record_id = record_data.get('audit_record_id', '')
    loan_application_id = record_data.get('loan_application_id', '')
    
    # Build audit detail link
    audit_link = f"{dashboard_url}/audits/{audit_record_id}"
    
    # Define thresholds based on requirements
    if risk_score > 80:
        alert_type = "CRITICAL"
        message = f"""CRITICAL ALERT: Loan Application {loan_application_id} flagged with Risk Score {risk_score}. Immediate review required.

Applicant: {record_data.get('applicant_name', 'Unknown')}
Risk Level: CRITICAL
Audit Record ID: {audit_record_id}

View Details: {audit_link}

Please review this application immediately."""
    elif risk_score > 50:
        alert_type = "HIGH"
        message = f"""HIGH RISK ALERT: Loan Application {loan_application_id} flagged with Risk Score {risk_score}. Review recommended.

Applicant: {record_data.get('applicant_name', 'Unknown')}
Risk Level: HIGH
Audit Record ID: {audit_record_id}

View Details: {audit_link}

Please review this application at your earliest convenience."""
    else:
        # No alert needed for low/medium risk
        return alerts_triggered

    try:
        response = sns.publish(
            TopicArn=alerts_topic_arn,
            Subject=f"AuditFlow Alert: {alert_type} Risk Detected - {loan_application_id}",
            Message=message,
            MessageAttributes={
                'RiskLevel': {'DataType': 'String', 'StringValue': alert_type},
                'LoanApplicationId': {'DataType': 'String', 'StringValue': loan_application_id},
                'AuditRecordId': {'DataType': 'String', 'StringValue': audit_record_id}
            }
        )
        logger.info(f"Triggered {alert_type} alert via SNS. MessageId: {response['MessageId']}")
        
        # Record the alert event (Task 10.3)
        alerts_triggered.append({
            "type": alert_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message_id": response['MessageId'],
            "audit_link": audit_link
        })
    except ClientError as e:
        logger.error(f"Failed to publish SNS alert: {e.response['Error']['Message']}")
        
    return alerts_triggered

def lambda_handler(event, context):
    """
    Task 10.1: Create Lambda handler and report compilation.
    """
    loan_application_id = event.get('loan_application_id')
    logger.info(f"Generating final report for application: {loan_application_id}")
    
    # 1. Compile complete audit record (Task 10.1)
    risk_assessment = event.get('risk_assessment', {})
    
    # Extract applicant name from golden record if available
    golden_record = event.get('golden_record', {})
    
    # Try to get name from 'name' field first (full name), then fallback to first_name + last_name
    if 'name' in golden_record and isinstance(golden_record['name'], dict):
        applicant_name = golden_record['name'].get('value', '').strip()
        # Clean the name to remove address data
        applicant_name = clean_applicant_name(applicant_name)
    else:
        applicant_first = golden_record.get('first_name', {}).get('value', '') if isinstance(golden_record.get('first_name'), dict) else golden_record.get('first_name', '')
        applicant_last = golden_record.get('last_name', {}).get('value', '') if isinstance(golden_record.get('last_name'), dict) else golden_record.get('last_name', '')
        applicant_name = f"{applicant_first} {applicant_last}".strip()
    
    # Final fallback
    if not applicant_name:
        applicant_name = "Unknown Applicant"
    
    audit_record_id = f"audit-{uuid.uuid4()}"
    
    audit_record = {
        "audit_record_id": audit_record_id,
        "loan_application_id": loan_application_id,
        "applicant_name": applicant_name,
        "audit_timestamp": datetime.now(timezone.utc).isoformat(),
        # Defaulting duration to 0 for simplicity, in a real scenario pass the start time through step functions
        "processing_duration_seconds": 0, 
        "status": "COMPLETED",
        "documents": event.get('documents', []),
        "golden_record": golden_record,
        "inconsistencies": event.get('inconsistencies', []),
        "risk_score": risk_assessment.get('risk_score', 0),
        "risk_level": risk_assessment.get('risk_level', 'UNKNOWN'),
        "risk_factors": risk_assessment.get('risk_factors', []),
        "alerts_triggered": []
    }
    
    try:
        # 2. Trigger Alerts (Task 10.3)
        triggered = trigger_alerts(audit_record)
        audit_record['alerts_triggered'] = triggered
        
        # 3. Store audit record in DynamoDB (Task 10.2)
        save_audit_record(audit_record)
        
        # 4. Update document processing status (Task 10.2)
        update_document_statuses(audit_record['documents'], "COMPLETED")
        
        # Log completion event with ID and Score (Task 10.4)
        logger.info(f"Audit Complete. AuditRecordID: {audit_record_id}, RiskScore: {audit_record['risk_score']}")
        
        return {
            "statusCode": 200,
            "message": "Report generated successfully",
            "audit_record_id": audit_record_id,
            "status": "COMPLETED"
        }
        
    except Exception as e:
        logger.error(f"Report generation failed: {str(e)}")
        # If the report fails, update documents to FAILED status
        update_document_statuses(event.get('documents', []), "FAILED")
        raise e
