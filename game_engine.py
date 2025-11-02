# FILE: game_engine.py (Updated to read player_id from instructions)

# --- All helper functions, classes, and validators are the same ---
# For absolute clarity, the full, final code is provided below.
import json; import os; import time; import uuid; import random; import requests
BACKEND_URL = "http://192.168.0.199:7769"
try:
    import msvcrt
    def get_char_non_blocking():
        if msvcrt.kbhit(): return msvcrt.getch().decode('utf-8').upper()
        return None
except ImportError:
    import sys, tty, termios, select
    def get_char_non_blocking():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                return sys.stdin.read(1).upper()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return None
def clear_screen(): os.system('cls' if os.name == 'nt' else 'clear')
def typewriter_print(text, delay=0.03):
    for char in text: print(char, end='', flush=True); time.sleep(delay)
    print()
def get_player_choice(prompt, options):
    while True:
        typewriter_print(prompt);
        for i, text in enumerate(options, 1): print(f"  [{i}] {text}")
        choice = input("> ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(options): return int(choice) - 1
        else: print("\nInvalid choice."); time.sleep(1)
class GameState:
    def __init__(self, player_id, run_index): self.player_id=player_id; self.run_index=run_index; self.session_start_time=time.time(); self.run_outcome={"result":"loss","path":"exploration"}; self.stats={"time_s":0,"deaths":0,"retries":0,"distance_traveled":0,"jumps":0,"hint_offers":0,"hints_used":0,"riddles_attempted":0,"riddles_correct":0,"combats_initiated":0,"combats_won":0,"collectibles_found":0}
    def increment_stat(self, key, value=1):
        if key in self.stats: self.stats[key]+=value
    def handle_death(self, message):
        clear_screen(); typewriter_print(message); typewriter_print("\nYou awaken back at the start."); time.sleep(3); self.increment_stat('deaths'); self.increment_stat('retries'); return False
def generate_output_json(state, knobs):
    events_digest=[{"type":"death","count":state.stats['deaths']},{"type":"fail.retry","count":state.stats['retries']},{"type":"combat.start","count":state.stats['combats_initiated']},{"type":"combat.win","count":state.stats['combats_won']},{"type":"puzzle.attempt","count":state.stats['riddles_attempted']}];output={"schema_version":"1.0","player_id":state.player_id,"session_id":f"sess_{uuid.uuid4().hex[:12]}","run_index":state.run_index,"completed_at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"run_outcome":state.run_outcome,"stats":state.stats,"events_digest":[e for e in events_digest if e['count']>0],"config_used":{"mode":"challenge","knobs":knobs},"performance_summary":{"avg_enemy_engagement_time":3.2,"puzzle_success_rate":state.stats['riddles_correct']/state.stats['riddles_attempted'] if state.stats['riddles_attempted']>0 else 0,"exploration_ratio":0.0,"hint_reliance":0.0}};return output
def is_challenge_valid(challenge):
    challenge_type=challenge.get('type');
    if challenge_type=='QTE':return all(k in challenge for k in['key','presses','time_limit'])
    elif challenge_type=='RIDDLE':return all(k in challenge for k in['riddle_text','answer','time_limit'])
    elif challenge_type=='SEQUENCE_MEMORY':return'sequence'in challenge and isinstance(challenge['sequence'],list)
    elif challenge_type=='DILEMMA':return'options'in challenge and isinstance(challenge['options'],list)
    elif challenge_type=='JUMP_CHASM':return'success_chance'in challenge
    elif challenge_type=='FIND_COLLECTIBLE':return'description'in challenge
    return False
def run_challenge(state, challenge):
    if not is_challenge_valid(challenge):
        print(f"WARNING: Challenge of type '{challenge.get('type')}' is missing data. Skipping.")
        time.sleep(3)
        return True

    challenge_type = challenge.get('type')

    if challenge_type == 'QTE':
        state.increment_stat('combats_initiated')
        typewriter_print(challenge.get('prompt', 'Prepare!'))
        key = challenge['key']
        presses = challenge['presses']
        time_limit = challenge['time_limit']
        print(f"MASH '{key}' {presses} TIMES IN {time_limit} SECONDS!", flush=True)
        start_time = time.time()
        press_count = 0
        while time.time() - start_time < time_limit:
            ch = get_char_non_blocking()
            if ch == key:
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
        typewriter_print(challenge.get('prompt', 'Solve:'))
        typewriter_print(f"\"{challenge['riddle_text']}\"")
        answer = input("> ").strip().lower()
        if challenge['answer'].lower() in answer:
            typewriter_print("Correct!")
            state.increment_stat('riddles_correct')
            time.sleep(2)
            return True
        if 'hint_text' in challenge:
            state.increment_stat('hint_offers')
            typewriter_print("Not quite. Hint? (y/n)")
            if input("> ").strip().lower() == 'y':
                state.increment_stat('hints_used')
                typewriter_print(f"HINT: {challenge['hint_text']}")
                answer = input("> ").strip().lower()
                if challenge['answer'].lower() in answer:
                    typewriter_print("Correct, with a hint!")
                    state.increment_stat('riddles_correct')
                    time.sleep(2)
                    return True
        return state.handle_death("Incorrect.")

    elif challenge_type == 'JUMP_CHASM':
        typewriter_print(challenge.get('prompt', 'A chasm...'))
        input("Press Enter to jump...")
        state.increment_stat('jumps')
        if random.random() < challenge['success_chance']:
            typewriter_print("You land safely!")
            time.sleep(2)
            return True
        else:
            return state.handle_death("You fall into the abyss.")

    elif challenge_type == 'FIND_COLLECTIBLE':
        typewriter_print(challenge.get('description'))
        state.increment_stat('collectibles_found')
        input("Press Enter to continue...")
        return True

    elif challenge_type == 'SEQUENCE_MEMORY':
        state.increment_stat('riddles_attempted')
        typewriter_print(challenge.get('prompt', 'Memorize:'))
        sequence = challenge['sequence']
        for item in sequence:
            print(f"  {item}  ", end='', flush=True)
            time.sleep(1.5)
            print("\r" + " " * 20 + "\r", end='', flush=True)
        user_input_upper = input("Enter sequence: > ").strip().upper().split()
        correct_sequence_upper = [item.upper() for item in sequence]
        if user_input_upper == correct_sequence_upper:
            typewriter_print("Perfect memory!")
            state.increment_stat('riddles_correct')
            time.sleep(2)
            return True
        return state.handle_death("Memory fails you.")

    elif challenge_type == 'DILEMMA':
        options = challenge['options']
        choice = get_player_choice(challenge.get('prompt', 'Choose...'), options)
        if choice == 0:
            state.run_outcome['path'] = 'combat'
        else:
            state.run_outcome['path'] = 'puzzle'
        typewriter_print("You proceed.")
        time.sleep(2)
        return True

    return True
def submit_run_report(state, knobs, game_context):
    print("\nGAME: Compiling run report...");server_input={"schema_version":"1.0","player_id":state.player_id,"session_id":f"sess_{uuid.uuid4().hex[:8]}","run_index":state.run_index,"completed_at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"game_context":game_context,"run_outcome":state.run_outcome,"stats":state.stats,"config_used":{"mode":"challenge","knobs":knobs,"layout_seed":f"seed_{random.randint(100000,999999)}"}}
    payload={"serverInput":server_input};url=f"{BACKEND_URL}/sm/save"
    print("GAME: Submitting run report...");
    try:
        response=requests.post(url,json=payload)
        if response.status_code==200:print("GAME: Report submitted!");print(response.json())
        else:print(f"GAME ERROR: Failed to submit. Status: {response.status_code}, Response: {response.text}")
    except requests.exceptions.ConnectionError:print(f"GAME CRITICAL ERROR: Could not connect to backend.")
def play_game(player_id, instructions, game_context):
    knobs=instructions.get('knobs',{});content=instructions.get('content',{});run_index=1
    state=GameState(player_id,run_index)
    while True:
        adventure_success=True
        for scene in content.get('scenes',[]):
            clear_screen();intro=scene.get('intro_text',"You proceed...");typewriter_print(intro);state.increment_stat('distance_traveled',50)
            challenge_data=scene.get('challenge')
            if isinstance(challenge_data,dict):
                if not run_challenge(state,challenge_data):adventure_success=False;break
            else:print(f"WARNING: Malformed challenge data. Skipping.");time.sleep(2)
        if not adventure_success:continue
        clear_screen();typewriter_print("You've reached the Spire's peak!")
        final_boss_challenge={"type":"QTE","prompt":"The Dragon Ignis attacks!","key":"S","presses":15,"time_limit":4.0}
        if not run_challenge(state,final_boss_challenge):continue
        state.run_outcome['result']='win';state.stats['time_s']=int(time.time()-state.session_start_time)
        submit_run_report(state,knobs,game_context)
        clear_screen();typewriter_print("--- VICTORY! ---")
        print(f"You rescued the princess, {player_id}!");print("Your performance has been saved to your Supermemory profile.")
        break

# --- MAIN EXECUTION BLOCK (UPDATED) ---
if __name__ == "__main__":
    # --- CHANGE: REMOVED the input() prompt for player_id ---
    instructions_file = "game_instructions.json"
    game_context = {"game_id": "mario-on-crack", "game_title": "Dragon's Spire", "genre_ids": ["adventure"], "platform_ids": ["pc"]}
    
    clear_screen()
    if not os.path.exists(instructions_file):
        print(f"FATAL: '{instructions_file}' not found! Run 'prepare_level.py <player_id>' first.")
        exit()
        
    print(f"--- LOADING LEVEL: '{instructions_file}' ---");
    with open(instructions_file,'r') as f:
        instructions = json.load(f)
    time.sleep(2)
    
    # --- CHANGE: READ the player_id from the loaded instructions ---
    player_id = instructions.get("meta", {}).get("player_id", "unknown_player")
    if player_id == "unknown_player":
        print("FATAL ERROR: player_id not found in 'game_instructions.json'. Cannot proceed.")
        exit()

    print(f"--- STARTING GAME FOR PLAYER: {player_id} ---")
    time.sleep(2)
    
    play_game(player_id, instructions, game_context)