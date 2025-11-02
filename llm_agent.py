# FILE: llm_dynamic_game.py

import json
import os
import time
import uuid
import random

# --- Platform-specific non-blocking input reader for QTEs ---
try:
    import msvcrt
    def get_char_non_blocking():
        if msvcrt.kbhit():
            return msvcrt.getch().decode('utf-8').upper()
        return None
except ImportError:
    import sys, tty, termios
    def get_char_non_blocking():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setcbreak(sys.stdin.fileno())
            import select
            if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                return sys.stdin.read(1).upper()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return None

# --- Helper Functions ---
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def typewriter_print(text, delay=0.03):
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()

def get_player_choice(prompt, options):
    while True:
        typewriter_print(prompt)
        for i, text in enumerate(options, 1):
            print(f"  [{i}] {text}")
        choice = input("> ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return int(choice) - 1
        else:
            print("\nInvalid choice. Please enter a number.")
            time.sleep(1)

# --- GameState Class ---
# This class tracks everything for the final "report card" JSON.
class GameState:
    def __init__(self, player_id, run_index):
        self.player_id = player_id
        self.run_index = run_index
        self.session_start_time = time.time()
        self.run_outcome = {"result": "loss", "path": "exploration"}
        self.stats = {
            "time_s": 0, "deaths": 0, "retries": 0, "distance_traveled": 0,
            "jumps": 0, "hint_offers": 0, "hints_used": 0, "riddles_attempted": 0,
            "riddles_correct": 0, "combats_initiated": 0, "combats_won": 0,
            "collectibles_found": 0
        }

    def increment_stat(self, key, value=1):
        if key in self.stats:
            self.stats[key] += value

    def handle_death(self, message):
        clear_screen()
        typewriter_print(message)
        typewriter_print("\nYou awaken back at the start of the adventure.")
        time.sleep(3)
        self.increment_stat('deaths')
        self.increment_stat('retries')
        return False

# --- JSON Report Card Generator ---
def generate_output_json(state, knobs):
    events_digest = [
        {"type": "death", "count": state.stats['deaths']},
        {"type": "fail.retry", "count": state.stats['retries']},
        {"type": "combat.start", "count": state.stats['combats_initiated']},
        {"type": "combat.win", "count": state.stats['combats_won']},
        {"type": "puzzle.attempt", "count": state.stats['riddles_attempted']}
    ]
    output = {
        "schema_version": "1.0",
        "player_id": state.player_id,
        "session_id": f"sess_{uuid.uuid4().hex[:12]}",
        "run_index": state.run_index,
        "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "run_outcome": state.run_outcome,
        "stats": state.stats,
        "events_digest": [e for e in events_digest if e['count'] > 0],
        "config_used": {
            "mode": "challenge",
            "knobs": knobs
        },
        "performance_summary": {
            "avg_enemy_engagement_time": 3.2,
            "puzzle_success_rate":
                state.stats['riddles_correct'] / state.stats['riddles_attempted']
                if state.stats['riddles_attempted'] > 0 else 0,
            "exploration_ratio": 0.0,
            "hint_reliance": 0.0
        }
    }
    return output

# --- Generic Challenge Runner ---
def run_challenge(state, challenge):
    challenge_type = challenge.get('type')
    
    if challenge_type == 'QTE':
        state.increment_stat('combats_initiated')
        typewriter_print(challenge.get('prompt', 'Prepare for action!'))
        key, presses, time_limit = challenge['key'], challenge['presses'], challenge['time_limit']
        print(f"MASH '{key}' {presses} TIMES IN {time_limit} SECONDS!", flush=True)
        start_time = time.time()
        press_count = 0
        while time.time() - start_time < time_limit:
            if get_char_non_blocking() == key:
                press_count += 1
                print(key, end='', flush=True)
                if press_count >= presses:
                    print("\n")
                    typewriter_print("Success!")
                    state.increment_stat('combats_won')
                    time.sleep(2)
                    return True
        return state.handle_death("Too slow!")

    elif challenge_type == 'RIDDLE':
        state.increment_stat('riddles_attempted')
        typewriter_print(challenge.get('prompt', 'Solve this riddle:'))
        typewriter_print(f"\"{challenge['riddle_text']}\"")
        start_time = time.time()
        answer = input("> ").strip().lower()
        if time.time() - start_time > challenge['time_limit']:
            return state.handle_death("You ran out of time!")
        if challenge['answer'].lower() in answer:
            typewriter_print("Correct!")
            state.increment_stat('riddles_correct')
            time.sleep(2)
            return True
        return state.handle_death("That is not the answer.")

    elif challenge_type == 'SEQUENCE_MEMORY':
        state.increment_stat('riddles_attempted')
        typewriter_print(challenge.get('prompt', 'Memorize the sequence.'))
        sequence = challenge['sequence']
        for item in sequence:
            print(f"  {item}  ", end='', flush=True)
            time.sleep(1.5)
            print("\r" + " " * 20 + "\r", end='', flush=True)
        user_input = input("Enter the sequence, separated by spaces: > ").strip().upper().split()
        if user_input == sequence:
            typewriter_print("Perfect memory!")
            state.increment_stat('riddles_correct')
            time.sleep(2)
            return True
        return state.handle_death("Your memory fails you.")
    
    elif challenge_type == 'DILEMMA':
        options = challenge['options']
        choice = get_player_choice(challenge.get('prompt', 'A difficult choice...'), options)
        if choice == 0:
            state.run_outcome['path'] = 'combat'
        else:
            state.run_outcome['path'] = 'puzzle'
        typewriter_print("You have made your choice and must proceed.")
        time.sleep(2)
        return True

    else:
        print(f"WARNING: Unknown challenge type '{challenge_type}'. Skipping.")
        time.sleep(2)
        return True

# --- Main Game Loop Function ---
def play_game(player_id, instructions):
    """
    This function contains the main game loop, ensuring it runs after loading.
    """
    knobs = instructions.get('knobs', {})
    content = instructions.get('content', {})
    run_index = instructions.get('meta', {}).get('run_index', 1)
    
    while True: # This is the retry loop for the current level
        state = GameState(player_id, run_index)
        
        adventure_success = True
        for scene in content.get('scenes', []):
            clear_screen()
            typewriter_print(scene['intro_text'])
            if not run_challenge(state, scene['challenge']):
                adventure_success = False
                break
        
        if not adventure_success:
            continue # If a challenge was failed, restart the 'while' loop
            
        # If all scenes passed, face the final boss
        clear_screen()
        typewriter_print("You've reached the Spire's peak!")
        final_boss_challenge = {
            "type": "QTE",
            "prompt": "The Dragon Ignis attacks! Defend the princess!",
            "key": "S",
            "presses": 20,
            "time_limit": 4.0
        }
        if not run_challenge(state, final_boss_challenge):
            continue
        
        # --- VICTORY ---
        state.run_outcome['result'] = 'win'
        state.stats['time_s'] = int(time.time() - state.session_start_time)
        final_data = generate_output_json(state, knobs)
        output_filename = f"server_input_{player_id}.json"
        with open(output_filename, 'w') as f:
            json.dump(final_data, f, indent=2)
        
        clear_screen()
        typewriter_print("--- VICTORY! ---")
        print(f"You have rescued the princess, {player_id}!")
        print(f"Run the AI agent on '{output_filename}' to evolve your persona and generate the next level!")
        break # Exit the retry loop upon victory

# --- Main Execution Block ---
if __name__ == "__main__":
    player_id = input("Enter your player name: ").strip() or f"player_{random.randint(100, 999)}"
    input_file = "gameInput.json"
    
    clear_screen()
    if not os.path.exists(input_file):
        print(f"FATAL ERROR: '{input_file}' not found!")
        print("Please run the AI agent first to generate the level instructions.")
        exit()
        
    print(f"--- LOADING LEVEL INSTRUCTIONS FROM '{input_file}' ---")
    with open(input_file, 'r') as f:
        instructions = json.load(f)
    time.sleep(2)

    # This was the missing piece: actually calling the function to start the game
    play_game(player_id, instructions)