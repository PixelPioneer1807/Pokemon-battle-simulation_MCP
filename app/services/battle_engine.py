import random
from typing import List, Optional, Tuple
from ..models.pydantic_models import PokemonData, MoveInfo
from . import llm_client

# (TYPE_EFFECTIVENESS dictionary remains the same)
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
        self.attack_points = 200

class BattleEngine:
    def __init__(self, pokemon1_data: PokemonData, pokemon2_data: PokemonData):
        self.p1 = BattlePokemon(pokemon1_data)
        self.p2 = BattlePokemon(pokemon2_data)
        self.battle_log: List[str] = []
        self.commentary_log: List[str] = []
        self.turn_count = 0

    def _get_move_by_name(self, pokemon: BattlePokemon, move_name: str) -> Optional[MoveInfo]:
        for move in pokemon.moves:
            if move.name == move_name:
                return move
        return None

    def _calculate_damage(self, move: MoveInfo, attacker: BattlePokemon, defender: BattlePokemon) -> Tuple[int, float]:
        if move.damage_class == 'physical':
            attack_stat = attacker.attack
            defense_stat = defender.defense
        elif move.damage_class == 'special':
            attack_stat = attacker.special_attack
            defense_stat = defender.special_defense
        else:
            return 0, 1.0
        damage = (((2 / 5 + 2) * move.power * attack_stat / defense_stat) / 50) + 2
        effectiveness = 1.0
        if move.move_type in TYPE_EFFECTIVENESS:
            for def_type in defender.types:
                effectiveness *= TYPE_EFFECTIVENESS[move.move_type].get(def_type, 1)
        return int(damage * effectiveness), effectiveness

    async def _apply_turn(self, attacker: BattlePokemon, defender: BattlePokemon):
        if attacker.current_hp <= 0: return

        if attacker.status == 'Paralyzed' and random.random() < 0.25:
            self.battle_log.append(f"**{attacker.name} is paralyzed! It can't move!**")
            self.commentary_log.append(f"{attacker.name} is fully paralyzed and can't make a move!")
            return

        llm_response = await llm_client.get_strategic_move_and_commentary(attacker, defender, self.turn_count)
        move_name = llm_response.get("chosen_move")
        self.battle_log.append(f"**LLM Strategy:** {llm_response.get('strategy', 'N/A')}")
        self.commentary_log.append(llm_response.get('commentary', '...'))

        if not move_name: return
        move = self._get_move_by_name(attacker, move_name)
        if not move: return

        move_cost = move.power or 0
        attacker.attack_points -= move_cost
        damage, effectiveness = self._calculate_damage(move, attacker, defender)
        defender.current_hp = max(0, defender.current_hp - damage)

        log_msg = f"{attacker.name} used **{move.name.replace('-', ' ').title()}** and dealt **{damage} damage**."
        if effectiveness > 1: log_msg += " (Super effective!)"
        elif effectiveness < 1 and effectiveness > 0: log_msg += " (Not very effective...)"

        self.battle_log.append(log_msg)
        self.battle_log.append(
            f"_{defender.name}: {defender.current_hp}/{defender.max_hp} HP | {attacker.name}: {attacker.attack_points} AP_"
        )

        if defender.current_hp <= 0:
            self.battle_log.append(f"**{defender.name} has fainted!**")
            self.commentary_log.append(f"And that's it! {defender.name} is down for the count!")

    def _apply_end_of_turn_status_effects(self):
        for pokemon in [self.p1, self.p2]:
            if pokemon.current_hp > 0 and pokemon.status in ['Poisoned', 'Burned']:
                damage = max(1, pokemon.max_hp // 8)
                pokemon.current_hp = max(0, pokemon.current_hp - damage)
                log_msg = f"_{pokemon.name} is hurt by its {pokemon.status.lower()}! It lost {damage} HP._"
                self.battle_log.append(log_msg)
                if pokemon.current_hp <= 0:
                    self.battle_log.append(f"**{pokemon.name} has fainted from the status effect!**")

    async def simulate_battle(self) -> dict:
        self.battle_log.append(f"**Battle Start: {self.p1.name} vs. {self.p2.name}!**")
        self.battle_log.append("-------------------------")

        # FEATURE RESTORED: Display movesets at the start
        self.battle_log.append(f"{self.p1.name}'s moveset:")
        for move in self.p1.moves:
            self.battle_log.append(f"  - {move.name.title()} (Power: {move.power}, Type: {move.move_type.capitalize()})")
        
        self.battle_log.append(f"{self.p2.name}'s moveset:")
        for move in self.p2.moves:
            self.battle_log.append(f"  - {move.name.title()} (Power: {move.power}, Type: {move.move_type.capitalize()})")
        self.battle_log.append("-------------------------")

        # FEATURE RESTORED: Random starting status
        if random.random() < 0.3: # 30% chance for a status effect
            target = random.choice([self.p1, self.p2])
            target.status = random.choice(['Poisoned', 'Paralyzed', 'Burned'])
            self.battle_log.append(f"_{target.name} starts the battle with a {target.status} status!_")

        attacker, defender = (self.p1, self.p2) if self.p1.speed >= self.p2.speed else (self.p2, self.p1)

        while self.p1.current_hp > 0 and self.p2.current_hp > 0 and self.turn_count < 50:
            self.turn_count += 1
            self.battle_log.append(f"### --- Turn {self.turn_count} ---")
            
            attacker.attack_points = min(200, attacker.attack_points + 40)
            defender.attack_points = min(200, defender.attack_points + 40)
            
            await self._apply_turn(attacker, defender)
            if defender.current_hp <= 0: break

            await self._apply_turn(defender, attacker)
            if attacker.current_hp <= 0: break

            self._apply_end_of_turn_status_effects()
            self.battle_log.append("---")

        winner = self.p1.name if self.p1.current_hp > 0 else self.p2.name
        self.battle_log.append(f"### The battle is over! The winner is {winner}!")
        return {"winner": winner, "battle_log": self.battle_log, "commentary_log": self.commentary_log}