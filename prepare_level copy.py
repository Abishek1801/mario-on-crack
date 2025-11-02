# FILE: prepare_level.py

import google.generativeai as genai
import json
import sys
import os
import requests
from dotenv import load_dotenv

# --- CONFIGURATION ---
BACKEND_URL = "http://192.168.0.199:7769" # The URL of your friend's server

# --- LLM Setup ---
load_dotenv(); GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY: raise ValueError("GEMINI_API_KEY not found.")
genai.configure(api_key=GEMINI_API_KEY); llm = genai.GenerativeModel('gemini-pro-latest')


def fetch_persona_from_supermemory(player_id, scope="global"):
    """Makes a GET request to the backend to fetch the player's persona."""
    print(f"AGENT: Fetching '{scope}' persona for player '{player_id}'...")
    url = f"{BACKEND_URL}/sm/personas?player_id={player_id}&scope={scope}&limit=1"
    
    try:
        response = requests.get(url)
        print(f"AGENT: Received response with status code {response.status_code}.")
        if response.status_code == 200:
            data = response.json()
            if data['total'] > 0 and data['items'][0]['persona']:
                print("AGENT: Persona successfully fetched.")
                return data['items'][0]['persona']
            else:
                print("AGENT WARNING: Player not found or has no persona. Using default.")
                return None
        else:
            print(f"AGENT ERROR: Failed to fetch persona. Status: {response.status_code}, Response: {response.text}")
            return None
    except requests.exceptions.ConnectionError as e:
        print(f"AGENT CRITICAL ERROR: Could not connect to the backend at {BACKEND_URL}.")
        print("Is the server running?")
        return None

def decide_knobs(persona):
    """Decides knobs based on the fetched persona traits."""
    knobs = {"enemy_count": 3, "enemy_speed": 1.0}
    traits = persona['traits']
    if traits.get('aggression', 0.5) > 0.6: knobs['enemy_count'] = 4
    if traits.get('resilience', 0.5) < 0.4: knobs['enemy_speed'] = 0.8
    return knobs

def generate_llm_content(persona):
    """Generates creative content from the LLM using the fetched persona."""
    prompt = f"You are an AI Dungeon Master. A hero with this persona is playing: {json.dumps(persona['traits'])}. Generate a JSON for their next adventure with a 'title' and two 'scenes'. Each scene needs 'intro_text' and a 'challenge' object (`QTE`, `RIDDLE`, etc.). Do not add any text before or after the JSON."
    try:
        print("AGENT: Asking LLM for creative content...")
        response = llm.generate_content(prompt)
        json_text = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(json_text)
    except Exception as e:
        print(f"AGENT ERROR: LLM failed. Error: {e}"); return None

# --- MAIN AGENT LOGIC ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python prepare_level.py <player_id>")
        sys.exit(1)
        
    player_id = sys.argv[1]
    
    # Fetch the persona from the live backend
    persona_data = fetch_persona_from_supermemory(player_id)
    print(f"AGENT: Current persona data: {persona_data}")
    
    if persona_data is None:
        # If no persona exists, create a default one for the first run
        persona_data = {
            "traits": {"aggression": 0.5, "stealth": 0.5, "curiosity": 0.5, "puzzle_affinity": 0.5, "independence": 0.5, "resilience": 0.5, "goal_focus": 0.5}
        }
    
    knobs = decide_knobs(persona_data)
    content = generate_llm_content(persona_data)
    
    if content:
        game_instructions = {"knobs": knobs, "content": content}
        with open("game_instructions.json", 'w') as f:
            json.dump(game_instructions, f, indent=2)
        print(f"\nSuccess! New level instructions saved to 'game_instructions.json'.")  