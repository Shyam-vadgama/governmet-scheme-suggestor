from fastapi import APIRouter, Depends, BackgroundTasks
from sqlmodel import Session, select
from database import get_session
from models import User, Profile, Scheme
from schemas import ProfileUpdate
from dependencies import get_current_user
from agent.researcher import search_and_extract_schemes

router = APIRouter(prefix="/profile", tags=["profile"])

def background_discovery(profile: Profile, session: Session):
    """
    Background task to discover schemes based on new profile data.
    """
    summary = f"{profile.user.user_type} in {profile.state} {profile.district} income {profile.income}"
    new_schemes = search_and_extract_schemes(summary)
    
    for scheme in new_schemes:
        # Use a new session block or ensure thread safety if needed, 
        # but here we are in a simple sync function run in threadpool
        # We need a fresh session for the background thread usually, 
        # but passing the generator's session might be risky if closed.
        # Best to create a new session here.
        from database import engine
        with Session(engine) as bg_session:
            existing = bg_session.exec(select(Scheme).where(Scheme.name == scheme.name)).first()
            if not existing:
                bg_session.add(scheme)
                bg_session.commit()

@router.get("/")
def get_profile(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    if not current_user.profile:
        return {}
    return current_user.profile

@router.put("/")
def update_profile(
    profile_data: ProfileUpdate, 
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user), 
    session: Session = Depends(get_session)
):
    db_profile = current_user.profile
    if not db_profile:
        db_profile = Profile(user_id=current_user.id, **profile_data.dict(exclude_unset=True))
        session.add(db_profile)
    else:
        profile_dict = profile_data.dict(exclude_unset=True)
        for key, value in profile_dict.items():
            setattr(db_profile, key, value)
        session.add(db_profile)
    
    session.commit()
    session.refresh(db_profile)
    
    # Trigger AI Discovery in Background
    background_tasks.add_task(background_discovery, db_profile, session)
    
    return db_profile