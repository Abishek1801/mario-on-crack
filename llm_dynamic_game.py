import json
import os
import time
import uuid
import random

# All helper functions (get_char_non_blocking, etc.) are the same.
# Condensed for brevity.
try:
    import msvcrt
    def get_char_non_blocking():
        if msvcrt.kbhit(): return msvcrt.getch().decode('utf-8').upper()
        return None
except ImportError:
    import sys, tty, termios
    def get_char_non_blocking():
        fd = sys.stdin.fileno(); old_settings = termios.tcgetattr(fd)
        try:
            tty.setcbreak(sys.stdin.fileno()); import select
            if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []): return sys.stdin.read(1).upper()
        finally: termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return None
def clear_screen(): os.system('cls' if os.name == 'nt' else 'clear')
def typewriter_print(text, delay=0.03):
    for char in text: print(char, end='', flush=True); time.sleep(delay)
    print()
def get_player_choice(prompt, options):
    while True:
        typewriter_print(prompt)
        for i, text in enumerate(options, 1): print(f"  [{i}] {text}")
        choice = input("> ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(options): return int(choice) - 1
        else: print("\nInvalid choice."); time.sleep(1)

# GameState class is unchanged.
class GameState:
    def __init__(self, player_id): self.player_id = player_id; self.session_start_time = time.time(); self.run_outcome = {"result": "loss", "path": "exploration"}; self.stats = {"time_s": 0, "deaths": 0, "retries": 0, "distance_traveled": 0, "jumps": 0, "hint_offers": 0, "hints_used": 0, "riddles_attempted": 0, "riddles_correct": 0, "combats_initiated": 0, "combats_won": 0, "collectibles_found": 0}
    def increment_stat(self, key, value=1):
        if key in self.stats: self.stats[key] += value
    def handle_death(self, message):
        clear_screen(); typewriter_print(message); typewriter_print("\nYou awaken back at the start."); time.sleep(3); self.increment_stat('deaths'); self.increment_stat('retries'); return False

# JSON Generator is unchanged.
def generate_output_json(state): # This function remains exactly the same as the previous version.
    events_digest = [{"type": "death", "count": state.stats['deaths']},{"type": "fail.retry", "count": state.stats['retries']},{"type": "combat.start", "count": state.stats['combats_initiated']},{"type": "combat.win", "count": state.stats['combats_won']},{"type": "puzzle.attempt", "count": state.stats['riddles_attempted']}]; output = {"schema_version": "1.0", "player_id": state.player_id, "session_id": f"sess_{uuid.uuid4().hex[:12]}", "run_index": state.stats['retries'] + 1, "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "run_outcome": state.run_outcome, "stats": state.stats, "events_digest": [e for e in events_digest if e['count'] > 0], "config_used": {"mode": "challenge", "knobs": {"enemy_count": 3, "enemy_speed": 1.3, "puzzle_gate_ratio": 0.4, "collectible_density": 0.25, "hint_delay_ms": 12000, "breadcrumb_brightness": 0.35}, "layout_seed": f"seed_{random.randint(100000, 999999)}"}, "performance_summary": {"avg_enemy_engagement_time": 3.2, "puzzle_success_rate": state.stats['riddles_correct'] / state.stats['riddles_attempted'] if state.stats['riddles_attempted'] > 0 else 0, "exploration_ratio": 0.0, "hint_reliance": 0.0}}; return output

# --- GENERIC CHALLENGE RUNNER ---
def run_challenge(state, challenge):
    """Reads a challenge object from the JSON and executes the correct game mechanic."""
    challenge_type = challenge.get('type')
    
    # ---- QTE Challenge ----
    if challenge_type == 'QTE':
        state.increment_stat('combats_initiated')
        typewriter_print(challenge.get('prompt', 'Prepare for battle!'))
        key, presses, time_limit = challenge['key'], challenge['presses'], challenge['time_limit']
        print(f"MASH '{key}' {presses} TIMES IN {time_limit} SECONDS!", flush=True)
        start_time = time.time(); press_count = 0
        while time.time() - start_time < time_limit:
            if get_char_non_blocking() == key:
                press_count += 1; print(key, end='', flush=True)
                if press_count >= presses:
                    print("\n"); typewriter_print("Success!"); state.increment_stat('combats_won'); time.sleep(2); return True
        return state.handle_death("Too slow!")

    # ---- Riddle Challenge ----
    elif challenge_type == 'RIDDLE':
        state.increment_stat('riddles_attempted')
        typewriter_print(challenge.get('prompt', 'Solve this riddle:'))
        typewriter_print(f"\"{challenge['riddle_text']}\"")
        start_time = time.time()
        answer = input("> ").strip().lower()
        if time.time() - start_time > challenge['time_limit']: return state.handle_death("You ran out of time!")
        if challenge['answer'].lower() in answer:
            typewriter_print("Correct!"); state.increment_stat('riddles_correct'); time.sleep(2); return True
        return state.handle_death("That is not the answer.")

    # ---- Sequence Memory Challenge ----
    elif challenge_type == 'SEQUENCE_MEMORY':
        state.increment_stat('riddles_attempted') # Counts as a puzzle
        typewriter_print(challenge.get('prompt', 'Repeat the sequence.'))
        sequence = challenge['sequence']
        for item in sequence:
            print(f"  {item}  ", end='', flush=True); time.sleep(1.5); print("\r" + " "*20 + "\r", end='', flush=True)
        typewriter_print("Now, enter the sequence, separated by spaces.")
        user_input = input("> ").strip().upper().split()
        if user_input == sequence:
            typewriter_print("Perfect memory!"); state.increment_stat('riddles_correct'); time.sleep(2); return True
        return state.handle_death("Your memory fails you.")
    
    # ---- Dilemma Challenge ----
    elif challenge_type == 'DILEMMA':
        options = challenge['options']
        choice = get_player_choice(challenge.get('prompt', 'A difficult choice...'), options)
        # We can optionally set the path based on the dilemma choice
        if choice == 0: state.run_outcome['path'] = 'combat'
        else: state.run_outcome['path'] = 'puzzle'
        typewriter_print("You have made your choice. The consequences are unknown, but you must proceed.")
        time.sleep(2)
        return True # Dilemmas don't have a "fail" state

    else:
        print(f"WARNING: Unknown challenge type '{challenge_type}'. Skipping."); time.sleep(2); return True

# --- MAIN GAME LOOP ---
if __name__ == "__main__":
    player_id = input("Enter your player name: ").strip() or f"player_{random.randint(100, 999)}"
    
    if os.path.exists("personalized_content.json"):
        content_file = "personalized_content.json"; msg = "--- LOADING LLM-GENERATED ADVENTURE ---"
    else:
        content_file = "default_content.json"; msg = "--- NO PERSONALIZED DATA FOUND, LOADING DEFAULT ADVENTURE ---"
    
    clear_screen(); print(msg)
    try:
        with open(content_file, 'r') as f: content = json.load(f)
    except FileNotFoundError:
        print(f"FATAL: Could not find '{content_file}'."); exit()
    time.sleep(2)

    while True: # Retry loop
        state = GameState(player_id)
        
        adventure_success = True
        for scene in content.get('scenes', []):
            clear_screen()
            typewriter_print(scene['intro_text'])
            if not run_challenge(state, scene['challenge']):
                adventure_success = False; break
        
        if not adventure_success: continue
            
        # --- FIXED FINAL BOSS ---
        # Instead of calling a non-existent function, we build a challenge object
        # and pass it to our universal challenge runner.
        clear_screen()
        typewriter_print("You've reached the end of the path... the Spire's peak awaits!")
        
        final_boss_challenge = {
            "type": "QTE",
            "prompt": "The Dragon Ignis awakens! Defend yourself!",
            "key": "S",
            "presses": 20,
            "time_limit": 4.0
        }
        
        if not run_challenge(state, final_boss_challenge):
            continue
        
        # --- VICTORY ---
        state.run_outcome['result'] = 'win'; state.stats['time_s'] = int(time.time() - state.session_start_time)
        final_data = generate_output_json(state); output_filename = f"server_input_{player_id}.json"
        with open(output_filename, 'w') as f: json.dump(final_data, f, indent=2)
        
        clear_screen(); typewriter_print("--- VICTORY! ---")
        print(f"You have rescued the princess, {player_id}!")
        print(f"Run the LLM AGENT on '{output_filename}' to create your next, unique adventure!")
        break