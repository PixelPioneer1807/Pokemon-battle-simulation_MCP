# In app/services/battle_engine.py
import random
from typing import List, Optional, Tuple
from ..models.pydantic_models import PokemonData, MoveInfo

# UPDATED: This is the complete type effectiveness chart for all 18 types.
TYPE_EFFECTIVENESS = {
    'normal': {'rock': 0.5, 'ghost': 0, 'steel': 0.5},
    'fire': {'fire': 0.5, 'water': 0.5, 'grass': 2, 'ice': 2, 'bug': 2, 'rock': 0.5, 'dragon': 0.5, 'steel': 2},
    'water': {'fire': 2, 'water': 0.5, 'grass': 0.5, 'ground': 2, 'rock': 2, 'dragon': 0.5},
    'grass': {'fire': 0.5, 'water': 2, 'grass': 0.5, 'poison': 0.5, 'ground': 2, 'flying': 0.5, 'bug': 0.5, 'rock': 2, 'dragon': 0.5, 'steel': 0.5},
    'electric': {'water': 2, 'grass': 0.5, 'electric': 0.5, 'ground': 0, 'flying': 2, 'dragon': 0.5},
    'ice': {'fire': 0.5, 'water': 0.5, 'grass': 2, 'ice': 0.5, 'ground': 2, 'flying': 2, 'dragon': 2, 'steel': 0.5},
    'fighting': {'normal': 2, 'ice': 2, 'poison': 0.5, 'flying': 0.5, 'psychic': 0.5, 'bug': 0.5, 'rock': 2, 'ghost': 0, 'dark': 2, 'steel': 2, 'fairy': 0.5},
    'poison': {'grass': 2, 'poison': 0.5, 'ground': 0.5, 'rock': 0.5, 'ghost': 0.5, 'steel': 0, 'fairy': 2},
    'ground': {'fire': 2, 'grass': 0.5, 'electric': 2, 'poison': 2, 'flying': 0, 'bug': 0.5, 'rock': 2, 'steel': 2},
    'flying': {'grass': 2, 'electric': 0.5, 'fighting': 2, 'bug': 2, 'rock': 0.5, 'steel': 0.5},
    'psychic': {'fighting': 2, 'poison': 2, 'psychic': 0.5, 'dark': 0, 'steel': 0.5},
    'bug': {'fire': 0.5, 'grass': 2, 'fighting': 0.5, 'poison': 0.5, 'flying': 0.5, 'psychic': 2, 'ghost': 0.5, 'dark': 2, 'steel': 0.5, 'fairy': 0.5},
    'rock': {'fire': 2, 'ice': 2, 'fighting': 0.5, 'ground': 0.5, 'flying': 2, 'bug': 2, 'steel': 0.5},
    'ghost': {'normal': 0, 'psychic': 2, 'ghost': 2, 'dark': 0.5},
    'dragon': {'dragon': 2, 'steel': 0.5, 'fairy': 0},
    'dark': {'fighting': 0.5, 'psychic': 2, 'ghost': 2, 'dark': 0.5, 'fairy': 0.5},
    'steel': {'fire': 0.5, 'water': 0.5, 'electric': 0.5, 'ice': 2, 'rock': 2, 'steel': 0.5, 'fairy': 2},
    'fairy': {'fighting': 2, 'poison': 0.5, 'dragon': 2, 'dark': 2, 'steel': 0.5}
}


class BattlePokemon:
    """Represents a Pokémon's state within a battle."""
    def __init__(self, data: PokemonData):
        self.name = data.name.capitalize()
        self.types = data.types
        stats = {s.name: s.base_stat for s in data.base_stats}
        
        self.max_hp = stats.get('hp', 1)
        self.current_hp = self.max_hp
        self.attack = stats.get('attack', 1)
        self.defense = stats.get('defense', 1)
        self.special_attack = stats.get('special-attack', 1)
        self.special_defense = stats.get('special-defense', 1)
        self.speed = stats.get('speed', 1)
        
        self.moves = [move for move in data.moves if move.power is not None and move.power > 0]
        self.status: Optional[str] = None

class BattleEngine:
    """Manages the logic and state of a Pokémon battle."""
    def __init__(self, pokemon1_data: PokemonData, pokemon2_data: PokemonData):
        self.p1 = BattlePokemon(pokemon1_data)
        self.p2 = BattlePokemon(pokemon2_data)
        self.battle_log: List[str] = []
        self.turn_count = 0
        
    def _select_move(self, attacker: BattlePokemon, defender: BattlePokemon) -> Optional[MoveInfo]:
        if not attacker.moves:
            return None
        self.battle_log.append(f"AI for {attacker.name} is choosing a move...")
        move_scores = {}
        for move in attacker.moves:
            effectiveness = 1.0
            if move.move_type in TYPE_EFFECTIVENESS:
                for def_type in defender.types:
                    effectiveness *= TYPE_EFFECTIVENESS[move.move_type].get(def_type, 1)
            score = (move.power or 0) * effectiveness
            move_scores[move.name] = score
            self.battle_log.append(f"  - Assessing '{move.name.title()}': Power({move.power}) * Effectiveness({effectiveness}x) = Score({score})")
        if not move_scores:
            return None
        max_score = max(move_scores.values())
        if max_score <= 0:
             return random.choice(attacker.moves) if attacker.moves else None
        good_moves = [move for move in attacker.moves if move_scores.get(move.name, 0) >= max_score * 0.8]
        selected_move = random.choice(good_moves) if good_moves else None
        if selected_move:
            self.battle_log.append(f"AI selected '{selected_move.name.title()}' from its best options.")
        return selected_move

    def _calculate_damage(self, move: MoveInfo, attacker: BattlePokemon, defender: BattlePokemon) -> Tuple[int, float]:
        if move.damage_class == 'physical':
            attack_stat = attacker.attack
            defense_stat = defender.defense
        elif move.damage_class == 'special':
            attack_stat = attacker.special_attack
            defense_stat = defender.special_defense
        else:
            return 0, 1.0
        damage = (((2/5 + 2) * move.power * attack_stat / defense_stat) / 50) + 2
        effectiveness = 1.0
        if move.move_type in TYPE_EFFECTIVENESS:
            for def_type in defender.types:
                effectiveness *= TYPE_EFFECTIVENESS[move.move_type].get(def_type, 1)
        total_damage = int(damage * effectiveness)
        return total_damage, effectiveness

    def _apply_turn(self, attacker: BattlePokemon, defender: BattlePokemon):
        if attacker.current_hp <= 0:
            return
        if attacker.status == 'Paralyzed' and random.random() < 0.25:
            self.battle_log.append(f"{attacker.name} is paralyzed! It can't move!")
            return
        move = self._select_move(attacker, defender)
        if not move:
            self.battle_log.append(f"{attacker.name} has no damaging moves to use!")
            return
        damage, effectiveness = self._calculate_damage(move, attacker, defender)
        defender.current_hp = max(0, defender.current_hp - damage)
        log_msg = f"{attacker.name} used {move.name.replace('-', ' ').title()}!"
        if effectiveness > 1:
            log_msg += f" It's super effective! ({effectiveness}x)"
        elif effectiveness < 1 and effectiveness > 0:
            log_msg += f" It's not very effective... ({effectiveness}x)"
        elif effectiveness == 0:
            log_msg += " It had no effect!"
        self.battle_log.append(log_msg)
        self.battle_log.append(f"It dealt {damage} damage, leaving {defender.name} with {defender.current_hp}/{defender.max_hp} HP.")
        if defender.current_hp <= 0:
            self.battle_log.append(f"{defender.name} has fainted!")

    def _apply_end_of_turn_status_effects(self):
        for pokemon in [self.p1, self.p2]:
            if pokemon.current_hp > 0 and pokemon.status in ['Poisoned', 'Burned']:
                damage = max(1, pokemon.max_hp // 8)
                pokemon.current_hp = max(0, pokemon.current_hp - damage)
                self.battle_log.append(f"{pokemon.name} is hurt by its {pokemon.status.lower()}! It lost {damage} HP.")
                if pokemon.current_hp <= 0:
                    self.battle_log.append(f"{pokemon.name} has fainted!")

    def simulate_battle(self) -> dict:
        self.battle_log.append(f"Battle Start: {self.p1.name} vs. {self.p2.name}!")
        self.battle_log.append("-" * 25)
        
        self.battle_log.append(f"{self.p1.name}'s selected moveset:")
        for move in self.p1.moves:
            self.battle_log.append(f"  - {move.name.title()} (Power: {move.power}, Type: {move.move_type.capitalize()})")
        
        self.battle_log.append(f"{self.p2.name}'s selected moveset:")
        for move in self.p2.moves:
            self.battle_log.append(f"  - {move.name.title()} (Power: {move.power}, Type: {move.move_type.capitalize()})")
        self.battle_log.append("-" * 25)

        if random.random() < 0.5:
            target = random.choice([self.p1, self.p2])
            target.status = random.choice(['Poisoned', 'Paralyzed', 'Burned'])
            self.battle_log.append(f"{target.name} starts the battle with a {target.status} status!")
            
        attacker, defender = (self.p1, self.p2) if self.p1.speed >= self.p2.speed else (self.p2, self.p1)
        while self.p1.current_hp > 0 and self.p2.current_hp > 0:
            self.turn_count += 1
            self.battle_log.append(f"--- Turn {self.turn_count} ---")
            self._apply_turn(attacker, defender)
            if defender.current_hp <= 0: break
            self._apply_turn(defender, attacker)
            if attacker.current_hp <= 0: break
            self._apply_end_of_turn_status_effects()
        winner = self.p1.name if self.p1.current_hp > 0 else self.p2.name
        self.battle_log.append(f"The battle is over! The winner is {winner}!")
        return {"winner": winner, "battle_log": self.battle_log}