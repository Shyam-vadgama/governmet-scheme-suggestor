import os
import json
import re
import requests
from google import genai
from google.genai import types
from openai import OpenAI

# Load Keys
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

# Initialize Clients
gemini_client = None
if GOOGLE_API_KEY:
    try:
        gemini_client = genai.Client(api_key=GOOGLE_API_KEY)
    except Exception as e:
        print(f"Gemini Client Init Failed: {e}")

openrouter_client = None
if OPENROUTER_API_KEY:
    openrouter_client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )

hf_client = None
if HUGGINGFACE_API_KEY:
    hf_client = OpenAI(
        base_url="https://router.huggingface.co/v1",
        api_key=HUGGINGFACE_API_KEY,
    )

# Priority: DeepSeek -> Others
FALLBACK_MODELS = [
    "deepseek/deepseek-chat", # DeepSeek V3 on OpenRouter
    "google/gemini-2.0-flash-exp:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "mistralai/mistral-7b-instruct:free",
    "qwen/qwen-2.5-vl-7b-instruct:free"
]

def extract_json(text: str) -> dict:
    """
    Robustly extracts the first JSON object found in a string.
    Useful for models that return conversational text around JSON.
    """
    try:
        # Try direct parse first
        return json.loads(text.strip())
    except:
        pass

    # Try finding JSON block
    try:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except:
        pass
        
    return None

def try_huggingface(prompt: str, is_json: bool = False) -> str:
    """
    Fallback to Hugging Face Inference API using the new router.
    """
    if not hf_client:
        return ""
        
    try:
        print("Attempting Hugging Face (Router) API...")
        # Use a reliable, supported model on HF Router
        model_id = "meta-llama/Meta-Llama-3-8B-Instruct"
        
        messages = [{"role": "user", "content": prompt}]
        if is_json:
            messages.insert(0, {"role": "system", "content": "You are a helpful assistant that outputs strict JSON."})
            
        completion = hf_client.chat.completions.create(
            model=model_id,
            messages=messages,
            max_tokens=1024,
            temperature=0.1,
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Hugging Face fallback failed: {e}")
    return ""

def try_ollama(prompt: str, is_json: bool = False) -> str:
    """
    Final fallback to local Ollama. Tries multiple models in sequence.
    """
    local_models = ["gemma3:4b", "gptoss20bcloud", "llama3.2"]
    url = "http://localhost:11434/api/chat"
    
    for model in local_models:
        try:
            print(f"Attempting Ollama with model: {model}...")
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            }
            if is_json:
                payload["format"] = "json"
                
            # Timeout set to 120s for local generation
            response = requests.post(url, json=payload, timeout=120)
            
            if response.status_code == 200:
                return response.json().get("message", {}).get("content", "")
            else:
                print(f"Ollama {model} failed: Status {response.status_code}")
                
        except Exception as e:
            print(f"Ollama fallback for {model} failed: {e}")
            
    return ""

def generate_json(prompt: str, model_hint: str = "gemini-2.0-flash") -> dict:
    """
    Priority: Gemini -> OpenRouter (DeepSeek first) -> Hugging Face -> Ollama
    """
    
    # 1. Try Gemini
    if gemini_client:
        try:
            response = gemini_client.models.generate_content(
                model=model_hint,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"Gemini failed. Trying OpenRouter...")
    
    # 2. Try OpenRouter (DeepSeek prioritized in FALLBACK_MODELS)
    if openrouter_client:
        for fallback_model in FALLBACK_MODELS:
            try:
                print(f"Attempting OpenRouter: {fallback_model}")
                completion = openrouter_client.chat.completions.create(
                    model=fallback_model,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that outputs strict JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                return json.loads(completion.choices[0].message.content)
            except:
                continue 
    
    # 3. Try Hugging Face
    hf_res = try_huggingface(prompt, is_json=True)
    if hf_res:
        result = extract_json(hf_res)
        if result:
            return result
        print("Hugging Face output was not valid JSON.")

    # 4. Final Fallback: Ollama
    print("Attempting Ollama fallback...")
    ollama_res = try_ollama(prompt, is_json=True)
    if ollama_res:
        result = extract_json(ollama_res)
        if result:
            return result
            
    return {}

def generate_text(prompt: str, model_hint: str = "gemini-2.0-flash") -> str:
    """
    Priority: Gemini -> OpenRouter -> Hugging Face -> Ollama
    """
    # 1. Try Gemini
    if gemini_client:
        try:
            response = gemini_client.models.generate_content(model=model_hint, contents=prompt)
            return response.text
        except:
            pass

    # 2. Try OpenRouter
    if openrouter_client:
        for fallback_model in FALLBACK_MODELS:
            try:
                completion = openrouter_client.chat.completions.create(
                    model=fallback_model,
                    messages=[{"role": "user", "content": prompt}]
                )
                return completion.choices[0].message.content
            except:
                continue
    
    # 3. Try Hugging Face
    hf_res = try_huggingface(prompt, is_json=False)
    if hf_res:
        return hf_res

    # 4. Final Fallback: Ollama
    ollama_res = try_ollama(prompt, is_json=False)
    if ollama_res:
        return ollama_res

    return "Error: LLM Generation Failed."