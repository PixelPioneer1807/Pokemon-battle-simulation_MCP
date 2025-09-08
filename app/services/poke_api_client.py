import httpx
import asyncio
import json
# REMOVED: from fastapi import HTTPException
from typing import List
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from ..models.pydantic_models import PokemonData, Stat, AbilityInfo, MoveInfo, EvolutionInfo
from . import database_client

POKEAPI_BASE_URL = "https://pokeapi.co/api/v2"

# NEW: A custom exception for our service layer.
class PokemonNotFoundError(Exception):
    """Raised when a Pokémon is not found in the PokéAPI."""
    pass

def _convert_db_pokemon_to_pydantic(db_pokemon: database_client.Pokemon) -> PokemonData:
    """Converts a database Pokemon object into a Pydantic PokemonData object."""
    return PokemonData(
        id=db_pokemon.pokedex_id,
        name=db_pokemon.name,
        sprite_url=db_pokemon.sprite_url,
        types=[t.name for t in db_pokemon.types],
        base_stats=[Stat(name=s.name, base_stat=s.base_stat) for s in db_pokemon.base_stats],
        abilities=[AbilityInfo(name=a.name, is_hidden=False) for a in db_pokemon.abilities],
        moves=[MoveInfo.parse_obj(json.loads(m.json_data)) for m in db_pokemon.moves],
        evolution=EvolutionInfo(chain=json.loads(db_pokemon.evolution_chain))
    )

async def get_pokemon_details(pokemon_name: str, session: AsyncSession) -> PokemonData:
    """Fetches comprehensive data for a Pokémon, utilizing the SQLite database."""
    normalized_name = pokemon_name.lower()
    
    db_pokemon = await database_client.get_pokemon_from_db(normalized_name, session)
    if db_pokemon:
        print(f"DB HIT: Found '{normalized_name}' in the database.")
        return _convert_db_pokemon_to_pydantic(db_pokemon)

    print(f"DB MISS: '{normalized_name}' not in database. Fetching from PokéAPI...")
    async with httpx.AsyncClient() as client:
        try:
            pokemon_response = await client.get(f"{POKEAPI_BASE_URL}/pokemon/{normalized_name}")
            pokemon_response.raise_for_status()
            pokemon_data = pokemon_response.json()

            species_url = pokemon_data['species']['url']
            species_response = await client.get(species_url)
            species_response.raise_for_status()
            species_data = species_response.json()

            evolution_chain_url = species_data['evolution_chain']['url']
            evolution_response = await client.get(evolution_chain_url)
            evolution_response.raise_for_status()
            evolution_data = evolution_response.json()

            pydantic_pokemon = await _parse_pydantic_pokemon(pokemon_data, evolution_data, client)
            
            print(f"Adding '{normalized_name}' to the database for future requests.")
            await database_client.add_pokemon_to_db(pydantic_pokemon.dict(), session)
            
            return pydantic_pokemon

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # UPDATED: Raise our new custom exception instead of HTTPException
                raise PokemonNotFoundError(f"Pokémon '{pokemon_name}' not found.")
            else:
                # For other errors, we can raise a generic exception
                raise Exception(f"Error fetching data from PokéAPI: {e.response.text}")

async def _parse_pydantic_pokemon(pokemon_data: dict, evolution_data: dict, client: httpx.AsyncClient) -> PokemonData:
    """Parses raw API data into our Pydantic PokemonData model."""
    stats = [Stat(name=s['stat']['name'], base_stat=s['base_stat']) for s in pokemon_data['stats']]
    abilities = [AbilityInfo(name=a['ability']['name'], is_hidden=a['is_hidden']) for a in pokemon_data['abilities']]
    types = [t['type']['name'] for t in pokemon_data['types']]
    
    sprite_url = pokemon_data.get('sprites', {}).get('front_default')

    moves = await _select_competitive_moveset(pokemon_data['moves'], types, client)

    chain = []
    current = evolution_data['chain']
    while current:
        chain.append(current['species']['name'])
        if current['evolves_to']: current = current['evolves_to'][0]
        else: current = None
    evolution_info = EvolutionInfo(chain=chain)
    
    return PokemonData(
        id=pokemon_data['id'],
        name=pokemon_data['name'],
        sprite_url=sprite_url,
        types=types,
        base_stats=stats,
        abilities=abilities,
        moves=moves,
        evolution=evolution_info
    )

async def _select_competitive_moveset(all_moves_data: List[dict], pokemon_types: List[str], client: httpx.AsyncClient) -> List[MoveInfo]:
    """Analyzes a move pool and selects a competitive set of four moves."""
    move_urls = [move_info['move']['url'] for move_info in all_moves_data]
    move_tasks = [client.get(url) for url in move_urls]
    move_responses = await asyncio.gather(*move_tasks, return_exceptions=True)

    processed_moves = []
    for res in move_responses:
        if isinstance(res, httpx.Response) and res.status_code == 200:
            move_data = res.json()
            if move_data.get('power') is not None and move_data['power'] > 0:
                processed_moves.append(MoveInfo(name=move_data['name'], power=move_data.get('power'), move_type=move_data['type']['name'], damage_class=move_data['damage_class']['name']))

    if not processed_moves: return []

    stab_moves = [m for m in processed_moves if m.move_type in pokemon_types]
    other_moves = [m for m in processed_moves if m.move_type not in pokemon_types]
    stab_moves.sort(key=lambda x: x.power, reverse=True)
    other_moves.sort(key=lambda x: x.power, reverse=True)

    final_moveset = []
    final_moveset.extend(stab_moves[:2])
    remaining_slots = 4 - len(final_moveset)
    final_moveset.extend(other_moves[:remaining_slots])
    
    if len(final_moveset) < 4:
        final_moveset.extend(stab_moves[2:2 + (4 - len(final_moveset))])

    return final_moveset[:4]