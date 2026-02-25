import os
import json
import time
import logging
import boto3
from botocore.exceptions import ClientError
from shared.models import DocumentMetadata

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize client outside handler for connection reuse
textract = boto3.client('textract', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

def analyze_document_with_retry(bucket: str, key: str, max_retries: int = 3):
    """Calls Textract with exponential backoff."""
    for attempt in range(max_retries):
        try:
            response = textract.analyze_document(
                Document={'S3Object': {'Bucket': bucket, 'Name': key}},
                FeatureTypes=['FORMS']
            )
            return response
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code in ['ProvisionedThroughputExceededException', 'ThrottlingException'] and attempt < max_retries - 1:
                sleep_time = (2 ** attempt) * 2  # Exponential backoff
                logger.warning(f"Textract throttled. Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                logger.error(f"Textract analysis failed: {str(e)}")
                raise

def classify_document(text_blocks: list) -> tuple:
    """
    Applies heuristic rules to determine document type and confidence.
    Returns (document_type, confidence).
    """
    text = " ".join([block['Text'].upper() for block in text_blocks if block['BlockType'] == 'LINE'])
    
    # 1. W2 Classification
    if "W-2" in text and "WAGE AND TAX STATEMENT" in text:
        return ("W2", 0.95)
    
    # 2. Tax Form Classification (e.g., 1040)
    if "1040" in text and ("U.S. INDIVIDUAL INCOME TAX RETURN" in text or "DEPARTMENT OF THE TREASURY" in text):
        return ("TAX_FORM", 0.95)
        
    # 3. Bank Statement Classification
    if "STATEMENT OF ACCOUNT" in text or "ENDING BALANCE" in text or "ACCOUNT NUMBER" in text:
        if "DEPOSITS" in text and "WITHDRAWALS" in text:
            return ("BANK_STATEMENT", 0.90)
            
    # 4. Driver's License Classification
    if "DRIVER LICENSE" in text or "DRIVER'S LICENSE" in text or "DMV" in text:
        return ("DRIVERS_LICENSE", 0.92)
        
    # 5. ID Document Classification
    if "PASSPORT" in text or "IDENTIFICATION CARD" in text:
        return ("ID_DOCUMENT", 0.85)
        
    # Default fallback
    return ("UNKNOWN", 0.40)

def lambda_handler(event, context):
    """
    Main Lambda entry point.
    Input: Step Functions event containing document details.
    """
    logger.info(f"Processing event: {json.dumps(event)}")
    
    document_id = event.get('document_id')
    s3_bucket = event.get('s3_bucket')
    s3_key = event.get('s3_key')
    
    # Initialize metadata object
    doc_metadata = DocumentMetadata(
        document_id=document_id,
        loan_application_id=event.get('loan_application_id', 'unknown'),
        s3_bucket=s3_bucket,
        s3_key=s3_key,
        upload_timestamp=event.get('upload_timestamp', ''),
        file_name=s3_key.split('/')[-1],
        file_size_bytes=event.get('file_size_bytes', 0),
        file_format=s3_key.split('.')[-1].upper(),
        checksum=event.get('checksum', '')
    )

    try:
        # Extract text using Textract
        response = analyze_document_with_retry(s3_bucket, s3_key)
        
        # Classify the document based on extracted text
        doc_type, confidence = classify_document(response.get('Blocks', []))
        
        doc_metadata.document_type = doc_type
        doc_metadata.classification_confidence = confidence
        
        # Flag for manual review if confidence is too low
        if confidence < 0.70:
            doc_metadata.requires_manual_review = True
            logger.warning(f"Document {document_id} flagged for manual review (Confidence: {confidence})")

        return {
            "document_id": doc_metadata.document_id,
            "document_type": doc_metadata.document_type,
            "confidence": doc_metadata.classification_confidence,
            "requires_manual_review": doc_metadata.requires_manual_review,
            "metadata": doc_metadata.to_dict()
        }

    except Exception as e:
        logger.error(f"Classification failed for {document_id}: {str(e)}")
        # Raise error to trigger Step Functions retry/failure routing
        raise e
