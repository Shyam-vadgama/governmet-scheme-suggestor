from typing import Optional, List
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship, JSON
from enum import Enum

class UserType(str, Enum):
    STUDENT = "student"
    FARMER = "farmer"
    UNEMPLOYED = "unemployed"
    WORKER = "worker"
    OTHER = "other"

class DocumentStatus(str, Enum):
    PENDING = "pending" # Not uploaded
    UPLOADED = "uploaded" # Uploaded, waiting processing
    VALID = "valid" # Verified and matches profile
    INVALID = "invalid" # Verified but mismatch or fake
    MISSING = "missing" # Explicitly flagged as missing for a scheme

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    hashed_password: str
    user_type: UserType
    
    profile: Optional["Profile"] = Relationship(back_populates="user")
    documents: List["Document"] = Relationship(back_populates="user")

class Profile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    
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
    income: Optional[float] = None # Annual family income

    # Student Specific
    college_name: Optional[str] = None
    university: Optional[str] = None
    course_name: Optional[str] = None
    course_type: Optional[str] = None # UG/PG/etc
    year_of_study: Optional[int] = None
    enrollment_number: Optional[str] = None
    category: Optional[str] = None # General/OBC/etc
    
    # Farmer Specific
    land_ownership: Optional[str] = None
    land_size: Optional[float] = None
    crop_type: Optional[str] = None
    
    user: User = Relationship(back_populates="profile")

class Document(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    name: str # e.g., "Aadhaar Card", "Income Certificate"
    file_path: Optional[str] = None
    status: DocumentStatus = Field(default=DocumentStatus.PENDING)
    validation_message: Optional[str] = None # "Name mismatch", "Expired", etc.
    extracted_data: Optional[str] = Field(default=None) # JSON string of data extracted by Agent
    
    user: User = Relationship(back_populates="documents")

class Scheme(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: str
    target_group: str # student, farmer
    benefits: str
    portal_url: str
    
    # Eligibility Rules (stored as JSON for flexibility in this demo)
    # e.g. {"income_limit": 50000, "category": ["SC", "ST"]}
    rules: str = Field(default="{}") 
    required_documents: str = Field(default="[]") # JSON list of doc names ["Aadhaar", "Income Cert"]

