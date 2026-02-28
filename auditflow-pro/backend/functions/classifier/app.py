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

def analyze_document_with_retry(bucket: str, key: str, document_id: str, max_retries: int = 3):
    """
    Calls Textract with exponential backoff retry logic.
    
    Implements Requirement 11.3, 11.4: Retry with exponential backoff (5s, 15s, 45s).
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        document_id: Document identifier for logging
        max_retries: Maximum number of retry attempts (default: 3)
    
    Returns:
        Textract API response
        
    Raises:
        ClientError: When all retries are exhausted or non-retryable error occurs
    """
    # Retry delays: 5s, 15s, 45s (exponential backoff with base 3)
    retry_delays = [5, 15, 45]
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Calling Textract for document {document_id} (attempt {attempt + 1}/{max_retries})")
            
            response = textract.analyze_document(
                Document={'S3Object': {'Bucket': bucket, 'Name': key}},
                FeatureTypes=['FORMS']
            )
            
            logger.info(f"Textract analysis successful for document {document_id}")
            return response
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error'].get('Message', str(e))
            
            # Log error with context (Requirement 18.5)
            logger.error(
                f"Textract API error for document {document_id}: "
                f"ErrorCode={error_code}, Message={error_message}, "
                f"Attempt={attempt + 1}/{max_retries}, Bucket={bucket}, Key={key}"
            )
            
            # Retry on throttling or provisioned throughput errors
            if error_code in ['ProvisionedThroughputExceededException', 'ThrottlingException', 'ServiceUnavailable']:
                if attempt < max_retries - 1:
                    sleep_time = retry_delays[attempt]
                    logger.warning(
                        f"Textract throttled for document {document_id}. "
                        f"Retrying in {sleep_time} seconds (attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(sleep_time)
                else:
                    logger.error(
                        f"Textract retries exhausted for document {document_id} after {max_retries} attempts"
                    )
                    raise
            else:
                # Non-retryable error (e.g., InvalidS3ObjectException for illegible documents)
                logger.error(
                    f"Non-retryable Textract error for document {document_id}: {error_code}"
                )
                raise
                
        except Exception as e:
            # Catch unexpected errors (Requirement 18.2)
            logger.error(
                f"Unexpected error during Textract analysis for document {document_id}: "
                f"{type(e).__name__}: {str(e)}"
            )
            raise

def classify_document(text_blocks: list) -> tuple:
    """
    Applies heuristic rules to determine document type and confidence.
    Returns (document_type, confidence).
    
    Classification rules per requirements:
    - W2: IRS form structure, EIN detection
    - Bank Statement: Institution headers, transaction tables
    - Tax Form: IRS form numbers, tax year
    - Driver's License: DMV formats, license numbers
    - ID Document: Government ID characteristics
    """
    import re
    
    text = " ".join([block['Text'].upper() for block in text_blocks if block['BlockType'] == 'LINE'])
    
    # Extract key-value pairs for more detailed analysis
    key_value_pairs = {}
    for block in text_blocks:
        if block['BlockType'] == 'KEY_VALUE_SET' and 'KEY' in block.get('EntityTypes', []):
            # Extract key text
            key_text = ""
            if 'Relationships' in block:
                for rel in block['Relationships']:
                    if rel['Type'] == 'CHILD':
                        for child_id in rel['Ids']:
                            for b in text_blocks:
                                if b['Id'] == child_id and b['BlockType'] == 'WORD':
                                    key_text += b.get('Text', '') + " "
            if key_text:
                key_value_pairs[key_text.strip().upper()] = True
    
    # 1. W2 Classification - IRS structure and EIN detection
    w2_score = 0
    w2_indicators = [
        ("W-2" in text or "W2" in text, 30),
        ("WAGE AND TAX STATEMENT" in text, 25),
        (re.search(r'\b\d{2}-\d{7}\b', text) is not None, 20),  # EIN pattern XX-XXXXXXX
        ("EMPLOYER" in text and "IDENTIFICATION" in text, 15),
        ("SOCIAL SECURITY" in text and "WAGES" in text, 10),
        ("FEDERAL INCOME TAX WITHHELD" in text, 10),
        ("INTERNAL REVENUE SERVICE" in text or "IRS" in text, 5)
    ]
    for condition, points in w2_indicators:
        if condition:
            w2_score += points
    
    # 2. Bank Statement Classification - Institution headers and transaction tables
    bank_score = 0
    bank_indicators = [
        ("STATEMENT" in text and ("ACCOUNT" in text or "BANKING" in text), 25),
        ("ENDING BALANCE" in text or "CLOSING BALANCE" in text, 20),
        ("BEGINNING BALANCE" in text or "OPENING BALANCE" in text, 15),
        (("DEPOSITS" in text or "CREDITS" in text) and ("WITHDRAWALS" in text or "DEBITS" in text), 20),
        (re.search(r'ACCOUNT\s*(?:NUMBER|#)?\s*:?\s*\d+', text) is not None, 15),
        ("STATEMENT PERIOD" in text or "STATEMENT DATE" in text, 10),
        (any(bank in text for bank in ["BANK", "CREDIT UNION", "FINANCIAL", "CHASE", "WELLS FARGO", "BANK OF AMERICA"]), 10)
    ]
    for condition, points in bank_indicators:
        if condition:
            bank_score += points
    
    # 3. Tax Form Classification - IRS form numbers and tax year
    tax_score = 0
    tax_indicators = [
        (re.search(r'\b(1040|1099|W-2|1098)\b', text) is not None, 30),
        ("U.S. INDIVIDUAL INCOME TAX RETURN" in text, 25),
        ("DEPARTMENT OF THE TREASURY" in text, 20),
        ("INTERNAL REVENUE SERVICE" in text or "IRS" in text, 15),
        (re.search(r'\b(TAX YEAR|FILING STATUS)\b', text) is not None, 15),
        ("ADJUSTED GROSS INCOME" in text or "TAXABLE INCOME" in text, 10),
        (re.search(r'\b20\d{2}\b', text) is not None, 5)  # Tax year pattern
    ]
    for condition, points in tax_indicators:
        if condition:
            tax_score += points
    
    # 4. Driver's License Classification - DMV formats and license numbers
    dl_score = 0
    dl_indicators = [
        ("DRIVER LICENSE" in text or "DRIVER'S LICENSE" in text or "DRIVERS LICENSE" in text, 30),
        ("DMV" in text or "DEPARTMENT OF MOTOR VEHICLES" in text, 20),
        (re.search(r'\b(DL|LIC|LICENSE)\s*(?:NO|NUMBER|#)?\s*:?\s*[A-Z0-9-]+\b', text) is not None, 20),
        ("DATE OF BIRTH" in text or "DOB" in text, 15),
        ("EXPIRATION" in text or "EXPIRES" in text, 10),
        (any(state in text for state in ["CLASS", "RESTRICTIONS", "ENDORSEMENTS"]), 10),
        (re.search(r'\b(SEX|HEIGHT|WEIGHT|EYES|HAIR)\b', text) is not None, 10)
    ]
    for condition, points in dl_indicators:
        if condition:
            dl_score += points
    
    # 5. ID Document Classification - Government ID characteristics
    id_score = 0
    id_indicators = [
        ("PASSPORT" in text, 30),
        ("IDENTIFICATION CARD" in text or "IDENTITY CARD" in text or "ID CARD" in text, 25),
        ("UNITED STATES OF AMERICA" in text or "U.S. DEPARTMENT OF STATE" in text, 20),
        (re.search(r'\b(PASSPORT|ID)\s*(?:NO|NUMBER|#)?\s*:?\s*[A-Z0-9]+\b', text) is not None, 20),
        ("DATE OF BIRTH" in text or "DOB" in text, 10),
        ("NATIONALITY" in text or "COUNTRY" in text, 10),
        ("ISSUING AUTHORITY" in text or "ISSUED BY" in text, 10)
    ]
    for condition, points in id_indicators:
        if condition:
            id_score += points
    
    # Determine document type based on highest score
    scores = {
        "W2": w2_score,
        "BANK_STATEMENT": bank_score,
        "TAX_FORM": tax_score,
        "DRIVERS_LICENSE": dl_score,
        "ID_DOCUMENT": id_score
    }
    
    max_score = max(scores.values())
    
    # If no strong indicators, return UNKNOWN
    if max_score < 40:
        return ("UNKNOWN", 0.40)
    
    # Find document type with highest score
    doc_type = max(scores, key=scores.get)
    
    # Calculate confidence score (normalize to 0-1 range)
    # Max possible score is 100, so we normalize and cap at 0.99
    confidence = min(0.99, max_score / 100.0)
    
    # Ensure minimum confidence for classified documents
    if confidence < 0.70:
        confidence = max(0.60, confidence)
    
    return (doc_type, confidence)

def lambda_handler(event, context):
    """
    Main Lambda entry point for document classification.
    
    Implements:
    - Requirement 3.7: Flag documents for manual review when confidence < 70%
    - Requirement 3.8: Store document type classification
    - Requirement 11.3: Retry logic with exponential backoff
    - Requirement 11.4: 3 retries with delays of 5s, 15s, 45s
    - Requirement 18.2: Log classification results with document ID, type, confidence
    - Requirement 18.5: Log errors with context information
    
    Input: Step Functions event containing document details.
    """
    logger.info(f"Processing classification event: {json.dumps(event)}")
    
    document_id = event.get('document_id')
    s3_bucket = event.get('s3_bucket')
    s3_key = event.get('s3_key')
    loan_application_id = event.get('loan_application_id', 'unknown')
    
    # Log document processing start (Requirement 18.2)
    logger.info(
        f"Starting classification for document_id={document_id}, "
        f"loan_application_id={loan_application_id}, "
        f"s3_bucket={s3_bucket}, s3_key={s3_key}"
    )
    
    # Initialize metadata object
    doc_metadata = DocumentMetadata(
        document_id=document_id,
        loan_application_id=loan_application_id,
        s3_bucket=s3_bucket,
        s3_key=s3_key,
        upload_timestamp=event.get('upload_timestamp', ''),
        file_name=s3_key.split('/')[-1],
        file_size_bytes=event.get('file_size_bytes', 0),
        file_format=s3_key.split('.')[-1].upper(),
        checksum=event.get('checksum', '')
    )

    try:
        # Extract text using Textract with retry logic (Requirement 11.3, 11.4)
        response = analyze_document_with_retry(s3_bucket, s3_key, document_id)
        
        # Classify the document based on extracted text
        doc_type, confidence = classify_document(response.get('Blocks', []))
        
        doc_metadata.document_type = doc_type
        doc_metadata.classification_confidence = confidence
        
        # Flag for manual review if confidence is too low (Requirement 3.7)
        if confidence < 0.70:
            doc_metadata.requires_manual_review = True
            logger.warning(
                f"Document flagged for manual review: document_id={document_id}, "
                f"document_type={doc_type}, confidence={confidence:.2f}, "
                f"reason=confidence_below_threshold"
            )
        
        # Log successful classification (Requirement 18.2)
        logger.info(
            f"Classification completed: document_id={document_id}, "
            f"document_type={doc_type}, confidence={confidence:.2f}, "
            f"requires_manual_review={doc_metadata.requires_manual_review}"
        )

        return {
            "document_id": doc_metadata.document_id,
            "document_type": doc_metadata.document_type,
            "confidence": doc_metadata.classification_confidence,
            "requires_manual_review": doc_metadata.requires_manual_review,
            "metadata": doc_metadata.to_dict()
        }

    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error'].get('Message', str(e))
        
        # Handle illegible documents gracefully (Requirement 3.7, 11.3)
        if error_code in ['InvalidS3ObjectException', 'InvalidParameterException', 'UnsupportedDocumentException']:
            logger.error(
                f"Illegible or invalid document: document_id={document_id}, "
                f"error_code={error_code}, error_message={error_message}, "
                f"s3_bucket={s3_bucket}, s3_key={s3_key}"
            )
            
            # Return a result indicating illegible document with manual review flag
            doc_metadata.document_type = "ILLEGIBLE"
            doc_metadata.classification_confidence = 0.0
            doc_metadata.requires_manual_review = True
            
            logger.warning(
                f"Document marked as illegible: document_id={document_id}, "
                f"requires_manual_review=True"
            )
            
            return {
                "document_id": doc_metadata.document_id,
                "document_type": "ILLEGIBLE",
                "confidence": 0.0,
                "requires_manual_review": True,
                "error": f"Document is illegible or invalid: {error_code}",
                "metadata": doc_metadata.to_dict()
            }
        else:
            # Log error with full context (Requirement 18.5)
            logger.error(
                f"Classification failed for document {document_id}: "
                f"error_code={error_code}, error_message={error_message}, "
                f"loan_application_id={loan_application_id}, "
                f"s3_bucket={s3_bucket}, s3_key={s3_key}"
            )
            # Re-raise to trigger Step Functions retry/failure routing
            raise
            
    except Exception as e:
        # Log unexpected errors with stack trace (Requirement 18.5)
        logger.error(
            f"Unexpected error during classification: document_id={document_id}, "
            f"loan_application_id={loan_application_id}, "
            f"error_type={type(e).__name__}, error_message={str(e)}",
            exc_info=True  # Include stack trace
        )
        # Raise error to trigger Step Functions retry/failure routing
        raise
