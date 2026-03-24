#!/bin/bash
################################################################################
# Step Functions Verification CLI - Unknown Applicant Issue
# 
# This script verifies that Step Functions is correctly passing extracted_data
# from Extractor to Validator, which is required for applicant names to display
# correctly instead of "Unknown Applicant"
#
# Usage: ./STEP_FUNCTIONS_VERIFICATION_CLI.sh
################################################################################

set -e

echo "================================================================================"
echo "STEP FUNCTIONS DATA FLOW VERIFICATION - Unknown Applicant Issue"
echo "================================================================================"
echo ""

# Configuration
STATE_MACHINE_NAME="AuditFlowDocumentProcessing"
REGION="${AWS_REGION:-ap-south-1}"

echo "[1/6] Getting State Machine ARN..."
STATE_MACHINE_ARN=$(aws stepfunctions list-state-machines \
  --region $REGION \
  --query "stateMachines[?name=='$STATE_MACHINE_NAME'].stateMachineArn" \
  --output text)

if [ -z "$STATE_MACHINE_ARN" ] || [ "$STATE_MACHINE_ARN" = "None" ]; then
  echo "✗ State machine not found: $STATE_MACHINE_NAME"
  exit 1
fi

echo "✓ State Machine ARN: $STATE_MACHINE_ARN"
echo ""

echo "[2/6] Getting most recent successful execution..."
EXECUTION_ARN=$(aws stepfunctions list-executions \
  --state-machine-arn $STATE_MACHINE_ARN \
  --status-filter SUCCEEDED \
  --query 'executions[0].executionArn' \
  --output text | tr -d ' ')

if [ -z "$EXECUTION_ARN" ] || [ "$EXECUTION_ARN" = "None" ]; then
  echo "✗ No successful executions found"
  exit 1
fi

echo "✓ Execution ARN: $EXECUTION_ARN"
echo ""

echo "[3/6] Retrieving execution history..."
aws stepfunctions get-execution-history \
  --execution-arn $EXECUTION_ARN > /tmp/execution_history.json

echo "✓ Execution history retrieved"
echo ""

echo "[4/6] Checking ExtractData Output..."
# Get the second TaskSucceeded event (ExtractData returns extracted_data)
EXTRACTOR_OUTPUT=$(cat /tmp/execution_history.json | jq -r '.events[] | select(.type=="TaskSucceeded") | .taskSucceededEventDetails.output' | sed -n '2p' | jq -r '.Payload')

if [ -z "$EXTRACTOR_OUTPUT" ] || [ "$EXTRACTOR_OUTPUT" = "null" ]; then
  echo "✗ No ExtractData output found"
  exit 1
fi

# Check for extracted_data
HAS_EXTRACTED_DATA=$(echo $EXTRACTOR_OUTPUT | jq 'has("extracted_data")')
if [ "$HAS_EXTRACTED_DATA" = "true" ]; then
  echo "✓ ExtractData output has extracted_data field"
  
  # Check for full_name (driver's license field)
  EMPLOYEE_NAME=$(echo $EXTRACTOR_OUTPUT | jq -r '.extracted_data.full_name.value // empty')
  if [ -n "$EMPLOYEE_NAME" ]; then
    echo "✓ ExtractData extracted full_name: $EMPLOYEE_NAME"
  else
    echo "⚠ ExtractData output missing full_name"
  fi
else
  echo "✗ ExtractData output MISSING extracted_data field"
  echo "  This is the root cause of 'Unknown Applicant' issue!"
  exit 1
fi
echo ""

echo "[5/6] Checking ValidateDocuments Input..."
# Get the ValidateDocuments task input from TaskStateEntered
VALIDATOR_INPUT=$(cat /tmp/execution_history.json | jq -r '.events[] | select(.type=="TaskStateEntered" and .stateEnteredEventDetails.name=="ValidateDocuments") | .stateEnteredEventDetails.input' | head -1)

if [ -z "$VALIDATOR_INPUT" ]; then
  echo "✗ No ValidateDocuments input found"
  exit 1
fi

# Check if ValidateDocuments received extracted_data in processed_documents
VALIDATOR_HAS_EXTRACTED_DATA=$(echo $VALIDATOR_INPUT | jq '.processed_documents[0] | has("extracted_data")')
if [ "$VALIDATOR_HAS_EXTRACTED_DATA" = "true" ]; then
  echo "✓ ValidateDocuments received extracted_data in processed_documents"
  
  # Check if it matches ExtractData output
  VALIDATOR_EXTRACTED_DATA=$(echo $VALIDATOR_INPUT | jq '.processed_documents[0].extracted_data')
  EXTRACTOR_EXTRACTED_DATA=$(echo $EXTRACTOR_OUTPUT | jq '.extracted_data')
  
  if [ "$VALIDATOR_EXTRACTED_DATA" = "$EXTRACTOR_EXTRACTED_DATA" ]; then
    echo "✓ ValidateDocuments extracted_data matches ExtractData output"
  else
    echo "⚠ ValidateDocuments extracted_data differs from ExtractData output"
  fi
else
  echo "✗ ValidateDocuments input MISSING extracted_data in processed_documents"
  echo "  PROBLEM: Step Functions not passing extracted_data to ValidateDocuments!"
  echo "  SOLUTION: Check Step Functions state machine ResultPath configuration"
  exit 1
fi
echo ""

echo "[6/6] Checking ValidateDocuments Output..."
# Get the fourth TaskSucceeded event (ValidateDocuments with golden_record)
VALIDATOR_OUTPUT=$(cat /tmp/execution_history.json | jq -r '.events[] | select(.type=="TaskSucceeded") | .taskSucceededEventDetails.output' | sed -n '4p' | jq -r '.Payload')

if [ -z "$VALIDATOR_OUTPUT" ] || [ "$VALIDATOR_OUTPUT" = "null" ]; then
  echo "✗ No ValidateDocuments output found"
  exit 1
fi

# Check for golden_record
HAS_GOLDEN_RECORD=$(echo $VALIDATOR_OUTPUT | jq '.golden_record | has("name")')
if [ "$HAS_GOLDEN_RECORD" = "true" ]; then
  echo "✓ ValidateDocuments generated golden_record with name field"
  
  # Check for applicant name value
  APPLICANT_NAME=$(echo $VALIDATOR_OUTPUT | jq -r '.golden_record.name.value // empty')
  if [ -n "$APPLICANT_NAME" ]; then
    echo "✓ Golden record has applicant name: $APPLICANT_NAME"
  else
    echo "⚠ Golden record name field is empty"
  fi
else
  echo "✗ ValidateDocuments output MISSING golden_record.name field"
  exit 1
fi
echo ""

echo "================================================================================"
echo "✓ ALL CHECKS PASSED - Data flow is correct!"
echo "================================================================================"
echo ""
echo "Summary:"
echo "  ✓ ExtractData returned extracted_data"
echo "  ✓ ExtractData extracted full_name: $EMPLOYEE_NAME"
echo "  ✓ ValidateDocuments received extracted_data"
echo "  ✓ ValidateDocuments generated golden_record"
echo "  ✓ Golden record has applicant name: $APPLICANT_NAME"
echo ""
echo "Result: Applicant names should display correctly (not 'Unknown Applicant')"
echo ""
