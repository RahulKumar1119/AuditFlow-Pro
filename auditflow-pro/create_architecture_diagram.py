#!/usr/bin/env python3
"""
AuditFlow-Pro Architecture Diagram Generator
Creates a comprehensive AWS architecture diagram with service symbols
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import Lambda, StepFunctions
from diagrams.aws.storage import S3
from diagrams.aws.database import DynamoDB
from diagrams.aws.network import APIGateway
from diagrams.aws.security import Cognito, KMS
from diagrams.aws.integration import SNS
from diagrams.aws.management import CloudWatch
from diagrams.aws.ml import Textract, Comprehend, Bedrock
from diagrams.aws.network import CloudFront
from diagrams.onprem.client import Client
from diagrams.onprem.inmemory import Redis

# Create the main diagram
with Diagram("AuditFlow-Pro Architecture", filename="auditflow-pro/architecture_diagram", show=False, direction="TB"):
    
    # Users and Frontend
    with Cluster("Client Layer"):
        user = Client("Loan Officer")
        
    # Frontend Layer
    with Cluster("Frontend Layer (AWS Amplify)"):
        frontend = CloudFront("React Dashboard\n(TypeScript)")
        
    # Authentication Layer
    with Cluster("Authentication & Security"):
        cognito = Cognito("Cognito\nUser Pool")
        kms = KMS("KMS\nEncryption Keys")
        
    # API Layer
    with Cluster("API Layer"):
        api_gateway = APIGateway("API Gateway\n(REST)")
        api_lambda = Lambda("API Handler\nLambda")
        
    # Storage Layer
    with Cluster("Storage Layer"):
        s3 = S3("S3 Bucket\n(Documents)")
        dynamodb_docs = DynamoDB("DynamoDB\nDocuments Table")
        dynamodb_audits = DynamoDB("DynamoDB\nAudit Records")
        
    # Processing Orchestration
    with Cluster("Orchestration Layer"):
        step_functions = StepFunctions("Step Functions\nState Machine")
        
    # Processing Pipeline
    with Cluster("Processing Pipeline (Lambda Functions)"):
        classifier = Lambda("Classifier\nLambda")
        extractor = Lambda("Extractor\nLambda")
        validator = Lambda("Validator\nLambda")
        risk_scorer = Lambda("Risk Scorer\nLambda")
        reporter = Lambda("Reporter\nLambda")
        
    # AI/ML Services
    with Cluster("AI/ML Services"):
        textract = Textract("Textract\n(OCR & Extraction)")
        comprehend = Comprehend("Comprehend\n(PII Detection)")
        bedrock = Bedrock("Bedrock\n(Claude Sonnet 4)")
        
    # Monitoring & Alerts
    with Cluster("Monitoring & Alerts"):
        cloudwatch = CloudWatch("CloudWatch\n(Logs & Metrics)")
        sns = SNS("SNS\n(Alerts)")
        
    # Data flows
    user >> frontend
    frontend >> api_gateway
    api_gateway >> cognito
    api_gateway >> api_lambda
    
    # Document upload flow
    api_lambda >> s3
    s3 >> step_functions
    
    # Processing pipeline
    step_functions >> classifier
    classifier >> textract
    textract >> extractor
    extractor >> comprehend
    extractor >> validator
    validator >> bedrock
    validator >> risk_scorer
    risk_scorer >> reporter
    
    # Storage
    classifier >> dynamodb_docs
    extractor >> dynamodb_docs
    reporter >> dynamodb_audits
    
    # Alerts
    reporter >> sns
    
    # Monitoring
    classifier >> cloudwatch
    extractor >> cloudwatch
    validator >> cloudwatch
    risk_scorer >> cloudwatch
    reporter >> cloudwatch
    api_lambda >> cloudwatch
    
    # Encryption
    s3 >> kms
    dynamodb_docs >> kms
    dynamodb_audits >> kms

print("✓ Architecture diagram created successfully!")
print("✓ Saved as: auditflow-pro/architecture_diagram.png")
