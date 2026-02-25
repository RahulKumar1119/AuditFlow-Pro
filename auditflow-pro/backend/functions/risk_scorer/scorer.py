# backend/functions/risk_scorer/scorer.py

import logging
from typing import List, Dict, Tuple, Any

logger = logging.getLogger(__name__)

def calculate_inconsistency_score(inconsistencies: List[Dict[str, Any]]) -> Tuple[int, List[Dict[str, Any]]]:
    """
    Task 9.2: Implement inconsistency-based scoring.
    Assigns specific point values based on the field and severity of the mismatch.
    Returns a tuple containing the total inconsistency score and a list of risk factor details.
    """
    score = 0
    factors = []
    
    for inc in inconsistencies:
        field = inc.get("field", "").lower()
        severity = inc.get("severity", "LOW")
        description = inc.get("description", "Unknown inconsistency")
        
        points = 0
        # Point allocations based on requirements
        if "name" in field:
            points = 15
        elif "address" in field:
            points = 20
        elif "income" in field:
            points = 25 if severity == "HIGH" else 15
        elif field in ["ssn", "date_of_birth", "document_number"]:
            points = 30
            
        if points > 0:
            score += points
            factors.append({
                "factor_type": "INCONSISTENCY",
                "field": field,
                "points_added": points,
                "description": f"{points} pts: {description}"
            })
            
    return score, factors

def calculate_extraction_quality_score(golden_record: Dict[str, Any], documents: List[Dict[str, Any]]) -> Tuple[int, List[Dict[str, Any]]]:
    """
    Task 9.3: Implement extraction quality scoring.
    Penalizes the application for low confidence data extractions or poor document quality.
    """
    score = 0
    factors = []
    
    # 1. Add 10 points per field with confidence < 80%
    for field, data in golden_record.items():
        if data.get("confidence", 100.0) < 80.0:
            points = 10
            score += points
            factors.append({
                "factor_type": "LOW_CONFIDENCE",
                "field": field,
                "points_added": points,
                "description": f"{points} pts: Low extraction confidence ({data.get('confidence')}%) for {field}."
            })
            
    # 2. Add 5 points per illegible or low-quality page/document
    for doc in documents:
        # Check if the document classifier or extractor flagged it for manual review
        if doc.get("status") == "LOW_QUALITY" or doc.get("requires_manual_review") is True:
            points = 5
            score += points
            factors.append({
                "factor_type": "POOR_DOCUMENT_QUALITY",
                "document_id": doc.get("document_id"),
                "points_added": points,
                "description": f"{points} pts: Document {doc.get('document_id')} flagged as low quality or requires manual review."
            })
            
    return score, factors

def determine_risk_level(total_score: int) -> str:
    """
    Task 9.4: Assign risk levels based on the numerical score.
    """
    if total_score <= 24:
        return "LOW"
    elif total_score <= 49:
        return "MEDIUM"
    elif total_score <= 79:
        return "HIGH"
    else:
        return "CRITICAL"

def calculate_total_risk(inconsistencies: List[Dict[str, Any]], golden_record: Dict[str, Any], documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Task 9.4 & 9.5: Orchestrates the scoring process, caps the maximum score, 
    and returns the structured risk assessment.
    """
    # Get scores from both categories
    inc_score, inc_factors = calculate_inconsistency_score(inconsistencies)
    qual_score, qual_factors = calculate_extraction_quality_score(golden_record, documents)
    
    raw_score = inc_score + qual_score
    all_factors = inc_factors + qual_factors
    
    # Cap risk score at 100
    final_score = min(raw_score, 100)
    risk_level = determine_risk_level(final_score)
    
    logger.info(f"Calculated Risk Score: {final_score} ({risk_level}). Raw score before capping: {raw_score}")
    
    return {
        "risk_score": final_score,
        "raw_score": raw_score, 
        "risk_level": risk_level,
        "is_high_risk": final_score > 50, # Flag applications as high-risk when score > 50
        "risk_factors": all_factors
    }
