# AuditFlow-Pro


# Team information

#  Team name
AuditFlow Pro

# Project information

Which category best describes your idea?
Workplace Efficiency

# In one or two sentences, what's your big idea?

Our project is an AI-powered Pre-Auditor that automatically extracts, cross-references, and validates data across multiple loan documents, such as IDs, bank statements, and tax forms, to flag inconsistencies before they reach human underwriters. It transforms a manual, error-prone checklist into a real-time digital dashboard.

# Tell us about your vision. What exactly will you build?

We are building the Automated Loan Document Auditor, a serverless application that acts as a quality-control gate for lending teams. When a loan officer uploads a document package, the system performs four core functions. First, it extracts and classifies documents to identify if they are W2s, driver's licenses, or bank statements. Second, it validates the data by matching names, addresses, and income figures across all files to find discrepancies. Third, it generates alerts, including a Confidence Score and a Risk Report that highlights exactly where information does not match or where handwriting is illegible. Finally, it presents these insights through an Underwriter Dashboard, a clean interface built with React that organizes findings for immediate action.

# How will your solution make a difference?

Currently, bank employees spend hours manually comparing documents, which leads to fatigue and missed errors. Our solution provides three major benefits. For Employees, it reduces manual data entry by 80 percent, allowing them to focus on high-value risk assessment rather than clerical work. For the Bank, it drastically lowers the risk of compliance fines and fraudulent applications by ensuring 100 percent of documents are audited, not just a sample. For Customers, it speeds up loan approval times from days to hours by removing the administrative bottleneck.

# What's your game plan for building this?

We will use Kiro's Spec-Driven Development to move from idea to deployment through five key stages. First, we will define requirements by using Kiro to generate a document that defines the Golden Record matching logic. Second, we will design a serverless architectural flow using Amazon S3 for storage, Lambda for triggers, Textract for extraction, Bedrock for analysis, and DynamoDB for results. Third, we will handle core feature implementation by using Kiro's agentic chat to scaffold the functions required for multi-page PDF processing. Fourth, we will focus on security integration by prompting Kiro to write IAM policies and encryption settings to ensure banking data is handled securely at-rest and in-transit. Finally, we will manage iteration by using Kiro Agent Hooks to automatically run unit tests every time we update the document extraction logic.

# Which AWS AI services will power your solution?
Amazon Bedrock, Kiro

# What other AWS Free Tier Services will you employ?
Amazon Textract, Amazon Comprehend, AWS Lambda, Amazon S3, Amazon DynamoDB, AWS Amplify Hosting











Architecture Flow Diagram



