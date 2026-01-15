from typing import Optional, List
from pydantic import BaseModel
from .models import UserType, DocumentStatus

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserCreate(BaseModel):
    username: str
    password: str
    user_type: UserType

class UserRead(BaseModel):
    id: int
    username: str
    user_type: UserType

class ProfileUpdate(BaseModel):
    # Common
    full_name: str
    dob: Optional[str] = None
    gender: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    aadhaar_number: Optional[str] = None
    mobile_number: Optional[str] = None
    bank_account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    income: Optional[float] = None

    # Student
    college_name: Optional[str] = None
    university: Optional[str] = None
    course_name: Optional[str] = None
    course_type: Optional[str] = None
    year_of_study: Optional[int] = None
    enrollment_number: Optional[str] = None
    category: Optional[str] = None

    # Farmer
    land_ownership: Optional[str] = None
    land_size: Optional[float] = None
    crop_type: Optional[str] = None

class DocumentRead(BaseModel):
    id: int
    name: str
    status: DocumentStatus
    validation_message: Optional[str] = None
    extracted_data: Optional[str] = None # Added this to read back data

class DocumentUpdate(BaseModel):
    name: Optional[str] = None
    # We will receive the JSON string or dictionary for extracted data
    # But for simplicity, let's accept specific fields to construct the JSON
    full_name: Optional[str] = None
    dob: Optional[str] = None
    id_number: Optional[str] = None

class SchemeRead(BaseModel):
    id: int
    name: str
    description: str
    benefits: str
    portal_url: str
    is_eligible: bool = False
    reason: Optional[str] = None
    missing_documents: List[str] = []