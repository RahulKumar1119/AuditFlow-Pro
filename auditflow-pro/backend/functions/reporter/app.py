# backend/functions/reporter/app.py

import os
import json
import uuid
import logging
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError

# Configure CloudWatch logging (Task 10.4)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
aws_region = os.environ.get('AWS_REGION', 'ap-south-1')
dynamodb = boto3.resource('dynamodb', region_name=aws_region)
sns = boto3.client('sns', region_name=aws_region)

AUDIT_TABLE_NAME = os.environ.get('AUDIT_RECORDS_TABLE', 'AuditFlow-AuditRecords')
DOCS_TABLE_NAME = os.environ.get('DOCUMENTS_TABLE', 'AuditFlow-Documents')
ALERTS_TOPIC_ARN = os.environ.get('ALERTS_TOPIC_ARN', '')

def save_audit_record(record_data: dict):
    """Task 10.2: Store audit record in DynamoDB."""
    table = dynamodb.Table(AUDIT_TABLE_NAME)
    try:
        table.put_item(Item=record_data)
        logger.info(f"Successfully saved audit record {record_data['audit_record_id']} to DynamoDB.")
    except ClientError as e:
        logger.error(f"Failed to save audit record: {e.response['Error']['Message']}")
        raise

def update_document_statuses(documents: list, status: str):
    """Task 10.2: Update document processing status in DynamoDB."""
    table = dynamodb.Table(DOCS_TABLE_NAME)
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
    if not ALERTS_TOPIC_ARN:
        logger.warning("ALERTS_TOPIC_ARN not configured. Skipping SNS alerts.")
        return []

    risk_score = record_data.get('risk_score', 0)
    alerts_triggered = []
    
    # Define thresholds based on requirements
    if risk_score > 80:
        alert_type = "CRITICAL"
        message = f"CRITICAL ALERT: Loan Application {record_data['loan_application_id']} flagged with Risk Score {risk_score}. Immediate review required."
    elif risk_score > 50:
        alert_type = "HIGH"
        message = f"HIGH RISK ALERT: Loan Application {record_data['loan_application_id']} flagged with Risk Score {risk_score}. Review recommended."
    else:
        # No alert needed for low/medium risk
        return alerts_triggered

    try:
        response = sns.publish(
            TopicArn=ALERTS_TOPIC_ARN,
            Subject=f"AuditFlow Alert: {alert_type} Risk Detected",
            Message=message,
            MessageAttributes={
                'RiskLevel': {'DataType': 'String', 'StringValue': alert_type}
            }
        )
        logger.info(f"Triggered {alert_type} alert via SNS. MessageId: {response['MessageId']}")
        
        # Record the alert event (Task 10.3)
        alerts_triggered.append({
            "type": alert_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message_id": response['MessageId']
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
    applicant_first = golden_record.get('first_name', {}).get('value', '')
    applicant_last = golden_record.get('last_name', {}).get('value', '')
    applicant_name = f"{applicant_first} {applicant_last}".strip() or "Unknown Applicant"
    
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
