from fpdf import FPDF
from ..models import Profile, Scheme, Document
import json
import os

class ApplicationPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Scheme Application Kit', 0, 1, 'C')
        self.ln(10)

def generate_application_kit(profile: Profile, scheme: Scheme, documents: list[Document]) -> str:
    """
    Generates a PDF Application Kit including:
    1. Cover Letter
    2. Document Checklist
    3. Step-by-Step Guide
    """
    pdf = ApplicationPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # 1. Cover Letter
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, f"Application for {scheme.name}", 0, 1)
    pdf.ln(5)
    
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, f"To,\nThe Authority,\n{scheme.name} Department.\n\nSubject: Application for {scheme.name}\n\nRespected Sir/Madam,\n\nI, {profile.full_name}, am writing to formally apply for the {scheme.name}. I meet the eligibility criteria as a {profile.user.user_type} residing in {profile.state}.\n\nPlease find attached my supporting documents for your verification.\n\nSincerely,\n{profile.full_name}\nMobile: {profile.mobile_number or 'N/A'}")
    
    pdf.ln(10)
    
    # 2. Document Checklist
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Document Checklist", 0, 1)
    pdf.set_font("Arial", size=12)
    
    req_docs = json.loads(scheme.required_documents)
    user_docs = [d.name.lower() for d in documents if d.status == "valid"]
    
    for doc in req_docs:
        status = "[X]"
        for ud in user_docs:
            if doc.lower() in ud:
                status = "[/]" # Checked
                break
        pdf.cell(0, 10, f"{status} {doc}", 0, 1)
        
    pdf.ln(10)
    
    # 3. Next Steps
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Next Steps", 0, 1)
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, f"1. Print this letter.\n2. Attach photocopies of the checked documents.\n3. Visit the official portal: {scheme.portal_url}\n4. Submit this application.")
    
    # Save
    filename = f"Application_Kit_{profile.id}_{scheme.id}.pdf"
    output_path = os.path.join("eligibility_agent", "static_exports", filename)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    pdf.output(output_path)
    return filename
