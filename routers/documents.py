from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlmodel import Session, select
from typing import List
import json
from ..database import get_session
from ..models import User, Document, DocumentStatus
from ..schemas import DocumentRead, DocumentUpdate
from ..dependencies import get_current_user
from ..agent.advanced_core import smart_extract_document, verify_document_agentic
from ..agent.core import validate_document_against_profile # Fallback deterministic verification

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("/upload", response_model=DocumentRead)
async def upload_document(
    name: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if not current_user.profile:
        raise HTTPException(status_code=400, detail="Complete your profile before uploading documents.")

    content = await file.read()
    
    try:
        text_content = content.decode("utf-8")
    except:
        text_content = f"[Binary File: {file.filename}]"

    # Agent Step 1: Advanced Extraction
    extracted_data = smart_extract_document(text_content, name)
    
    # Agent Step 2: Advanced Verification
    status, message = verify_document_agentic(current_user.profile, extracted_data, name)
    
    # Save to DB
    doc = Document(
        user_id=current_user.id,
        name=name,
        file_path=file.filename, 
        status=status,
        validation_message=message,
        extracted_data=json.dumps(extracted_data)
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)
    
    return doc

@router.get("/", response_model=List[DocumentRead])
def get_documents(current_user: User = Depends(get_current_user)):
    return current_user.documents

@router.delete("/{doc_id}")
def delete_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    doc = session.get(Document, doc_id)
    if not doc or doc.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Document not found")
    
    session.delete(doc)
    session.commit()
    return {"message": "Document deleted"}

@router.put("/{doc_id}", response_model=DocumentRead)
def update_document(
    doc_id: int,
    update_data: DocumentUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    doc = session.get(Document, doc_id)
    if not doc or doc.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Update fields if provided
    if update_data.name:
        doc.name = update_data.name
        
    # Construct manual extracted data
    current_extracted = {}
    if doc.extracted_data:
        try:
            current_extracted = json.loads(doc.extracted_data)
        except:
            current_extracted = {}
            
    # Merge updates
    if update_data.full_name:
        current_extracted["full_name"] = update_data.full_name
    if update_data.dob:
        current_extracted["dob"] = update_data.dob
    if update_data.id_number:
        current_extracted["id_number"] = update_data.id_number
        
    doc.extracted_data = json.dumps(current_extracted)
    
    # Re-verify using Deterministic Logic (agent.core)
    # We bypass the Agentic one because the user is manually overriding the extracted data,
    # so we trust their input as "extracted" and just check if it matches profile.
    status, message = validate_document_against_profile(current_user.profile, current_extracted, doc.name)
    
    doc.status = status
    doc.validation_message = message
    
    session.add(doc)
    session.commit()
    session.refresh(doc)
    
    return doc