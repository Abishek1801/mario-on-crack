import json

def run_interview():
    """
    A simple, non-LLM interview to set baseline persona traits.
    This is faster and more reliable for an initial setup.
    """
    print("--- CHRONICLE PLAYER SETUP ---")
    print("Answer two questions to establish your starting persona.")
    
    # Start with a neutral baseline
    traits = { "aggression": 0.5, "stealth": 0.5, "curiosity": 0.5, "puzzle_affinity": 0.5, "independence": 0.5, "resilience": 0.5, "goal_focus": 0.5 }

    # Question 1
    print("\n[1] A guard blocks your path. Do you:")
    print("  [1] Fight them head-on.")
    print("  [2] Sneak around them.")
    choice1 = input("> ")
    if choice1 == '1':
        traits['aggression'] += 0.2
        traits['stealth'] -= 0.1
    elif choice1 == '2':
        traits['aggression'] -= 0.1
        traits['stealth'] += 0.2

    # Question 2
    print("\n[2] You face a locked door with a riddle. Do you:")
    print("  [1] Try to solve the riddle.")
    print("  [2] Try to break the door down.")
    choice2 = input("> ")
    if choice2 == '1':
        traits['puzzle_affinity'] += 0.2
        traits['curiosity'] += 0.1
    elif choice2 == '2':
        traits['goal_focus'] += 0.2
        traits['puzzle_affinity'] -= 0.1

    # Normalize values to be between 0.0 and 1.0
    for key in traits:
        traits[key] = round(max(0.0, min(1.0, traits[key])), 2)

    return traits

if __name__ == "__main__":
    initial_traits = run_interview()
    
    # Create the full persona structure you defined
    player_persona = {
        "schema_version": "1.0",
        "player_id": "user_123", # This would be dynamically assigned in a real system
        "game_id": "mario-on-crack",
        "persona": {
            "global": {"traits": initial_traits, "source": {"provider": "initial_interview"}},
            "game": {"traits": initial_traits, "source": {"provider": "initial_interview"}}
        }
    }
    
    output_filename = "player_persona.json"
    with open(output_filename, 'w') as f:
        json.dump(player_persona, f, indent=2)

    print(f"\nSuccess! Your starting persona has been saved to '{output_filename}'.")
    print("You can now run the Chronicle Agent to generate your first level.")