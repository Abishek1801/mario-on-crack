import google.generativeai as genai
import json
import sys
import os
from dotenv import load_dotenv

# Load the API key from the .env file
load_dotenv()
# do some pre processing
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found. Please create a .env file and add it.")

genai.configure(api_key=GEMINI_API_KEY)

# --- FIX #1: Use the current, stable model name ---
# NEW, CORRECTED CODE
llm = genai.GenerativeModel('gemini-pro-latest')

def generate_llm_content(player_data):
    """
    Crafts a detailed prompt with player data and asks the LLM to generate
    a new, personalized game level as a JSON object.
    """
    
    # Condense player data into a readable summary for the LLM
    stats = player_data.get('stats', {})
    outcome = player_data.get('run_outcome', {})
    
    player_summary = (
        f"The player's name is {player_data.get('player_id', 'Unknown')}. "
        f"In their last run, they {outcome.get('result', 'had an unknown result')} via the {outcome.get('path', 'unknown')} path. "
        f"They died {stats.get('deaths', 0)} times and won {stats.get('combats_won', 0)} out of {stats.get('combats_initiated', 0)} combats. "
        f"Their puzzle success rate was {player_data.get('performance_summary', {}).get('puzzle_success_rate', 0) * 100}%. "
    )

    # The prompt engineering - the core of the AI agent.
    prompt = f"""
    You are a creative AI Dungeon Master for a text-based CLI adventure game called 'Dragon's Spire'.
    Your task is to generate the next level's content based on a player's performance.
    The goal is always to rescue the princess from the dragon at the end, but the journey there must be unique.

    PLAYER PERFORMANCE SUMMARY:
    {player_summary}

    INSTRUCTIONS:
    1.  Analyze the player's summary. If they are good at combat, give them harder combat challenges. If they struggle with puzzles, make the puzzles easier or more action-oriented. If they die a lot, create a slightly more forgiving path.
    2.  Create a sequence of TWO scenes for their next adventure.
    3.  Your output MUST be a valid JSON object. Do not include any text or formatting before or after the JSON.
    4.  The JSON must follow this exact schema:
        {{
            "title": "A custom title for this level",
            "scenes": [
                {{
                    "scene_id": 1,
                    "intro_text": "A creative, personalized description of the scene.",
                    "challenge": {{
                        "type": "CHALLENGE_TYPE",
                        "prompt": "The text to show the player before the challenge.",
                        // ... other parameters depending on the type
                    }}
                }},
                {{
                    "scene_id": 2,
                    "intro_text": "Description of the second scene.",
                    "challenge": {{
                        // ... challenge object for the second scene
                    }}
                }}
            ]
        }}
    5.  Available `CHALLENGE_TYPE` values and their required parameters are:
        -   `QTE`: A Quick-Time Event. Requires `key` (string), `presses` (integer), `time_limit` (float).
        -   `RIDDLE`: A riddle. Requires `riddle_text` (string), `answer` (string, one-word), `time_limit` (integer).
        -   `SEQUENCE_MEMORY`: A memory test. Requires `sequence` (list of strings, e.g., ["RED", "BLUE", "GREEN"]).
        -   `DILEMMA`: A choice with no right answer. Requires `options` (list of two strings).

    Now, generate a new JSON object for the player described above.
    """
    
    try:
        print("AGENT: Asking the LLM to generate a new adventure...")
        response = llm.generate_content(prompt)
        # Clean up the response to ensure it's just the JSON
        json_text = response.text.strip().replace('```json', '').replace('```', '')
        print("AGENT: LLM responded. Parsing JSON...")
        return json.loads(json_text)
    except Exception as e:
        print(f"AGENT ERROR: Failed to get a valid response from the LLM. Error: {e}")
        # --- FIX #2: Removed the buggy line that tried to access 'response.text' ---
        # The error details are already printed in the line above.
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python llm_agent.py <path_to_server_input.json>")
        sys.exit(1)

    input_filepath = sys.argv[1]
    try:
        with open(input_filepath, 'r') as f:
            game_run_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not find the file {input_filepath}")
        sys.exit(1)

    personalized_content = generate_llm_content(game_run_data)
    
    if personalized_content:
        output_filename = "personalized_content.json"
        with open(output_filename, 'w') as f:
            json.dump(personalized_content, f, indent=2)
        print(f"\nSuccess! New personalized narrative saved to '{output_filename}'.")