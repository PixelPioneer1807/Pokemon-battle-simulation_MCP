# In app/services/llm_client.py
import os
import json
from groq import Groq
import random

async def get_strategic_move_and_commentary(attacker, defender, turn_count) -> dict:
    """
    Asks the LLM to choose a strategic move and provide separate strategy and commentary.
    """
    try:
        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

        available_moves = [
            {
                "name": move.name, "power": move.power, "type": move.move_type,
                "cost": move.power or 0,
                "effectiveness": 1.0 # Will be updated below
            }
            for move in attacker.moves if (move.power or 0) <= attacker.attack_points
        ]

        if not available_moves:
            return {
                "chosen_move": None,
                "strategy": f"{attacker.name} needs to build up more Attack Points.",
                "commentary": f"{attacker.name} conserves its energy, waiting for the right moment to strike!"
            }

        # Add effectiveness to help the LLM make better decisions
        from .battle_engine import TYPE_EFFECTIVENESS
        for move in available_moves:
            effectiveness = 1.0
            if move["type"] in TYPE_EFFECTIVENESS:
                for def_type in defender.types:
                    effectiveness *= TYPE_EFFECTIVENESS[move["type"]].get(def_type, 1)
            move["effectiveness"] = effectiveness


        prompt = f"""
        You are a master Pokémon battle strategist and a hype commentator.

        **Battle State (Turn {turn_count}):**
        - **Your Pokémon (Attacker):** {attacker.name} (HP: {attacker.current_hp}/{attacker.max_hp}, AP: {attacker.attack_points}, Types: {', '.join(attacker.types)})
        - **Opponent (Defender):** {defender.name} (HP: {defender.current_hp}/{defender.max_hp}, Types: {', '.join(defender.types)})

        **Your Available Moves:**
        {json.dumps(available_moves, indent=2)}

        **Your Task:**
        1.  **Strategize:** Choose the best move. Consider type effectiveness, move power, and remaining AP. Your goal is to win the battle.
        2.  **Commentate:** Write a short, exciting, one-sentence commentary for the chosen action.

        **Provide your response in this exact JSON format:**
        {{
          "chosen_move": "move-name",
          "strategy": "Your brief explanation for choosing this move.",
          "commentary": "Your exciting play-by-play commentary for this turn."
        }}
        """

        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile", # Using a more powerful model for better strategy
            temperature=0.8,
            response_format={"type": "json_object"},
        )

        response_text = chat_completion.choices[0].message.content
        return json.loads(response_text)

    except Exception as e:
        print(f"LLM Error: {e}") # For debugging
        # Failsafe: If LLM fails, pick the highest power move the Pokemon can afford
        if not available_moves: return {"chosen_move": None, "strategy": "Failsafe: No moves available.", "commentary": "Failsafe: Attack failed."}
        
        best_move = max(available_moves, key=lambda x: x['power'])
        return {
            "chosen_move": best_move['name'],
            "strategy": f"Failsafe: The LLM failed, so {attacker.name} chose its strongest available move: {best_move['name'].replace('-', ' ').title()}.",
            "commentary": f"Under pressure, {attacker.name} unleashes a powerful {best_move['name'].replace('-', ' ').title()}!"
        }