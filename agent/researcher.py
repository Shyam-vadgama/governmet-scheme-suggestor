import json
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS
from models import Scheme
from .llm_client import generate_json

def search_and_extract_schemes(user_profile_summary: str) -> list[Scheme]:
    """
    1. Searches the web for schemes matching the profile.
    2. Scrapes top results.
    3. Uses LLM (Gemini/OpenRouter) to extract Scheme objects.
    """
    # 1. Search
    query = f"latest government schemes for {user_profile_summary} india official apply online"
    print(f"Researcher: Searching for '{query}'...")
    
    results = []
    try:
        with DDGS() as ddgs:
            # Get top 5 results
            ddgs_gen = ddgs.text(query, max_results=5)
            results = [r for r in ddgs_gen]
    except Exception as e:
        print(f"Search failed: {e}")
        return []

    found_schemes = []
    
    # 2. Scrape & Extract
    for res in results:
        url = res['href']
        print(f"Researcher: Scraping {url}...")
        try:
            page = requests.get(url, timeout=10)
            soup = BeautifulSoup(page.content, 'html.parser')
            # Get main text, limit length to avoid token limits
            text_content = soup.get_text(separator=' ', strip=True)[:10000]
            
            prompt = f"""
            You are a Government Scheme Researcher.
            Analyze the text from this website: {url}
            
            Extract any GOVERNMENT SCHEMES mentioned.
            Return a list of JSON objects with this EXACT schema:
            [
                {{
                    "name": "Scheme Name",
                    "description": "Short description",
                    "target_group": "student/farmer/worker/etc",
                    "benefits": "Key benefits",
                    "portal_url": "{url}",
                    "rules": {{ "income_limit": number, "state": "string", "category": "string" }},
                    "required_documents": ["Doc 1", "Doc 2"]
                }}
            ]
            
            If no specific scheme is found, return [].
            
            Web Content:
            {text_content}
            """
            
            schemes_data = generate_json(prompt)
            
            if isinstance(schemes_data, list):
                for s_data in schemes_data:
                    # Convert dict rules/docs to string for DB
                    scheme = Scheme(
                        name=s_data.get("name", "Unknown Scheme"),
                        description=s_data.get("description", ""),
                        target_group=s_data.get("target_group", "other"),
                        benefits=s_data.get("benefits", ""),
                        portal_url=s_data.get("portal_url", url),
                        rules=json.dumps(s_data.get("rules", {})),
                        required_documents=json.dumps(s_data.get("required_documents", []))
                    )
                    found_schemes.append(scheme)
            
        except Exception as e:
            print(f"Failed to process {url}: {e}")
            continue
            
    return found_schemes