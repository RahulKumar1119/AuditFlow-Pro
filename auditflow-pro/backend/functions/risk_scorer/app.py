# backend/functions/risk_scorer/app.py

import json
import logging
from scorer import calculate_total_risk

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Task 9.1: Risk Score Calculator Lambda Handler.
    """
    loan_application_id = event.get('loan_application_id')
    logger.info(f"Calculating risk score for application: {loan_application_id}")
    
    inconsistencies = event.get('inconsistencies', [])
    golden_record = event.get('golden_record', {})
    documents = event.get('documents', [])
    
    if not loan_application_id:
        raise ValueError("Missing loan_application_id in event payload.")

    try:
        # Calculate the risk metrics
        risk_metrics = calculate_total_risk(inconsistencies, golden_record, documents)
        
        # Merge the risk metrics into the payload to pass to the next step
        response = {
            "statusCode": 200,
            "loan_application_id": loan_application_id,
            "documents": documents,
            "inconsistencies": inconsistencies,
            "golden_record": golden_record,
            "risk_assessment": risk_metrics
        }
        
        logger.info(f"Risk Assessment completed. Score: {risk_metrics['risk_score']} ({risk_metrics['risk_level']})")
        return response
        
    except Exception as e:
        logger.error(f"Failed to calculate risk score: {str(e)}")
        raise e
