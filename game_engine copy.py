# FILE: game_engine.py (Corrected with a safety check for challenge data type)

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
class GameState:
    def __init__(self, player_id, run_index):
        self.player_id = player_id; self.run_index = run_index; self.session_start_time = time.time(); self.run_outcome = {"result": "loss", "path": "exploration"}; self.stats = {"time_s": 0, "deaths": 0, "retries": 0, "distance_traveled": 0, "jumps": 0, "hint_offers": 0, "hints_used": 0, "riddles_attempted": 0, "riddles_correct": 0, "combats_initiated": 0, "combats_won": 0, "collectibles_found": 0}
    def increment_stat(self, key, value=1):
        if key in self.stats: self.stats[key] += value
    def handle_death(self, message):
        clear_screen(); typewriter_print(message); typewriter_print("\nYou awaken back at the start of the adventure."); time.sleep(3); self.increment_stat('deaths'); self.increment_stat('retries'); return False

# --- JSON Report Card Generator ---
def generate_output_json(state, knobs):
    events_digest = [{"type": "death", "count": state.stats['deaths']},{"type": "fail.retry", "count": state.stats['retries']},{"type": "combat.start", "count": state.stats['combats_initiated']},{"type": "combat.win", "count": state.stats['combats_won']},{"type": "puzzle.attempt", "count": state.stats['riddles_attempted']}]; output = {"schema_version": "1.0", "player_id": state.player_id, "session_id": f"sess_{uuid.uuid4().hex[:12]}", "run_index": state.run_index, "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "run_outcome": state.run_outcome, "stats": state.stats, "events_digest": [e for e in events_digest if e['count'] > 0], "config_used": {"mode": "challenge", "knobs": knobs}, "performance_summary": {"avg_enemy_engagement_time": 3.2, "puzzle_success_rate": state.stats['riddles_correct'] / state.stats['riddles_attempted'] if state.stats['riddles_attempted'] > 0 else 0, "exploration_ratio": 0.0, "hint_reliance": 0.0}}; return output

# --- Generic Challenge Runner ---
def run_challenge(state, challenge):
    challenge_type = challenge.get('type')
    if challenge_type == 'QTE':
        state.increment_stat('combats_initiated'); typewriter_print(challenge.get('prompt', 'Prepare!')); key, presses, time_limit = challenge['key'], challenge['presses'], challenge['time_limit']; print(f"MASH '{key}' {presses} TIMES IN {time_limit} SECONDS!", flush=True); start_time = time.time(); press_count = 0
        while time.time() - start_time < time_limit:
            if get_char_non_blocking() == key:
                press_count += 1; print(key, end='', flush=True)
                if press_count >= presses: print("\n"); typewriter_print("Success!"); state.increment_stat('combats_won'); time.sleep(2); return True
        return state.handle_death("Too slow!")
    elif challenge_type == 'RIDDLE':
        state.increment_stat('riddles_attempted'); typewriter_print(challenge.get('prompt', 'Solve:')); typewriter_print(f"\"{challenge['riddle_text']}\""); start_time = time.time(); answer = input("> ").strip().lower()
        if time.time() - start_time > challenge['time_limit']: return state.handle_death("Out of time!")
        if challenge['answer'].lower() in answer: typewriter_print("Correct!"); state.increment_stat('riddles_correct'); time.sleep(2); return True
        return state.handle_death("Incorrect.")
    elif challenge_type == 'SEQUENCE_MEMORY':
        state.increment_stat('riddles_attempted'); typewriter_print(challenge.get('prompt', 'Memorize:')); sequence = challenge['sequence']
        for item in sequence: print(f"  {item}  ", end='', flush=True); time.sleep(1.5); print("\r" + " " * 20 + "\r", end='', flush=True)
        user_input_upper = input("Enter the sequence: > ").strip().upper().split(); correct_sequence_upper = [item.upper() for item in sequence]
        if user_input_upper == correct_sequence_upper: typewriter_print("Perfect memory!"); state.increment_stat('riddles_correct'); time.sleep(2); return True
        return state.handle_death("Memory fails you.")
    elif challenge_type == 'DILEMMA':
        options = challenge['options']; choice = get_player_choice(challenge.get('prompt', 'Choose...'), options)
        if choice == 0: state.run_outcome['path'] = 'combat'
        else: state.run_outcome['path'] = 'puzzle'
        typewriter_print("You proceed."); time.sleep(2); return True
    else: print(f"WARNING: Unknown challenge type '{challenge_type}'."); time.sleep(2); return True

# --- Main Game Loop Function ---
def play_game(player_id, instructions):
    knobs = instructions.get('knobs', {}); content = instructions.get('content', {}); run_index = instructions.get('meta', {}).get('run_index', 1)
    while True: # Retry loop
        state = GameState(player_id, run_index)
        adventure_success = True
        for scene in content.get('scenes', []):
            clear_screen()
            intro = scene.get('intro_text', "You proceed to the next area...")
            typewriter_print(intro)
            
            # --- THIS IS THE BUG FIX ---
            # 1. Safely get the challenge data.
            challenge_data = scene.get('challenge')
            
            # 2. Check if the data is a dictionary before trying to use it.
            if isinstance(challenge_data, dict):
                if not run_challenge(state, challenge_data):
                    adventure_success = False
                    break
            elif challenge_data is not None:
                # If it's not a dictionary (e.g., a string), print a warning and skip.
                print(f"WARNING: Malformed challenge data from LLM (not a dictionary). Skipping scene.")
                time.sleep(3)
            # If challenge_data is None, just move on to the next scene.

        if not adventure_success: continue
            
        clear_screen(); typewriter_print("You've reached the Spire's peak!")
        final_boss_challenge = {"type": "QTE", "prompt": "The Dragon Ignis attacks!", "key": "S", "presses": 20, "time_limit": 4.0}
        if not run_challenge(state, final_boss_challenge): continue
        
        state.run_outcome['result'] = 'win'; state.stats['time_s'] = int(time.time() - state.session_start_time)
        final_data = generate_output_json(state, knobs); output_filename = f"run_report_{player_id}.json"
        with open(output_filename, 'w') as f: json.dump(final_data, f, indent=2)
        
        clear_screen(); typewriter_print("--- VICTORY! ---")
        print(f"You rescued the princess, {player_id}!")
        print(f"Game finished! Report saved to '{output_filename}'.")
        print("Run the Chronicle Agent on this report to generate your next level.")
        break

# --- Main Execution Block ---
if __name__ == "__main__":
    player_id = input("Enter your player name: ").strip() or "player123"
    instructions_file = "game_instructions.json"
    
    clear_screen()
    if not os.path.exists(instructions_file):
        print(f"FATAL: '{instructions_file}' not found! Run the Chronicle Agent first.")
        exit()
        
    print(f"--- LOADING LEVEL INSTRUCTIONS FROM '{instructions_file}' ---")
    with open(instructions_file, 'r') as f:
        instructions = json.load(f)
    time.sleep(2)

    play_game(player_id, instructions)