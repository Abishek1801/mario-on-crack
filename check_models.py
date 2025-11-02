import google.generativeai as genai
import os
from dotenv import load_dotenv  
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
	raise ValueError("GEMINI_API_KEY not found in .env file. Please ensure it's there.")
print("Connecting to Google AI with your API key...")
genai.configure(api_key=GEMINI_API_KEY)
print("\n--- Available Models for 'generateContent' ---")
print("I will now ask Google which models you are allowed to use.")
print("----------------------------------------------")
found_models = False
try:
    for m in genai.list_models():
        # We check if the model supports the specific function our agent uses
        if 'generateContent' in m.supported_generation_methods:
            print(f"Model found: {m.name}")
            found_models = True
except Exception as e:
    print(f"\nAn error occurred while trying to list models: {e}")
    print("This could be an issue with your API key or project permissions.")
if not found_models:
    print("\nNo models supporting 'generateContent' were found for your API key.")
    print("This strongly suggests a regional availability issue or a problem with your API key setup.")
print("----------------------------------------------")
print("Copy the full model name (e.g., 'models/gemini-1.0-pro') from the list above.")
print("Paste it into your 'llm_agent.py' file to fix the error.")