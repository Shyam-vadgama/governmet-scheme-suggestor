from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from typing import List
from ..database import get_session
from ..models import User, Scheme
from ..schemas import SchemeRead
from ..dependencies import get_current_user
from ..agent.advanced_core import check_eligibility_agentic
from ..agent.researcher import search_and_extract_schemes
from ..agent.action_taker import generate_application_kit
from fastapi.responses import FileResponse
import os

router = APIRouter(prefix="/schemes", tags=["schemes"])

@router.post("/discover", response_model=List[SchemeRead])
def discover_schemes(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    if not current_user.profile:
        return []
        
    # Create a summary string for search
    p = current_user.profile
    summary = f"{p.user.user_type} in {p.state} {p.district} income {p.income}"
    
    # 1. Run Search Agent
    new_schemes = search_and_extract_schemes(summary)
    
    # 2. Save new schemes to DB (deduplicate by name)
    saved = []
    for scheme in new_schemes:
        existing = session.exec(select(Scheme).where(Scheme.name == scheme.name)).first()
        if not existing:
            session.add(scheme)
            saved.append(scheme)
    session.commit()
    
    # Return all schemes (new + old)
    return get_schemes(current_user, session)

@router.post("/{scheme_id}/apply")
def apply_scheme(scheme_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    scheme = session.get(Scheme, scheme_id)
    if not scheme:
        return {"error": "Scheme not found"}
        
    filename = generate_application_kit(current_user.profile, scheme, current_user.documents)
    file_path = os.path.join("eligibility_agent", "static_exports", filename)
    
    return FileResponse(file_path, media_type='application/pdf', filename=filename)

@router.get("/", response_model=List[SchemeRead])
def get_schemes(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    schemes = session.exec(select(Scheme)).all()
    results = []
    
    # If no profile, all ineligible
    if not current_user.profile:
        for s in schemes:
            results.append(SchemeRead(
                id=s.id, name=s.name, description=s.description, 
                benefits=s.benefits, portal_url=s.portal_url,
                is_eligible=False, reason="Profile missing", missing_documents=[]
            ))
        return results

    documents = current_user.documents
    
    for s in schemes:
        eligible, reason, missing = check_eligibility_agentic(current_user.profile, documents, s)
        results.append(SchemeRead(
            id=s.id,
            name=s.name,
            description=s.description,
            benefits=s.benefits,
            portal_url=s.portal_url,
            is_eligible=eligible,
            reason=reason,
            missing_documents=missing
        ))
        
    return results
