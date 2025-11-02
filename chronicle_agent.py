# FILE: chronicle_agent.py (With a final, ultra-strict prompt to enforce the schema)

import google.generativeai as genai
import json
import sys
import os
import time
from dotenv import load_dotenv

# --- LLM Setup ---
load_dotenv(); GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY: raise ValueError("GEMINI_API_KEY not found.")
genai.configure(api_key=GEMINI_API_KEY); llm = genai.GenerativeModel('gemini-pro-latest')

def evolve_persona(persona_data, run_report):
    """Evolves the game-specific persona based on the last run."""
    print("AGENT: Evolving game-specific persona...")
    game_traits = persona_data['persona']['game']['traits'].copy()
    stats = run_report.get('stats', {})
    if stats.get('combats_initiated', 0) > stats.get('riddles_attempted', 0):
        game_traits['aggression'] = round(game_traits['aggression'] * 0.8 + 1.0 * 0.2, 2)
    else:
        game_traits['puzzle_affinity'] = round(game_traits['puzzle_affinity'] * 0.8 + 1.0 * 0.2, 2)
    if stats.get('deaths', 0) == 0:
        game_traits['resilience'] = round(min(1.0, game_traits['resilience'] + 0.1), 2)
    persona_data['persona']['game']['traits'] = game_traits
    print(f"AGENT -> Evolved game traits: {game_traits}")
    return persona_data

def decide_knobs(persona_data):
    """Decides knobs based on the game-specific persona."""
    print("AGENT: Deciding knobs...")
    knobs = {"enemy_count": 3, "enemy_speed": 1.0, "hint_delay_ms": 10000}
    game_traits = persona_data['persona']['game']['traits']
    if game_traits['aggression'] > 0.6: knobs['enemy_count'] = 4
    if game_traits['resilience'] < 0.4: knobs['enemy_speed'] = 0.8
    return knobs

def generate_llm_content(persona_data):
    """Generates creative content from the LLM with a more robust, example-driven prompt."""
    persona_summary = json.dumps(persona_data['persona']['game']['traits'])
    
    # --- THIS IS THE FINAL, STRICTEST PROMPT ---
    prompt = f"""
    You are an AI game content generator. Your only job is to create a perfectly formatted JSON object that follows a strict schema.

    PLAYER PERSONA:
    {persona_summary}

    YOUR TASK:
    Based on the player's persona, create a JSON object for their next adventure.

    **CRITICAL SCHEMA ENFORCEMENT RULES:**
    1.  Your output MUST be a valid JSON object and nothing else.
    2.  The root object must have a "title" (string) and "scenes" (a list of exactly two scene objects).
    3.  EVERY scene object MUST have an "intro_text" (string) and a "challenge" (OBJECT).
    4.  The "challenge" object MUST have a "type" key.
    5.  The value for the "type" key **MUST BE ONE OF THESE FOUR EXACT STRINGS**:
        - "QTE"
        - "RIDDLE"
        - "SEQUENCE_MEMORY"
        - "DILEMMA"
    6.  **DO NOT invent new challenge types like "CHOICE".** If you want to give the player a choice, you **MUST** use the "DILEMMA" type.

    Follow the schema perfectly. Here is an example of a perfect response:
    {{
      "title": "The Path of Whispers",
      "scenes": [
        {{
          "intro_text": "You enter a hall of mirrors. Your reflection seems to move on its own.",
          "challenge": {{
            "type": "DILEMMA",
            "prompt": "One reflection points to a golden door, another to a silver one. Which do you trust?",
            "options": ["Trust the golden reflection.", "Trust the silver reflection."]
          }}
        }},
        {{
          "intro_text": "The door leads to a pressure-plated floor.",
          "challenge": {{
            "type": "QTE",
            "prompt": "A section of the floor gives way!",
            "key": "J",
            "presses": 5,
            "time_limit": 1.5
          }}
        }}
      ]
    }}

    Now, following all rules, generate a new JSON object for the player.
    """
    try:
        print("AGENT: Asking LLM for creative content with final, strict prompt...")
        response = llm.generate_content(prompt)
        json_text = response.text.strip().replace('```json', '').replace('```', '')
        parsed_json = json.loads(json_text)
        if not isinstance(parsed_json, dict):
            raise ValueError("LLM did not return a dictionary.")
        return parsed_json
    except Exception as e:
        print(f"AGENT CRITICAL ERROR: LLM failed to generate valid JSON. Error: {e}")
        return None

# --- Main Agent Logic (Unchanged) ---
if __name__ == "__main__":
    persona_file = "player_persona.json"
    if not os.path.exists(persona_file):
        print(f"FATAL: '{persona_file}' not found! Run 'player_setup.py' first.")
        sys.exit(1)
    with open(persona_file, 'r') as f:
        persona_data = json.load(f)
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            run_report = json.load(f)
        persona_data = evolve_persona(persona_data, run_report)
        with open(persona_file, 'w') as f:
            json.dump(persona_data, f, indent=2)
        print(f"AGENT: Evolved persona saved to '{persona_file}'.")
    knobs = decide_knobs(persona_data)
    content = generate_llm_content(persona_data)
    if content:
        game_instructions = {"knobs": knobs, "content": content}
        with open("game_instructions.json", 'w') as f:
            json.dump(game_instructions, f, indent=2)
        print(f"\nSuccess! New level instructions saved to 'game_instructions.json'.")