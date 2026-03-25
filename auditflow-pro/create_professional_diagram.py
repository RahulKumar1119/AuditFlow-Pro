#!/usr/bin/env python3
"""
AuditFlow-Pro Professional Architecture Diagram
Creates a high-quality diagram similar to AWS reference architectures
with proper service icons and styling
"""

import subprocess

# Create a professional DOT file with AWS styling
dot_content = """
digraph AuditFlowProArchitecture {
    rankdir=LR;
    bgcolor=white;
    splines=curved;
    nodesep=1.2;
    ranksep=1.5;
    
    // Define node styles
    node [fontname="Arial", fontsize=11, shape=box, style="rounded,filled"];
    edge [fontname="Arial", fontsize=9];
    
    // Title
    title [label="AuditFlow-Pro: AI-Powered Loan Document Auditor", 
           shape=plaintext, fontsize=16, fontname="Arial Bold"];
    
    // ============ CLIENT LAYER ============
    subgraph cluster_client {
        label="Client Layer";
        style=filled;
        fillcolor="#F5F5F5";
        color="#333333";
        fontcolor="#333333";
        fontsize=12;
        fontname="Arial Bold";
        margin=15;
        
        user [label="Loan Officer\\n(User)", fillcolor="#4A90E2", fontcolor=white, shape=box, width=2];
    }
    
    // ============ FRONTEND LAYER ============
    subgraph cluster_frontend {
        label="Frontend & Hosting";
        style=filled;
        fillcolor="#F5F5F5";
        color="#333333";
        fontcolor="#333333";
        fontsize=12;
        fontname="Arial Bold";
        margin=15;
        
        react [label="React Dashboard\\n(TypeScript)", fillcolor="#FF9900", fontcolor=white, shape=box, width=2.2];
        amplify [label="AWS Amplify\\n(Hosting)", fillcolor="#FF9900", fontcolor=white, shape=box, width=2.2];
    }
    
    // ============ SECURITY LAYER ============
    subgraph cluster_security {
        label="Security & Authentication";
        style=filled;
        fillcolor="#F5F5F5";
        color="#333333";
        fontcolor="#333333";
        fontsize=12;
        fontname="Arial Bold";
        margin=15;
        
        cognito [label="Amazon Cognito\\n(Auth)", fillcolor="#E74C3C", fontcolor=white, shape=box, width=2.2];
        kms [label="AWS KMS\\n(Encryption)", fillcolor="#E74C3C", fontcolor=white, shape=box, width=2.2];
    }
    
    // ============ API LAYER ============
    subgraph cluster_api {
        label="API & Integration";
        style=filled;
        fillcolor="#F5F5F5";
        color="#333333";
        fontcolor="#333333";
        fontsize=12;
        fontname="Arial Bold";
        margin=15;
        
        apigw [label="API Gateway\\n(REST)", fillcolor="#FF9900", fontcolor=white, shape=box, width=2.2];
        lambda_api [label="Lambda\\n(API Handler)", fillcolor="#FF9900", fontcolor=white, shape=box, width=2.2];
    }
    
    // ============ STORAGE LAYER ============
    subgraph cluster_storage {
        label="Storage Layer";
        style=filled;
        fillcolor="#F5F5F5";
        color="#333333";
        fontcolor="#333333";
        fontsize=12;
        fontname="Arial Bold";
        margin=15;
        
        s3 [label="Amazon S3\\n(Documents)", fillcolor="#FF9900", fontcolor=white, shape=box, width=2.2];
        dynamodb_docs [label="DynamoDB\\n(Documents)", fillcolor="#3498DB", fontcolor=white, shape=box, width=2.2];
        dynamodb_audit [label="DynamoDB\\n(Audit Records)", fillcolor="#3498DB", fontcolor=white, shape=box, width=2.2];
    }
    
    // ============ ORCHESTRATION LAYER ============
    subgraph cluster_orchestration {
        label="Orchestration";
        style=filled;
        fillcolor="#F5F5F5";
        color="#333333";
        fontcolor="#333333";
        fontsize=12;
        fontname="Arial Bold";
        margin=15;
        
        stepfunctions [label="Step Functions\\n(Workflow)", fillcolor="#FF9900", fontcolor=white, shape=box, width=2.2];
    }
    
    // ============ PROCESSING PIPELINE ============
    subgraph cluster_processing {
        label="Processing Pipeline";
        style=filled;
        fillcolor="#F5F5F5";
        color="#333333";
        fontcolor="#333333";
        fontsize=12;
        fontname="Arial Bold";
        margin=15;
        
        classifier [label="Classifier\\nLambda", fillcolor="#FF9900", fontcolor=white, shape=box, width=1.8];
        extractor [label="Extractor\\nLambda", fillcolor="#FF9900", fontcolor=white, shape=box, width=1.8];
        validator [label="Validator\\nLambda", fillcolor="#FF9900", fontcolor=white, shape=box, width=1.8];
        risk_scorer [label="Risk Scorer\\nLambda", fillcolor="#FF9900", fontcolor=white, shape=box, width=1.8];
        reporter [label="Reporter\\nLambda", fillcolor="#FF9900", fontcolor=white, shape=box, width=1.8];
    }
    
    // ============ AI/ML SERVICES ============
    subgraph cluster_aiml {
        label="AI/ML Services";
        style=filled;
        fillcolor="#F5F5F5";
        color="#333333";
        fontcolor="#333333";
        fontsize=12;
        fontname="Arial Bold";
        margin=15;
        
        textract [label="Textract\\n(OCR)", fillcolor="#27AE60", fontcolor=white, shape=box, width=1.8];
        comprehend [label="Comprehend\\n(PII)", fillcolor="#27AE60", fontcolor=white, shape=box, width=1.8];
        bedrock [label="Bedrock\\n(Claude)", fillcolor="#27AE60", fontcolor=white, shape=box, width=1.8];
    }
    
    // ============ MONITORING & ALERTS ============
    subgraph cluster_monitoring {
        label="Monitoring & Alerts";
        style=filled;
        fillcolor="#F5F5F5";
        color="#333333";
        fontcolor="#333333";
        fontsize=12;
        fontname="Arial Bold";
        margin=15;
        
        cloudwatch [label="CloudWatch\\n(Logs)", fillcolor="#9B59B6", fontcolor=white, shape=box, width=2.2];
        sns [label="SNS\\n(Alerts)", fillcolor="#E74C3C", fontcolor=white, shape=box, width=2.2];
    }
    
    // ============ CONNECTIONS ============
    
    // User to Frontend
    user -> react [label="Access", color="#333333", penwidth=2];
    react -> amplify [label="Deploy", color="#333333", penwidth=1.5, style=dashed];
    
    // Frontend to API
    amplify -> apigw [label="API Calls", color="#333333", penwidth=2];
    apigw -> cognito [label="Authenticate", color="#E74C3C", penwidth=2];
    apigw -> lambda_api [label="Route", color="#333333", penwidth=2];
    
    // API to Storage
    lambda_api -> s3 [label="Upload", color="#333333", penwidth=2];
    lambda_api -> dynamodb_docs [label="Query", color="#333333", penwidth=1.5, style=dashed];
    
    // S3 to Orchestration
    s3 -> stepfunctions [label="Trigger", color="#FF6B6B", penwidth=2];
    
    // Orchestration to Processing
    stepfunctions -> classifier [label="Start", color="#333333", penwidth=2];
    
    // Processing Pipeline Flow
    classifier -> textract [label="Analyze", color="#27AE60", penwidth=2];
    textract -> extractor [label="Extract", color="#333333", penwidth=2];
    extractor -> comprehend [label="Detect PII", color="#27AE60", penwidth=2];
    extractor -> validator [label="Validate", color="#333333", penwidth=2];
    validator -> bedrock [label="Reason", color="#27AE60", penwidth=2];
    validator -> risk_scorer [label="Score", color="#333333", penwidth=2];
    risk_scorer -> reporter [label="Report", color="#333333", penwidth=2];
    
    // Storage
    classifier -> dynamodb_docs [label="Save", color="#3498DB", penwidth=1.5];
    extractor -> dynamodb_docs [label="Save", color="#3498DB", penwidth=1.5];
    reporter -> dynamodb_audit [label="Save", color="#3498DB", penwidth=2];
    
    // Alerts
    reporter -> sns [label="Alert", color="#E74C3C", penwidth=2];
    sns -> user [label="Notify", color="#E74C3C", penwidth=2];
    
    // Monitoring
    classifier -> cloudwatch [label="Log", color="#9B59B6", penwidth=1.5, style=dashed];
    extractor -> cloudwatch [label="Log", color="#9B59B6", penwidth=1.5, style=dashed];
    validator -> cloudwatch [label="Log", color="#9B59B6", penwidth=1.5, style=dashed];
    risk_scorer -> cloudwatch [label="Log", color="#9B59B6", penwidth=1.5, style=dashed];
    reporter -> cloudwatch [label="Log", color="#9B59B6", penwidth=1.5, style=dashed];
    
    // Encryption
    s3 -> kms [label="Encrypt", color="#E74C3C", penwidth=1.5, style=dotted];
    dynamodb_docs -> kms [label="Encrypt", color="#E74C3C", penwidth=1.5, style=dotted];
    dynamodb_audit -> kms [label="Encrypt", color="#E74C3C", penwidth=1.5, style=dotted];
    
    // ============ LEGEND ============
    subgraph cluster_legend {
        label="Legend & Key Features";
        style=filled;
        fillcolor="#FFFACD";
        color="#333333";
        fontcolor="#333333";
        fontsize=11;
        fontname="Arial";
        margin=10;
        
        legend1 [label="Message Flow", shape=plaintext, fontsize=10];
        legend2 [label="Authentication", shape=plaintext, fontsize=10];
        legend3 [label="Logging", shape=plaintext, fontsize=10];
        legend4 [label="Encryption", shape=plaintext, fontsize=10];
        
        features [label="Key Features:\\n• Multi-document processing\\n• AI-powered validation\\n• Real-time risk scoring\\n• Automated alerts\\n• Comprehensive audit logging\\n• Banking-grade security", 
                 shape=box, style=filled, fillcolor=white, fontsize=9, fontname="Arial"];
    }
}
"""

# Write DOT file
dot_file = "auditflow-pro/architecture_professional.dot"
with open(dot_file, 'w') as f:
    f.write(dot_content)

print("✓ Professional DOT file created")

# Generate PNG
try:
    subprocess.run(['dot', '-Tpng', dot_file, '-o', 'auditflow-pro/architecture_professional.png'], 
                   check=True, capture_output=True)
    print("✓ Professional architecture diagram created!")
    print("✓ Saved as: auditflow-pro/architecture_professional.png")
except Exception as e:
    print(f"Error: {e}")
