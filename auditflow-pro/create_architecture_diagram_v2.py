#!/usr/bin/env python3
"""
AuditFlow-Pro Architecture Diagram Generator using Graphviz
Creates a comprehensive AWS architecture diagram with service symbols
"""

import subprocess
import os

# Create DOT file for Graphviz
dot_content = """
digraph AuditFlowArchitecture {
    rankdir=TB;
    bgcolor=white;
    node [shape=box, style=filled, fillcolor="#FF9900", fontcolor=white, fontname="Arial", fontsize=10];
    edge [color="#232F3E", penwidth=2];
    
    // Client Layer
    subgraph cluster_client {
        label="Client Layer";
        style=filled;
        fillcolor="#F0F0F0";
        color="#232F3E";
        fontcolor="#232F3E";
        fontsize=12;
        fontname="Arial";
        
        user [label="👤 Loan Officer", fillcolor="#FF9900"];
    }
    
    // Frontend Layer
    subgraph cluster_frontend {
        label="Frontend Layer (AWS Amplify)";
        style=filled;
        fillcolor="#F0F0F0";
        color="#232F3E";
        fontcolor="#232F3E";
        fontsize=12;
        fontname="Arial";
        
        frontend [label="🌐 React Dashboard\n(TypeScript + Vite)", fillcolor="#FF9900"];
    }
    
    // Authentication & Security
    subgraph cluster_auth {
        label="Authentication & Security";
        style=filled;
        fillcolor="#F0F0F0";
        color="#232F3E";
        fontcolor="#232F3E";
        fontsize=12;
        fontname="Arial";
        
        cognito [label="🔐 Cognito\nUser Pool", fillcolor="#FF9900"];
        kms [label="🔑 KMS\nEncryption Keys", fillcolor="#FF9900"];
    }
    
    // API Layer
    subgraph cluster_api {
        label="API Layer";
        style=filled;
        fillcolor="#F0F0F0";
        color="#232F3E";
        fontcolor="#232F3E";
        fontsize=12;
        fontname="Arial";
        
        api_gateway [label="🚪 API Gateway\n(REST)", fillcolor="#FF9900"];
        api_lambda [label="⚡ API Handler\nLambda", fillcolor="#FF9900"];
    }
    
    // Storage Layer
    subgraph cluster_storage {
        label="Storage Layer";
        style=filled;
        fillcolor="#F0F0F0";
        color="#232F3E";
        fontcolor="#232F3E";
        fontsize=12;
        fontname="Arial";
        
        s3 [label="📦 S3 Bucket\n(Documents)", fillcolor="#FF9900"];
        dynamodb_docs [label="📊 DynamoDB\nDocuments", fillcolor="#FF9900"];
        dynamodb_audits [label="📊 DynamoDB\nAudit Records", fillcolor="#FF9900"];
    }
    
    // Orchestration Layer
    subgraph cluster_orchestration {
        label="Orchestration Layer";
        style=filled;
        fillcolor="#F0F0F0";
        color="#232F3E";
        fontcolor="#232F3E";
        fontsize=12;
        fontname="Arial";
        
        step_functions [label="🔄 Step Functions\nState Machine", fillcolor="#FF9900"];
    }
    
    // Processing Pipeline
    subgraph cluster_processing {
        label="Processing Pipeline (Lambda Functions)";
        style=filled;
        fillcolor="#F0F0F0";
        color="#232F3E";
        fontcolor="#232F3E";
        fontsize=12;
        fontname="Arial";
        
        classifier [label="⚡ Classifier\nLambda", fillcolor="#FF9900"];
        extractor [label="⚡ Extractor\nLambda", fillcolor="#FF9900"];
        validator [label="⚡ Validator\nLambda", fillcolor="#FF9900"];
        risk_scorer [label="⚡ Risk Scorer\nLambda", fillcolor="#FF9900"];
        reporter [label="⚡ Reporter\nLambda", fillcolor="#FF9900"];
    }
    
    // AI/ML Services
    subgraph cluster_aiml {
        label="AI/ML Services";
        style=filled;
        fillcolor="#F0F0F0";
        color="#232F3E";
        fontcolor="#232F3E";
        fontsize=12;
        fontname="Arial";
        
        textract [label="🤖 Textract\n(OCR & Extraction)", fillcolor="#FF9900"];
        comprehend [label="🤖 Comprehend\n(PII Detection)", fillcolor="#FF9900"];
        bedrock [label="🤖 Bedrock\n(Claude Sonnet 4)", fillcolor="#FF9900"];
    }
    
    // Monitoring & Alerts
    subgraph cluster_monitoring {
        label="Monitoring & Alerts";
        style=filled;
        fillcolor="#F0F0F0";
        color="#232F3E";
        fontcolor="#232F3E";
        fontsize=12;
        fontname="Arial";
        
        cloudwatch [label="📈 CloudWatch\n(Logs & Metrics)", fillcolor="#FF9900"];
        sns [label="📢 SNS\n(Alerts)", fillcolor="#FF9900"];
    }
    
    // Data flows
    user -> frontend [label="Access"];
    frontend -> api_gateway [label="API Calls"];
    api_gateway -> cognito [label="Authenticate"];
    api_gateway -> api_lambda [label="Route"];
    
    // Document upload flow
    api_lambda -> s3 [label="Upload"];
    s3 -> step_functions [label="Trigger"];
    
    // Processing pipeline
    step_functions -> classifier [label="Start"];
    classifier -> textract [label="Analyze"];
    textract -> extractor [label="Extract"];
    extractor -> comprehend [label="Detect PII"];
    extractor -> validator [label="Validate"];
    validator -> bedrock [label="Reason"];
    validator -> risk_scorer [label="Score"];
    risk_scorer -> reporter [label="Report"];
    
    // Storage
    classifier -> dynamodb_docs [label="Save"];
    extractor -> dynamodb_docs [label="Save"];
    reporter -> dynamodb_audits [label="Save"];
    
    // Alerts
    reporter -> sns [label="Alert"];
    
    // Monitoring
    classifier -> cloudwatch [label="Log"];
    extractor -> cloudwatch [label="Log"];
    validator -> cloudwatch [label="Log"];
    risk_scorer -> cloudwatch [label="Log"];
    reporter -> cloudwatch [label="Log"];
    api_lambda -> cloudwatch [label="Log"];
    
    // Encryption
    s3 -> kms [label="Encrypt"];
    dynamodb_docs -> kms [label="Encrypt"];
    dynamodb_audits -> kms [label="Encrypt"];
}
"""

# Write DOT file
dot_file = "auditflow-pro/architecture_diagram.dot"
with open(dot_file, 'w') as f:
    f.write(dot_content)

print("✓ DOT file created")

# Try to generate PNG using graphviz
try:
    subprocess.run(['dot', '-Tpng', dot_file, '-o', 'auditflow-pro/architecture_diagram.png'], 
                   check=True, capture_output=True)
    print("✓ Architecture diagram created successfully!")
    print("✓ Saved as: auditflow-pro/architecture_diagram.png")
except FileNotFoundError:
    print("⚠ Graphviz not installed. Installing...")
    subprocess.run(['apt-get', 'update', '-qq'], capture_output=True)
    subprocess.run(['apt-get', 'install', '-y', 'graphviz'], capture_output=True)
    subprocess.run(['dot', '-Tpng', dot_file, '-o', 'auditflow-pro/architecture_diagram.png'], 
                   check=True, capture_output=True)
    print("✓ Architecture diagram created successfully!")
    print("✓ Saved as: auditflow-pro/architecture_diagram.png")
except Exception as e:
    print(f"Error: {e}")
    print("Trying alternative method...")
