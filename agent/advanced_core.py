import json
from typing import List
from models import Profile, Document, Scheme, DocumentStatus
from .llm_client import generate_json

# ---------------------------------------------------------
# 1. Structured Extraction Agent
# ---------------------------------------------------------

def smart_extract_document(file_content: str, doc_type: str) -> dict:
    """
    Extracts structured data from document text.
    """
    extraction_prompt = f"""
    You are a government document digitization agent. 
    Extract the following fields from the provided {doc_type} text.
    
    Return a JSON object with exactly these keys (value can be null if not found):
    - full_name (string)
    - dob (string, format YYYY-MM-DD)
    - id_number (string, e.g., Aadhaar/PAN/ID)
    - parent_name (string)
    - address_state (string)
    - address_district (string)
    - institution_name (string, for student IDs)
    - income (number, for income certs)
    
    Document Text:
    {file_content}
    """
    
    result = generate_json(extraction_prompt)
    if not result:
        return {"extraction_failed": True, "reason": "LLM Service Unavailable"}
    return result

# ---------------------------------------------------------
# 2. Verification & Reasoning Agent
# ---------------------------------------------------------

def verify_document_agentic(profile: Profile, doc_data: dict, doc_type: str) -> (DocumentStatus, str):
    """
    Uses an LLM to 'reason' about whether the document belongs to the profile user.
    """
    # 0. Check for upstream failure
    if doc_data.get("extraction_failed"):
        return DocumentStatus.PENDING, "Verification Skipped: Extraction Service Unavailable"

    # Construct a comparison context
    profile_summary = {
        "full_name": profile.full_name,
        "dob": profile.dob,
        "aadhaar": profile.aadhaar_number,
        "state": profile.state
    }
    
    prompt = f"""
    You are a strict Compliance Officer. Verify if the Document Data matches the User Profile.
    
    User Profile:
    {json.dumps(profile_summary)}
    
    Extracted Document Data ({doc_type}):
    {json.dumps(doc_data)}
    
    Rules:
    1. Names must match closely (ignore minor spelling/case differences).
    2. If ID numbers (Aadhaar) are present in both, they MUST match exactly.
    3. DOB must match exactly if present in both.
    4. Allow minor address variations.
    
    Return a JSON object:
    {{
        "is_valid": boolean,
        "reason": "string explaining why valid or invalid"
    }}
    """
    
    result = generate_json(prompt)
    
    if result and "is_valid" in result:
        if result["is_valid"]:
            return DocumentStatus.VALID, result.get("reason", "Verified")
        else:
            return DocumentStatus.INVALID, result.get("reason", "Mismatch")
    
    return DocumentStatus.PENDING, "Verification Service Unavailable"

# ---------------------------------------------------------
# 3. Eligibility Decision Agent
# ---------------------------------------------------------

def check_eligibility_agentic(profile: Profile, documents: List[Document], scheme: Scheme) -> (bool, str, List[str]):
    """
    Uses LLM to evaluate complex scheme rules against the profile.
    """
    # 1. Prepare Context
    profile_dict = profile.model_dump(exclude={'id', 'user_id'})
    doc_summary = [{"name": d.name, "status": d.status, "extracted": d.extracted_data} for d in documents]
    
    prompt = f"""
    You are a Government Scheme Eligibility Engine.
    Determine if the user is eligible for the scheme based on the provided Profile and Documents.
    
    Scheme Details:
    Name: {scheme.name}
    Target Group: {scheme.target_group}
    Rules (JSON/Text): {scheme.rules}
    Required Documents: {scheme.required_documents}
    
    User Profile:
    {json.dumps(profile_dict)}
    
    User Documents:
    {json.dumps(doc_summary)}
    
    Task:
    1. Check if Profile meets ALL Scheme Rules (Income, Category, State, Occupation).
    2. Check if REQUIRED documents are present AND have status 'valid'.
    
    Return JSON:
    {{
        "eligible": boolean,
        "reason": "Clear explanation of why eligible or not",
        "missing_documents": ["List", "of", "missing/invalid", "doc", "names"]
    }}
    """
    
    result = generate_json(prompt)
    if result:
        return result.get("eligible", False), result.get("reason", "Unknown"), result.get("missing_documents", [])
    
    return False, "Eligibility Service Unavailable", []