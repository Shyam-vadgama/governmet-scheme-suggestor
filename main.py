from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select
import uvicorn
import json
import os
from dotenv import load_dotenv

# Explicitly load .env from the module directory
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(current_dir, ".env")
load_dotenv(env_path)

from .database import create_db_and_tables, engine
from .models import Scheme
from .routers import auth, profile, documents, schemes

app = FastAPI(title="AI Eligibility & Scheme Recommendation Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/ui", StaticFiles(directory="frontend", html=True), name="frontend")

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(documents.router)
app.include_router(schemes.router)

def create_initial_data():
    with Session(engine) as session:
        existing = session.exec(select(Scheme)).first()
        if not existing:
            s1 = Scheme(
                name="Post Matric Scholarship",
                description="Financial assistance for SC/ST students.",
                target_group="student",
                benefits="Tuition fee waiver + Maintenance allowance",
                portal_url="https://scholarships.gov.in",
                rules=json.dumps({
                    "user_type": "student",
                    "max_income": 250000,
                    "category": ["SC", "ST"]
                }),
                required_documents=json.dumps(["Aadhaar", "Income Certificate", "Caste Certificate"])
            )
            s2 = Scheme(
                name="PM Kisan Samman Nidhi",
                description="Income support for all landholding farmers.",
                target_group="farmer",
                benefits="Rs 6000 per year",
                portal_url="https://pmkisan.gov.in",
                rules=json.dumps({
                    "user_type": "farmer",
                    "state": "Gujarat" # Example constraint
                }),
                required_documents=json.dumps(["Aadhaar", "Land Records", "Bank Passbook"])
            )
            
            session.add(s1)
            session.add(s2)
            session.commit()

@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    create_initial_data()

if __name__ == "__main__":
    uvicorn.run("eligibility_agent.main:app", host="0.0.0.0", port=8000, reload=True)
