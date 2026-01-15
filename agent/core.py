import json
import os
import re
from datetime import datetime
from difflib import SequenceMatcher
import google.generativeai as genai
from models import Profile, Document, Scheme, DocumentStatus

# Configure Gemini if key is available
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# --- Helper Functions for Robust Matching ---

def normalize_name(name):
    """
    Normalizes name: lowercase, strip spaces, remove punctuation.
    """
    if not name: return ""
    # Lowercase and strip
    name = name.lower().strip()
    # Normalize internal spaces
    name = " ".join(name.split())
    # Remove punctuation (keep spaces)
    name = re.sub(r'[^\w\s]', '', name)
    return name

def names_match(n1, n2):
    """
    Checks if names match using multiple strategies:
    1. Exact Match (Normalized)
    2. Token Set Match (Order Agnostic)
    3. Fuzzy Match (Levenshtein Ratio > 0.85)
    """
    n1_clean = normalize_name(n1)
    n2_clean = normalize_name(n2)
    
    if not n1_clean or not n2_clean:
        return False

    # 1. Exact match
    if n1_clean == n2_clean:
        return True
        
    # 2. Token Set Match (Order Agnostic)
    # e.g., "Shyam Vadgama" == "Vadgama Shyam"
    t1 = set(n1_clean.split())
    t2 = set(n2_clean.split())
    if t1 == t2:
        return True
    
    # Check if one is a subset of another (e.g. missing middle name)
    # "Shyam Nileshbhai Vadgama" vs "Shyam Vadgama"
    if t1.issubset(t2) or t2.issubset(t1):
        # Only if the subset is significant (more than just common words)
        # But for now, let's assume valid
        pass # Moving to fuzzy check might be safer or accept here?
        # Let's rely on fuzzy for partials or return True if explicitly desired.
        # Strict subset might be risky ("Shyam" vs "Shyam Kumar"), so let's stick to fuzzy.

    # 3. Fuzzy Match (SequenceMatcher)
    # Handle typos: "Nileshbhai" vs "nileshhai"
    ratio = SequenceMatcher(None, n1_clean, n2_clean).ratio()
    if ratio > 0.85: # 85% similarity threshold
        return True
        
    return False

def parse_date(date_str):
    """
    Parses date string into a date object using common formats.
    """
    if not date_str: return None
    formats = [
        "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", 
        "%d.%m.%Y", "%Y.%m.%d", "%d %b %Y", "%d %B %Y",
        "%d-%m-%y", "%m/%d/%Y"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    return None

def dates_match(d1_str, d2_str):
    """
    Compares two date strings by parsing them first.
    """
    d1 = parse_date(d1_str)
    d2 = parse_date(d2_str)
    
    if d1 and d2:
        return d1 == d2
    
    # Fallback to direct string comparison if parsing fails
    return d1_str.strip() == d2_str.strip()

# --- Main Functions ---

def extract_data_from_document(file_content: str, doc_type: str) -> dict:
    """
    Uses GenAI to extract structured data from document text/OCR.
    """
    if not GOOGLE_API_KEY:
        # Mock behavior for testing without key
        print("No Google API Key found. Returning mock data.")
        return {"full_name": "Test User", "aadhaar_number": "123456789012"}

    model = genai.GenerativeModel('gemini-pro')
    prompt = f"""
    You are a strict data extraction engine.
    Extract the following fields from this {doc_type} text as a JSON object:
    - full_name
    - dob (YYYY-MM-DD)
    - id_number (if Aadhaar or PAN or College ID)
    - institution_name (if academic)
    - income (if income certificate)
    
    Return ONLY valid JSON.
    
    Document Text:
    {file_content}
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text.replace("```json", "").replace("```", "")
        return json.loads(text)
    except Exception as e:
        print(f"Error extracting data: {e}")
        return {}

def validate_document_against_profile(profile: Profile, doc_data: dict, doc_type: str) -> (DocumentStatus, str):
    """
    Compares extracted document data against the user's profile.
    Returns (Status, Message).
    """
    mismatches = []
    
    # 1. Name Check (Robust)
    if "full_name" in doc_data and doc_data["full_name"]:
        if not names_match(doc_data["full_name"], profile.full_name):
            mismatches.append(f"Name mismatch: Doc has '{doc_data['full_name']}', Profile has '{profile.full_name}'")

    # 2. DOB Check (Robust)
    if "dob" in doc_data and doc_data["dob"] and profile.dob:
        if not dates_match(doc_data["dob"], profile.dob):
             mismatches.append(f"DOB mismatch: Doc has '{doc_data['dob']}', Profile has '{profile.dob}'")

    # 3. ID Check
    if "id_number" in doc_data and doc_data["id_number"]:
        if "aadhaar" in doc_type.lower() and profile.aadhaar_number:
            # Clean spaces/dashes from Aadhaar
            doc_id = doc_data["id_number"].replace(" ", "").replace("-", "")
            prof_id = profile.aadhaar_number.replace(" ", "").replace("-", "")
            if doc_id != prof_id:
                mismatches.append(f"Aadhaar mismatch")
    
    # 4. Income Check logic (optional tolerance)
    if "income" in doc_data and doc_data["income"] and profile.income:
        try:
            doc_inc = float(doc_data["income"])
            # Example: Profile says 50k, Doc says 500k -> Mismatch
            if abs(doc_inc - profile.income) > 5000: # 5000 tolerance
                 mismatches.append(f"Income mismatch: Doc has {doc_inc}, Profile has {profile.income}")
        except:
            pass

    if mismatches:
        return DocumentStatus.INVALID, "; ".join(mismatches)
    
    return DocumentStatus.VALID, "Verified"

def check_scheme_eligibility(profile: Profile, documents: list[Document], scheme: Scheme) -> (bool, str, list[str]):
    """
    Checks if a user is eligible for a scheme based on:
    1. Profile attributes (Income, Category, etc.)
    2. Document presence and validity
    
    Returns (Eligible, Reason, MissingDocs)
    """
    rules = json.loads(scheme.rules)
    req_docs = json.loads(scheme.required_documents)
    
    # 1. Profile Rule Checks
    if "user_type" in rules and rules["user_type"] != profile.user.user_type:
        return False, f"Scheme only for {rules['user_type']}", []
    
    if "max_income" in rules and profile.income:
        if profile.income > rules["max_income"]:
            return False, f"Income {profile.income} exceeds limit {rules['max_income']}", []

    if "category" in rules and profile.category:
        if profile.category not in rules["category"]:
            return False, f"Category {profile.category} not eligible", []

    if "state" in rules and profile.state:
        if profile.state.lower() != rules["state"].lower():
             return False, f"Only for residents of {rules['state']}", []

    # 2. Document Checks
    missing_docs = []
    # Create a map of Valid documents
    # we normalize doc names for comparison (simple approach)
    valid_docs_names = [d.name.lower() for d in documents if d.status == DocumentStatus.VALID]
    
    for req in req_docs:
        # Check if we have a valid doc that "contains" the required name (fuzzy match)
        # e.g. req="Aadhaar", valid="Aadhaar Card" -> match
        found = False
        for vd in valid_docs_names:
            if req.lower() in vd:
                found = True
                break
        if not found:
            missing_docs.append(req)
            
    if missing_docs:
        return False, "Missing or Invalid required documents", missing_docs
        
    return True, "Eligible", []
