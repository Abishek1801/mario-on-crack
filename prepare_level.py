# FILE: prepare_level.py (Final, robust version for Supermemory integration)

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

# --- Display Helpers ---
def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def typewriter_print(text, delay=0.03):
    """Print text with a typewriter effect."""
    import time
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()


def fetch_persona_from_supermemory(player_id, scope="global"):
    """
    Makes a GET request to the backend. Now correctly handles the 'default' response for new players.
    Returns a tuple: (persona_object, is_new_player_boolean)
    """
    print(f"AGENT: Fetching '{scope}' persona for player '{player_id}'...")
    url = f"{BACKEND_URL}/sm/personas?player_id={player_id}&scope={scope}&limit=1"
    headers = {"X-API-Key": os.getenv("CHRONICLE_API_KEY")}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            # Case 1: Existing player found
            if data.get('total', 0) > 0 and data['items'][0].get('persona'):
                print("AGENT: Existing persona successfully fetched.")
                return data['items'][0]['persona'], False # False means NOT a new player
            # Case 2: New player detected, API provides a default persona
            elif 'default' in data and data['default'].get('persona'):
                print("AGENT: New player detected. Using default persona from API.")
                # We extract the global persona from the default structure
                return data['default']['persona']['global'], True # True means IS a new player
            else:
                print("AGENT WARNING: API response was not in the expected format. Using local default.")
                return None, True
        else:
            print(f"AGENT ERROR: Failed to fetch persona. Status: {response.status_code}"); return None, True
    except requests.exceptions.ConnectionError:
        print(f"AGENT CRITICAL ERROR: Could not connect to backend at {BACKEND_URL}."); return None, True

def decide_knobs(persona, is_new_player):
    """
    Decides knobs based on persona traits. Now makes the first level easier.
    """
    print("AGENT: Deciding difficulty knobs...")
    
    # --- THIS IS THE "EASY FIRST LEVEL" FIX ---
    if is_new_player:
        print("AGENT -> New player detected. Applying 'Welcome Mat' difficulty settings.")
        return {"enemy_count": 2, "enemy_speed": 0.7}, ["New player detected. Setting easier difficulty."]

    # Standard logic for returning players
    knobs = {"enemy_count": 3, "enemy_speed": 1.0}
    reasons = []
    traits = persona.get('traits', {})
    if traits.get('aggression', 0.5) > 0.6:
        knobs['enemy_count'] = 4; reasons.append(f"High Aggression -> Increased enemy count.")
    if traits.get('resilience', 0.5) < 0.4:
        knobs['enemy_speed'] = 0.8; reasons.append(f"Low Resilience -> Reduced enemy speed.")
    if not reasons: reasons.append("Balanced profile. Using standard difficulty.")
    return knobs, reasons

def generate_llm_content(persona):
    """Generates creative content from the LLM with the final, strictest prompt."""
    persona_summary = json.dumps(persona.get('traits', {}))
    
    # --- THIS IS THE FINAL, ULTRA-STRICT PROMPT ---
    prompt = f"""
    You are an AI game content generator. Your only job is to create a perfectly formatted JSON object.

    PLAYER PERSONA:
    {persona_summary}

    YOUR TASK:
    Based on the player's persona, create a JSON object for their next adventure.

    **CRITICAL SCHEMA ENFORCEMENT RULES - FOLLOW PERFECTLY:**
    1.  Your output MUST be a valid JSON object and nothing else.
    2.  The root object MUST have "title" (string) and "scenes" (a list of FOUR scene objects).
    3.  EVERY scene object MUST have an "intro_text" (string, 1-2 sentences) and a "challenge" (OBJECT).
    4.  The "challenge" object MUST have a "type" key. The value for "type" MUST be one of these EXACT STRINGS: "QTE", "RIDDLE", "SEQUENCE_MEMORY", "DILEMMA", "JUMP_CHASM", "FIND_COLLECTIBLE".
    5.  **MANDATORY KEYS FOR EACH TYPE (THIS IS NOT OPTIONAL):**
        - If "type" is "QTE", the challenge object MUST also contain: "key" (string), "presses" (integer), "time_limit" (float).
        - If "type" is "RIDDLE", the challenge object MUST also contain: "riddle_text" (string), "answer" (string), "time_limit" (integer), and "hint_text" (string).
        - If "type" is "SEQUENCE_MEMORY", the challenge object MUST also contain: "sequence" (list of strings).
        - If "type" is "DILEMMA", the challenge object MUST also contain: "options" (a list of exactly two strings).
        - If "type" is "JUMP_CHASM", it MUST contain: "prompt" (string), "success_chance" (float).
        - If "type" is "FIND_COLLECTIBLE", it MUST contain: "description" (string).
    6.  DO NOT invent new types. Use a variety of the allowed types.

    Generate the JSON object now.
    """
    try:
        print("AGENT: Asking SDK for a varied and creative adventure..."); response = llm.generate_content(prompt)
        json_text = response.text.strip().replace('```json', '').replace('```', ''); parsed_json = json.loads(json_text)
        if not isinstance(parsed_json, dict): raise ValueError("SDK did not return a dictionary.")
        return parsed_json
    except Exception as e:
        print(f"AGENT CRITICAL ERROR: SDK failed to generate valid JSON. Error: {e}"); return None

# ... (display_generation_summary and main logic are the same, just paste them in)
def display_generation_summary(player_id,persona,knob_reasons,content):
    clear_screen();print("="*60);print("  CHRONICLE AI: PERSONALIZING YOUR NEXT ADVENTURE...");print("="*60);time.sleep(1);print("\n[ 1. WE ANALYZED YOUR PLAYSTYLE ]\n");
    if persona and persona.get('traits'):
        traits=persona['traits'];top_trait=max(traits,key=traits.get);persona_description={"aggression":"a bold fighter.","puzzle_affinity":"a clever strategist.","curiosity":"a keen explorer.","stealth":"a silent shadow.","resilience":"a determined hero.","independence":"a self-reliant adventurer.","goal_focus":"a focused champion."}.get(top_trait,"a balanced adventurer.");print("  Our AI has analyzed your profile and sees that you are...");typewriter_print(f"  ... {persona_description}\n",delay=0.05)
    else:print("  No existing persona found. Preparing a balanced trial.\n")
    time.sleep(1);print("[ 2. WE ARE RESHAPING THE WORLD FOR YOU ]\n");print("  Based on what we learned, we've adjusted the next level:")
    for reason in knob_reasons:typewriter_print(f"  * {reason}",delay=0.04)
    print();time.sleep(1);print("[ 3. YOUR PERSONALIZED ADVENTURE AWAITS ]\n")
    if content and content.get('scenes'):
        challenge_counts={};
        for scene in content['scenes']:challenge_type=scene.get('challenge',{}).get('type','UNKNOWN');challenge_counts[challenge_type]=challenge_counts.get(challenge_type,0)+1
        print(f"  Our AI Storyteller has crafted a chapter called: '{content.get('title','A Fated Encounter')}'");print("  This adventure will feature:")
        for challenge_type,count in challenge_counts.items():
            challenge_description={"QTE":f"{count} test(s) of strength.","RIDDLE":f"{count} riddle(s) of intellect.","JUMP_CHASM":f"{count} leap(s) of faith.","SEQUENCE_MEMORY":f"{count} puzzle(s) of memory.","DILEMMA":f"{count} choice(s) with consequences.","FIND_COLLECTIBLE":f"{count} secret(s) to discover."}.get(challenge_type,f"{count} unknown trial(s).");typewriter_print(f"    - {challenge_description}",delay=0.04)
        print()
    else:print("  * The AI Storyteller failed to generate content.")
    print("="*60);print("  PREPARE YOURSELF...");print("="*60);time.sleep(3)

if __name__ == "__main__":
    if len(sys.argv) < 2: print("Usage: python prepare_level.py <player_id>"); sys.exit(1)
    player_id = sys.argv[1]
    
    # Fetch persona and check if it's a new player
    persona_data, is_new_player = fetch_persona_from_supermemory(player_id)
    
    if persona_data is None: 
        # Fallback if API fails completely
        persona_data = {"traits": {"aggression": 0.5, "stealth": 0.5, "curiosity": 0.5, "puzzle_affinity": 0.5, "independence": 0.5, "resilience": 0.5, "goal_focus": 0.5}}
        is_new_player = True # Treat as new player if API fails
    
    # Pass the is_new_player flag to the knobs function
    knobs, knob_reasons = decide_knobs(persona_data, is_new_player)
    
    content = generate_llm_content(persona_data)
    
    if content:
        game_instructions = {"meta": {"player_id": player_id}, "knobs": knobs, "content": content}
        with open("game_instructions.json", 'w') as f:
            json.dump(game_instructions, f, indent=2)
        display_generation_summary(player_id, persona_data, knob_reasons, content)
        print(f"\nSUCCESS! New instructions saved to 'game_instructions.json'.\nRun 'python game_engine.py' to play.")