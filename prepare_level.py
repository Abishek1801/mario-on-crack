# FILE: prepare_level.py (Final version with a non-technical summary)

import google.generativeai as genai
import json
import sys
import os
import requests
import time
from dotenv import load_dotenv

# --- CONFIGURATION ---
BACKEND_URL = "http://192.168.0.199:7769"

# --- LLM Setup ---
load_dotenv(); GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY: raise ValueError("GEMINI_API_KEY not found.")
genai.configure(api_key=GEMINI_API_KEY); llm = genai.GenerativeModel('gemini-pro-latest')

# Small helpers used by the summary display
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def typewriter_print(text, delay=0.03):
    for ch in str(text):
        print(ch, end='', flush=True)
        time.sleep(delay)
    print()


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
    knobs = {"enemy_count": 3, "enemy_speed": 1.0}
    reasons = []
    traits = persona.get('traits', {})
    if traits.get('aggression', 0.5) > 0.6:
        knobs['enemy_count'] = 4
        reasons.append(f"High Aggression ({traits['aggression']}) -> Increased enemy count to 4.")
    if traits.get('resilience', 0.5) < 0.4:
        knobs['enemy_speed'] = 0.8
        reasons.append(f"Low Resilience ({traits['resilience']}) -> Reduced enemy speed to make things a bit easier.")
    if not reasons:
        reasons.append("Player has a balanced profile. Using standard difficulty.")
    return knobs, reasons

def generate_llm_content(persona):
    # ... (This function is unchanged)
    persona_summary = json.dumps(persona.get('traits', {}))
    prompt = f"""You are an AI Dungeon Master. A hero with this persona is playing: {persona_summary}. Create a JSON for their adventure with a "title" and FOUR "scenes". Each scene needs "intro_text" and a "challenge" object (`QTE`, `RIDDLE` with `hint_text`, `JUMP_CHASM`, etc.). Use a variety of challenges. Do not add any text before or after the JSON."""
    try:
        print("AGENT: Asking LLM for a varied and creative adventure...")
        response = llm.generate_content(prompt)
        json_text = response.text.strip().replace('```json', '').replace('```', '')
        parsed_json = json.loads(json_text)
        if not isinstance(parsed_json, dict): raise ValueError("LLM did not return a dictionary.")
        return parsed_json
    except Exception as e:
        print(f"AGENT CRITICAL ERROR: LLM failed to generate valid JSON. Error: {e}"); return None

# --- NEW FUNCTION: The Non-Technical Generation Report ---
def display_generation_summary(player_id, persona, knob_reasons, content):
    """
    Prints a clear, non-technical, story-driven summary of the agent's decisions.
    """
    clear_screen()
    print("="*60)
    print("  CHRONICLE AI: PERSONALIZING YOUR NEXT ADVENTURE...")
    print("="*60)
    time.sleep(1)

    # --- 1. What the Agent Saw ---
    print("\n[ 1. WE ANALYZED YOUR PLAYSTYLE ]\n")
    if persona and persona.get('traits'):
        traits = persona['traits']
        top_trait = max(traits, key=traits.get)
        
        # Translate the technical trait name into a story
        persona_description = {
            "aggression": "a bold and aggressive fighter who charges into battle.",
            "puzzle_affinity": "a clever strategist who enjoys a good puzzle.",
            "curiosity": "a keen explorer who loves to uncover secrets.",
            "stealth": "a silent shadow who prefers to avoid direct conflict.",
            "resilience": "a determined hero who never gives up, no matter the setback.",
            "independence": "a self-reliant adventurer who forges their own path.",
            "goal_focus": "a focused champion who drives directly towards their objective."
        }.get(top_trait, "a balanced adventurer.")

        print(f"  Our AI has looked at your past adventures and sees that you are...")
        typewriter_print(f"  ... {persona_description}\n", delay=0.05)
    else:
        print("  As a new adventurer, your path is yet unwritten. We've prepared a balanced trial for you.\n")
    
    time.sleep(1)

    # --- 2. How the Agent Changed the World ---
    print("[ 2. WE ARE RESHAPING THE WORLD FOR YOU ]\n")
    print("  Based on what we learned, we've adjusted the next level:")
    
    # Translate the technical reasons into a story
    for reason in knob_reasons:
        if "Increased enemy count" in reason:
            typewriter_print("  * Because you are a strong fighter, we've summoned more enemies to test your might.", delay=0.04)
        elif "Reduced enemy speed" in reason:
            typewriter_print("  * Because you've faced setbacks, we've made the enemies a little slower to give you an edge.", delay=0.04)
        else:
            typewriter_print("  * The challenges ahead are set to a standard difficulty.", delay=0.04)
    print()
    time.sleep(1)
    
    # --- 3. What the Player Will Experience ---
    print("[ 3. YOUR PERSONALIZED ADVENTURE AWAITS ]\n")
    if content and content.get('scenes'):
        challenge_counts = {}
        for scene in content['scenes']:
            challenge_type = scene.get('challenge', {}).get('type', 'UNKNOWN')
            challenge_counts[challenge_type] = challenge_counts.get(challenge_type, 0) + 1
        
        print(f"  Our AI Storyteller has crafted a new chapter called: '{content.get('title', 'A Fated Encounter')}'")
        print(f"  To match your unique style, this adventure will feature:")
        
        # Translate the challenge types into a story
        for challenge_type, count in challenge_counts.items():
            challenge_description = {
                "QTE": f"{count} test(s) of your strength and reflexes.",
                "RIDDLE": f"{count} riddle(s) to challenge your intellect.",
                "JUMP_CHASM": f"{count} perilous leap(s) of faith.",
                "SEQUENCE_MEMORY": f"{count} ancient puzzle(s) that will test your memory.",
                "DILEMMA": f"{count} difficult choice(s) with unknown consequences.",
                "FIND_COLLECTIBLE": f"{count} hidden secret(s) for you to discover."
            }.get(challenge_type, f"{count} unknown trial(s).")
            typewriter_print(f"    - {challenge_description}", delay=0.04)
        print()
    else:
        print("  * The AI Storyteller is still pondering your fate... (LLM failed to generate content).")
    
    print("="*60)
    print("  PREPARE YOURSELF. THE GAME IS ABOUT TO BEGIN...")
    print("="*60)
    time.sleep(3)


# --- Main Agent Logic (Unchanged) ---
if __name__ == "__main__":
    if len(sys.argv) < 2: print("Usage: python prepare_level.py <player_id>"); sys.exit(1)
    player_id = sys.argv[1]
    
    persona_data = fetch_persona_from_supermemory(player_id)
    if persona_data is None: 
        persona_data = {"traits": {"aggression": 0.5, "stealth": 0.5, "curiosity": 0.5, "puzzle_affinity": 0.5, "independence": 0.5, "resilience": 0.5, "goal_focus": 0.5}}
    
    knobs, knob_reasons = decide_knobs(persona_data)
    content = generate_llm_content(persona_data)
    
    if content:
        game_instructions = {
            "meta": {"player_id": player_id},
            "knobs": knobs,
            "content": content
        }
        with open("game_instructions.json", 'w') as f:
            json.dump(game_instructions, f, indent=2)
            
        display_generation_summary(player_id, persona_data, knob_reasons, content)
        
        print(f"\nSUCCESS! New level instructions saved to 'game_instructions.json'.\nRun 'python game_engine.py' to play.")