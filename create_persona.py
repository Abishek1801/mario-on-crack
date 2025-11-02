# FILE: create_persona.py (New and Improved Version)

import google.generativeai as genai
import json
import os
from dotenv import load_dotenv

# --- LLM Setup ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file.")
genai.configure(api_key=GEMINI_API_KEY)
llm = genai.GenerativeModel('gemini-pro-latest')

# --- Helper function for asking questions ---
def get_player_choice(prompt, options):
    """
    Displays a prompt and a list of options, returning the chosen text.
    """
    print("\n" + "="*50)
    print(prompt)
    print("="*50)
    
    for i, text in enumerate(options, 1):
        print(f"  [{i}] {text}")
    
    while True:
        choice_input = input("> ").strip()
        if choice_input.isdigit() and 1 <= int(choice_input) <= len(options):
            return options[int(choice_input) - 1] # Return the full text of the choice
        else:
            print("Invalid choice. Please enter a number from the options.")

# --- Main Persona Creation Function ---
def create_initial_persona():
    """
    Asks the user a series of simple, direct questions and uses the LLM
    to generate an initial persona JSON from their answers.
    """
    print("--- CHRONICLE PERSONA FORGE ---")
    print("Answer a few questions to shape your hero's starting identity.")
    
    # --- Question 1 ---
    q1_prompt = "You stand before a locked door. The guard has the key but is fast asleep."
    q1_options = [
        "Attack the guard to get the key quickly.",
        "Attempt to sneak past and pick the guard's pocket for the key.",
        "Look around the room for another way forward, avoiding the guard entirely."
    ]
    answer1 = get_player_choice(q1_prompt, q1_options)
    
    # --- Question 2 ---
    q2_prompt = "You find a treasure chest, but it's sealed with a complex riddle."
    q2_options = [
        "Spend as long as it takes to solve the riddle yourself.",
        "Look for clues in the environment to help you solve it.",
        "Smash the lock. The treasure is what's important, not the puzzle."
    ]
    answer2 = get_player_choice(q2_prompt, q2_options)
    
    print("\nAnalyzing your choices to forge your persona...")

    # --- Construct the Prompt for the LLM ---
    # This prompt is very direct and tells the LLM exactly how to behave.
    prompt = f"""
    You are a Persona Forge AI. Your task is to create a JSON object representing a player's starting persona based on their answers to two scenarios.

    PLAYER'S ANSWERS:
    - Scenario 1 (Sleeping Guard): The player chose to '{answer1}'
    - Scenario 2 (Riddle Chest): The player chose to '{answer2}'

    YOUR INSTRUCTIONS:
    1. Analyze the player's choices.
    2. Create a JSON object with the following keys: "aggression", "stealth", "curiosity", "puzzle_affinity", "independence", "resilience", "goal_focus".
    3. Assign a value from 0.0 to 1.0 for each trait based on their answers.

    MAPPING GUIDELINES:
    - Choosing to 'Attack' strongly increases 'aggression' and 'goal_focus'.
    - Choosing to 'Sneak' strongly increases 'stealth'.
    - Choosing to 'Look around' strongly increases 'curiosity'.
    - Choosing to 'Solve the riddle yourself' strongly increases 'independence' and 'puzzle_affinity'.
    - Choosing to 'Look for clues' increases 'curiosity' and 'puzzle_affinity'.
    - Choosing to 'Smash the lock' strongly increases 'aggression' and 'goal_focus', and lowers 'puzzle_affinity'.
    - All personas should have a baseline 'resilience' of around 0.5.

    Your output MUST be ONLY the JSON object. Do not include any other text, comments, or markdown formatting.
    """
    
    try:
        response = llm.generate_content(prompt)
        json_text = response.text.strip().replace('```json', '').replace('```', '')
        persona_traits = json.loads(json_text)
        
        # Final structure for the persona file
        final_persona = {"traits": persona_traits}
        return final_persona

    except Exception as e:
        print(f"An error occurred while forging the persona: {e}")
        return None

# --- Main Execution Block ---
if __name__ == "__main__":
    player_persona = create_initial_persona()
    
    if player_persona:
        output_filename = "persona.json"
        with open(output_filename, 'w') as f:
            json.dump(player_persona, f, indent=2)
        print(f"\nSuccess! Your initial persona has been saved to '{output_filename}'.")
        print("You can now run 'python llm_agent.py' to generate your first personalized adventure.")