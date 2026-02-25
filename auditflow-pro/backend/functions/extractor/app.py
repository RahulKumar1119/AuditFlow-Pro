# backend/functions/extractor/app.py

import os
import json
import time
import logging
import boto3
from parsers import parse_w2, parse_bank_statement, parse_tax_form_1040, parse_id_document

# Configure logging for CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize Textract client outside the handler for connection reuse
textract = boto3.client('textract', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

def process_multipage_document(s3_bucket: str, s3_key: str, doc_type: str) -> list:
    """
    Task 6.8: Handles multi-page PDFs using Textract Async APIs and pagination.
    This prevents Lambda timeouts on large loan documents.
    """
    logger.info(f"Starting async analysis for {s3_key} of type {doc_type}")
    
    # 1. Start the asynchronous job
    # We request both FORMS and TABLES features to support all document types
    response = textract.start_document_analysis(
        DocumentLocation={'S3Object': {'Bucket': s3_bucket, 'Name': s3_key}},
        FeatureTypes=['FORMS', 'TABLES']
    )
    job_id = response['JobId']
    
    # 2. Poll for completion (with timeout protection)
    max_attempts = 60 # 5 minutes maximum wait
    attempt = 0
    status = 'IN_PROGRESS'
    
    while status == 'IN_PROGRESS' and attempt < max_attempts:
        time.sleep(5)
        job_status_response = textract.get_document_analysis(JobId=job_id)
        status = job_status_response['JobStatus']
        attempt += 1
        
    if status != 'SUCCEEDED':
        raise Exception(f"Textract async job failed or timed out. Status: {status}")

    # 3. Aggregate data across all pages (Pagination)
    all_blocks = []
    next_token = None
    
    while True:
        kwargs = {'JobId': job_id}
        if next_token:
            kwargs['NextToken'] = next_token
            
        page_response = textract.get_document_analysis(**kwargs)
        all_blocks.extend(page_response.get('Blocks', []))
        
        next_token = page_response.get('NextToken')
        if not next_token:
            break
            
    logger.info(f"Successfully aggregated {len(all_blocks)} blocks across all pages.")
    return all_blocks

def lambda_handler(event, context):
    """
    Task 6.1: Data Extractor Lambda Handler.
    Routes document processing based on classification from the previous Step Function.
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    # Extract inputs from Step Functions payload
    document_id = event.get('document_id')
    doc_type = event.get('document_type')
    s3_bucket = event.get('metadata', {}).get('s3_bucket')
    s3_key = event.get('metadata', {}).get('s3_key')
    
    if not all([document_id, doc_type, s3_bucket, s3_key]):
        logger.error("Missing required fields in event payload.")
        raise ValueError("Missing required fields: document_id, document_type, s3_bucket, or s3_key")
        
    extracted_data = {}
    
    try:
        # 1. Identity Documents (Typically single page, utilize specialized AnalyzeID API)
        if doc_type in ['DRIVERS_LICENSE', 'ID_DOCUMENT']:
            logger.info(f"Processing Identity Document: {document_id}")
            response = textract.analyze_id(
                DocumentPages=[{'S3Object': {'Bucket': s3_bucket, 'Name': s3_key}}]
            )
            extracted_data = parse_id_document(response)
            
        # 2. Complex Forms and Multi-page Documents (W2s, Tax Forms, Bank Statements)
        else:
            logger.info(f"Processing Multi-page Form: {document_id}")
            # Aggregate blocks across all pages to handle potential multi-page files safely
            all_blocks = process_multipage_document(s3_bucket, s3_key, doc_type)
            
            # Route to specific parser based on classification
            if doc_type == 'W2':
                extracted_data = parse_w2(all_blocks)
            elif doc_type == 'BANK_STATEMENT':
                extracted_data = parse_bank_statement(all_blocks)
            elif doc_type == 'TAX_FORM':
                extracted_data = parse_tax_form_1040(all_blocks)
            else:
                logger.warning(f"No specific extractor implemented for type: {doc_type}. Passing through.")
                extracted_data = {"status": "unsupported_format"}

        # Attach the newly extracted data to the metadata payload
        metadata = event.get('metadata', {})
        metadata['extracted_data'] = extracted_data
        
        # Return structured output for the next Step Function
        return {
            "statusCode": 200,
            "document_id": document_id,
            "document_type": doc_type,
            "extraction_status": "SUCCESS",
            "metadata": metadata
        }

    except Exception as e:
        logger.error(f"Extraction failed for document {document_id}: {str(e)}")
        # Raise the exception so Step Functions can catch it and handle retries/failures
        raise e
