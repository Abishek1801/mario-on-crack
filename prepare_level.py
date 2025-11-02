# FILE: prepare_level.py (Updated to accept player_id from CLI)

import google.generativeai as genai
import json
import sys
import os
import requests
from dotenv import load_dotenv

# --- CONFIGURATION ---
BACKEND_URL = "http://192.168.0.199:7769"

# --- LLM Setup ---
load_dotenv(); GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY: raise ValueError("GEMINI_API_KEY not found.")
genai.configure(api_key=GEMINI_API_KEY); llm = genai.GenerativeModel('gemini-pro-latest')

def fetch_persona_from_supermemory(player_id, scope="global"):
    # ... (This function is unchanged)
    print(f"AGENT: Fetching '{scope}' persona for player '{player_id}'...")
    url = f"{BACKEND_URL}/sm/personas?player_id={player_id}&scope={scope}&limit=1"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data['total'] > 0 and data['items'][0]['persona']: print("AGENT: Persona fetched."); return data['items'][0]['persona']
            else: print("AGENT WARNING: Player has no persona. Using default."); return None
        else: print(f"AGENT ERROR: Failed to fetch persona. Status: {response.status_code}"); return None
    except requests.exceptions.ConnectionError: print(f"AGENT CRITICAL ERROR: Could not connect to backend at {BACKEND_URL}."); return None

def decide_knobs(persona):
    # ... (This function is unchanged)
    knobs = {"enemy_count": 3, "enemy_speed": 1.0}; traits = persona['traits']
    if traits.get('aggression', 0.5) > 0.6: knobs['enemy_count'] = 4
    if traits.get('resilience', 0.5) < 0.4: knobs['enemy_speed'] = 0.8
    return knobs

def generate_llm_content(persona):
    # ... (This function is unchanged)
    persona_summary = json.dumps(persona['traits'])
    prompt = f"""
    You are an AI Dungeon Master. A hero with this persona is playing: {persona_summary}.
    Your task is to create a JSON object for their next adventure.
    CRITICAL SCHEMA ENFORCEMENT RULES:
    1. Your output MUST be a valid JSON object.
    2. The root object must have "title" (string) and "scenes" (a list of EXACTLY FOUR scene objects).
    3. EVERY scene object MUST have an "intro_text" (string, 1-2 sentences) and a "challenge" (OBJECT).
    4. The "challenge" object's "type" key MUST be one of: "QTE", "RIDDLE", "SEQUENCE_MEMORY", "DILEMMA", "JUMP_CHASM", "FIND_COLLECTIBLE".
    5. MANDATORY KEYS FOR EACH TYPE:
       - "QTE": "key", "presses", "time_limit".
       - "RIDDLE": "riddle_text", "answer", "time_limit", AND "hint_text".
       - "SEQUENCE_MEMORY": "sequence".
       - "DILEMMA": "options".
       - "JUMP_CHASM": "prompt", "success_chance".
       - "FIND_COLLECTIBLE": "description".
    Generate a new JSON object for the player now.
    """
    try:
        print("AGENT: Asking LLM for a varied and creative adventure..."); response = llm.generate_content(prompt)
        json_text = response.text.strip().replace('```json', '').replace('```', ''); return json.loads(json_text)
    except Exception as e:
        print(f"AGENT CRITICAL ERROR: LLM failed to generate valid JSON. Error: {e}"); return None

# --- MAIN AGENT LOGIC (UPDATED) ---
if __name__ == "__main__":
    # --- CHANGE: Get player_id from command-line argument ---
    if len(sys.argv) < 2:
        print("Usage: python prepare_level.py <player_id>")
        sys.exit(1)
    player_id = sys.argv[1]
    
    persona_data = fetch_persona_from_supermemory(player_id)
    if persona_data is None: 
        persona_data = {"traits": {"aggression": 0.5, "stealth": 0.5, "curiosity": 0.5, "puzzle_affinity": 0.5, "independence": 0.5, "resilience": 0.5, "goal_focus": 0.5}}
    
    knobs = decide_knobs(persona_data)
    content = generate_llm_content(persona_data)
    
    if content:
        # --- CHANGE: Add a 'meta' object with the player_id to the instructions ---
        game_instructions = {
            "meta": {
                "player_id": player_id
            },
            "knobs": knobs,
            "content": content
        }
        with open("game_instructions.json", 'w') as f:
            json.dump(game_instructions, f, indent=2)
        print(f"\nSuccess! New level instructions for player '{player_id}' saved to 'game_instructions.json'.")