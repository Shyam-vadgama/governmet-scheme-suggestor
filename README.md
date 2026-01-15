# AI Eligibility & Scheme Recommendation Agent

An intelligent agent that verifies user profiles against uploaded documents and recommends government schemes.

## Features
- **Agentic Document Analysis**: Uses Google Gemini to extract data from uploaded documents.
- **Strict Validation**: Compares extracted document data with user profile data (Name, DOB, Income).
- **Rule Engine**: Deterministic eligibility checks based on profile and document validity.
- **Role Based**: Supports Students, Farmers, etc.

## Setup
1. `pip install -r requirements.txt`
2. Set `GOOGLE_API_KEY` in environment (optional, mock data used if missing).
3. Run: `uvicorn eligibility_agent.main:app --reload`

## API Usage
- **Auth**: `/auth/register`, `/auth/token`
- **Profile**: `PUT /profile` to set up your data.
- **Documents**: `POST /documents/upload` to upload evidence (e.g., text files simulating OCR'd docs).
- **Schemes**: `GET /schemes` to see what you qualify for.
