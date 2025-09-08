from pydantic import BaseModel, Field
from typing import List, Optional


class Stat(BaseModel):
    """Represents a single base statistic of a Pokémon."""
    name: str = Field(..., description="The name of the statistic (e.g., 'hp', 'attack').")
    base_stat: int = Field(..., description="The base value of the statistic.")

class AbilityInfo(BaseModel):
    """Represents a Pokémon's ability."""
    name: str = Field(..., description="The name of the ability.")
    is_hidden: bool = Field(..., description="Indicates if this is a hidden ability.")

class MoveInfo(BaseModel):
    """Represents a move a Pokémon can learn, with detailed info."""
    name: str = Field(..., description="The name of the move.")
    power: Optional[int] = Field(0, description="The power of the move. 0 for status moves.")
    move_type: str = Field(..., description="The type of the move (e.g., 'fire', 'water').")
    damage_class: str = Field(..., description="The damage class ('physical', 'special', or 'status').")

class EvolutionInfo(BaseModel):
    """Represents the evolution chain information."""
    chain: List[str] = Field(..., description="An ordered list of Pokémon names in the evolution chain.")

class PokemonData(BaseModel):
    """
    The comprehensive data model for a single Pokémon, designed to be exposed via the MCP resource.
    """
    id: int
    name: str
    sprite_url: Optional[str] = Field(None, description="The URL for the Pokémon's default front sprite image.")
    types: List[str]
    base_stats: List[Stat]
    abilities: List[AbilityInfo]
    moves: List[MoveInfo]
    evolution: EvolutionInfo


# --- Models for Battle Simulation Tool ---

class BattleRequest(BaseModel):
    """The request model for initiating a battle simulation."""
    pokemon1_name: str = Field(..., description="The name of the first Pokémon competitor.")
    pokemon2_name: str = Field(..., description="The name of the second Pokémon competitor.")

class BattleResponse(BaseModel):
    """The response model providing the results of the battle simulation."""
    winner: Optional[str] = Field(None, description="The name of the winning Pokémon. Can be null in a draw.")
    battle_log: List[str] = Field(..., description="A detailed, turn-by-turn log of the battle.")