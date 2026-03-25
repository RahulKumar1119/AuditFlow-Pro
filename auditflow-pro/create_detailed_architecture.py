#!/usr/bin/env python3
"""
AuditFlow-Pro Detailed Architecture Diagram with AWS Colors
"""

import subprocess

# Create a more detailed DOT file with AWS color scheme
dot_content = """
digraph AuditFlowDetailedArchitecture {
    rankdir=TB;
    bgcolor=white;
    splines=ortho;
    nodesep=0.5;
    ranksep=1.0;
    
    // Define AWS color scheme
    node [fontname="Arial", fontsize=11, shape=box, style="rounded,filled"];
    edge [color="#232F3E", penwidth=2.5, fontname="Arial", fontsize=9];
    
    // Client Layer
    subgraph cluster_0 {
        label="Client Layer";
        style=filled;
        fillcolor="#E8F4F8";
        color="#232F3E";
        fontcolor="#232F3E";
        fontsize=13;
        fontname="Arial Bold";
        margin=20;
        
        user [label="👤 Loan Officer", fillcolor="#FF9900", fontcolor=white, shape=ellipse];
    }
    
    // Frontend & Hosting
    subgraph cluster_1 {
        label="Frontend & Hosting (AWS Amplify)";
        style=filled;
        fillcolor="#E8F4F8";
        color="#232F3E";
        fontcolor="#232F3E";
        fontsize=13;
        fontname="Arial Bold";
        margin=20;
        
        frontend [label="React Dashboard\\n(TypeScript + Vite)", fillcolor="#FF9900", fontcolor=white];
        cloudfront [label="CloudFront\\n(CDN)", fillcolor="#FF9900", fontcolor=white];
    }
    
    // Security & Auth
    subgraph cluster_2 {
        label="Security & Authentication";
        style=filled;
        fillcolor="#E8F4F8";
        color="#232F3E";
        fontcolor="#232F3E";
        fontsize=13;
        fontname="Arial Bold";
        margin=20;
        
        cognito [label="Cognito\\nUser Pool", fillcolor="#FF9900", fontcolor=white];
        kms [label="KMS\\nEncryption", fillcolor="#FF9900", fontcolor=white];
    }
    
    // API Layer
    subgraph cluster_3 {
        label="API Layer";
        style=filled;
        fillcolor="#E8F4F8";
        color="#232F3E";
        fontcolor="#232F3E";
        fontsize=13;
        fontname="Arial Bold";
        margin=20;
        
        api_gateway [label="API Gateway\\n(REST)", fillcolor="#FF9900", fontcolor=white];
        api_lambda [label="API Handler\\nLambda", fillcolor="#FF9900", fontcolor=white];
    }
    
    // Storage Layer
    subgraph cluster_4 {
        label="Storage Layer";
        style=filled;
        fillcolor="#E8F4F8";
        color="#232F3E";
        fontcolor="#232F3E";
        fontsize=13;
        fontname="Arial Bold";
        margin=20;
        
        s3 [label="S3 Bucket\\n(Documents)", fillcolor="#FF9900", fontcolor=white];
        dynamodb_docs [label="DynamoDB\\nDocuments", fillcolor="#FF9900", fontcolor=white];
        dynamodb_audits [label="DynamoDB\\nAudit Records", fillcolor="#FF9900", fontcolor=white];
    }
    
    // Orchestration
    subgraph cluster_5 {
        label="Orchestration Layer";
        style=filled;
        fillcolor="#E8F4F8";
        color="#232F3E";
        fontcolor="#232F3E";
        fontsize=13;
        fontname="Arial Bold";
        margin=20;
        
        step_functions [label="Step Functions\\nState Machine", fillcolor="#FF9900", fontcolor=white];
    }
    
    // Processing Pipeline
    subgraph cluster_6 {
        label="Processing Pipeline (Lambda Functions)";
        style=filled;
        fillcolor="#E8F4F8";
        color="#232F3E";
        fontcolor="#232F3E";
        fontsize=13;
        fontname="Arial Bold";
        margin=20;
        
        classifier [label="Classifier\\nLambda", fillcolor="#FF9900", fontcolor=white];
        extractor [label="Extractor\\nLambda", fillcolor="#FF9900", fontcolor=white];
        validator [label="Validator\\nLambda", fillcolor="#FF9900", fontcolor=white];
        risk_scorer [label="Risk Scorer\\nLambda", fillcolor="#FF9900", fontcolor=white];
        reporter [label="Reporter\\nLambda", fillcolor="#FF9900", fontcolor=white];
    }
    
    // AI/ML Services
    subgraph cluster_7 {
        label="AI/ML Services";
        style=filled;
        fillcolor="#E8F4F8";
        color="#232F3E";
        fontcolor="#232F3E";
        fontsize=13;
        fontname="Arial Bold";
        margin=20;
        
        textract [label="Textract\\n(OCR)", fillcolor="#FF9900", fontcolor=white];
        comprehend [label="Comprehend\\n(PII)", fillcolor="#FF9900", fontcolor=white];
        bedrock [label="Bedrock\\n(Claude)", fillcolor="#FF9900", fontcolor=white];
    }
    
    // Monitoring & Alerts
    subgraph cluster_8 {
        label="Monitoring & Alerts";
        style=filled;
        fillcolor="#E8F4F8";
        color="#232F3E";
        fontcolor="#232F3E";
        fontsize=13;
        fontname="Arial Bold";
        margin=20;
        
        cloudwatch [label="CloudWatch\\n(Logs)", fillcolor="#FF9900", fontcolor=white];
        sns [label="SNS\\n(Alerts)", fillcolor="#FF9900", fontcolor=white];
    }
    
    // Connections
    user -> frontend [label="Access", color="#232F3E"];
    frontend -> cloudfront [label="Serve", color="#232F3E"];
    cloudfront -> api_gateway [label="API Calls", color="#232F3E"];
    
    api_gateway -> cognito [label="Auth", color="#232F3E"];
    api_gateway -> api_lambda [label="Route", color="#232F3E"];
    
    api_lambda -> s3 [label="Upload", color="#232F3E"];
    s3 -> step_functions [label="Trigger", color="#232F3E"];
    
    step_functions -> classifier [label="Start", color="#232F3E"];
    classifier -> textract [label="Analyze", color="#232F3E"];
    textract -> extractor [label="Extract", color="#232F3E"];
    extractor -> comprehend [label="Detect", color="#232F3E"];
    extractor -> validator [label="Validate", color="#232F3E"];
    validator -> bedrock [label="Reason", color="#232F3E"];
    validator -> risk_scorer [label="Score", color="#232F3E"];
    risk_scorer -> reporter [label="Report", color="#232F3E"];
    
    classifier -> dynamodb_docs [label="Save", color="#232F3E"];
    extractor -> dynamodb_docs [label="Save", color="#232F3E"];
    reporter -> dynamodb_audits [label="Save", color="#232F3E"];
    
    reporter -> sns [label="Alert", color="#232F3E"];
    
    classifier -> cloudwatch [label="Log", color="#232F3E"];
    extractor -> cloudwatch [label="Log", color="#232F3E"];
    validator -> cloudwatch [label="Log", color="#232F3E"];
    risk_scorer -> cloudwatch [label="Log", color="#232F3E"];
    reporter -> cloudwatch [label="Log", color="#232F3E"];
    
    s3 -> kms [label="Encrypt", color="#232F3E"];
    dynamodb_docs -> kms [label="Encrypt", color="#232F3E"];
    dynamodb_audits -> kms [label="Encrypt", color="#232F3E"];
}
"""

# Write DOT file
dot_file = "auditflow-pro/architecture_diagram_detailed.dot"
with open(dot_file, 'w') as f:
    f.write(dot_content)

print("✓ Detailed DOT file created")

# Generate PNG
try:
    subprocess.run(['dot', '-Tpng', dot_file, '-o', 'auditflow-pro/architecture_diagram_detailed.png'], 
                   check=True, capture_output=True)
    print("✓ Detailed architecture diagram created!")
    print("✓ Saved as: auditflow-pro/architecture_diagram_detailed.png")
except Exception as e:
    print(f"Error: {e}")
