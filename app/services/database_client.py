# In app/services/database_client.py

import json
from typing import List, Optional
from sqlalchemy.orm import selectinload
from sqlmodel import Field, Relationship, Session, SQLModel, create_engine, select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine

# --- Database Models ---

class PokemonTypeLink(SQLModel, table=True):
    pokemon_id: Optional[int] = Field(default=None, foreign_key="pokemon.id", primary_key=True)
    type_id: Optional[int] = Field(default=None, foreign_key="type.id", primary_key=True)

class PokemonAbilityLink(SQLModel, table=True):
    pokemon_id: Optional[int] = Field(default=None, foreign_key="pokemon.id", primary_key=True)
    ability_id: Optional[int] = Field(default=None, foreign_key="ability.id", primary_key=True)

class PokemonMoveLink(SQLModel, table=True):
    pokemon_id: Optional[int] = Field(default=None, foreign_key="pokemon.id", primary_key=True)
    move_id: Optional[int] = Field(default=None, foreign_key="move.id", primary_key=True)

class Type(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    pokemons: List["Pokemon"] = Relationship(back_populates="types", link_model=PokemonTypeLink)

class Ability(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    pokemons: List["Pokemon"] = Relationship(back_populates="abilities", link_model=PokemonAbilityLink)

class Move(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    json_data: str
    pokemons: List["Pokemon"] = Relationship(back_populates="moves", link_model=PokemonMoveLink)

class Stat(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    base_stat: int
    pokemon_id: Optional[int] = Field(default=None, foreign_key="pokemon.id")
    pokemon: "Pokemon" = Relationship(back_populates="base_stats")

class Pokemon(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    pokedex_id: int = Field(unique=True, index=True)
    name: str = Field(unique=True, index=True)
    # UPDATED: Allow sprite_url to be optional (nullable) in the database
    sprite_url: Optional[str] = None
    evolution_chain: str

    base_stats: List[Stat] = Relationship(back_populates="pokemon", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    types: List[Type] = Relationship(back_populates="pokemons", link_model=PokemonTypeLink)
    abilities: List[Ability] = Relationship(back_populates="pokemons", link_model=PokemonAbilityLink)
    moves: List[Move] = Relationship(back_populates="pokemons", link_model=PokemonMoveLink)


# --- Database Engine and Setup ---
DATABASE_URL = "sqlite+aiosqlite:///pokemon.db"
engine = create_async_engine(DATABASE_URL, echo=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

# --- Database Interaction Functions ---
async def get_pokemon_from_db(name: str, session: AsyncSession) -> Optional[Pokemon]:
    statement = (
        select(Pokemon)
        .where(Pokemon.name == name)
        .options(
            selectinload(Pokemon.types),
            selectinload(Pokemon.abilities),
            selectinload(Pokemon.moves),
            selectinload(Pokemon.base_stats)
        )
    )
    result = await session.exec(statement)
    return result.first()

async def add_pokemon_to_db(pokemon_data: dict, session: AsyncSession):
    types = []
    for type_name in pokemon_data['types']:
        result = await session.exec(select(Type).where(Type.name == type_name))
        type_obj = result.first() or Type(name=type_name)
        types.append(type_obj)
    
    abilities = []
    for ability_info in pokemon_data['abilities']:
        ability_name = ability_info['name']
        result = await session.exec(select(Ability).where(Ability.name == ability_name))
        ability_obj = result.first() or Ability(name=ability_name)
        abilities.append(ability_obj)
    
    moves = []
    for move_info in pokemon_data['moves']:
        move_name = move_info['name']
        result = await session.exec(select(Move).where(Move.name == move_name))
        move_obj = result.first()
        if not move_obj:
            move_obj = Move(name=move_name, json_data=json.dumps(move_info))
        moves.append(move_obj)
    
    db_pokemon = Pokemon(
        pokedex_id=pokemon_data['id'],
        name=pokemon_data['name'],
        evolution_chain=json.dumps(pokemon_data['evolution']['chain']),
        types=types,
        abilities=abilities,
        moves=moves
    )
    
    db_stats = [Stat(name=s['name'], base_stat=s['base_stat'], pokemon=db_pokemon) for s in pokemon_data['base_stats']]
    
    session.add(db_pokemon)
    session.add_all(db_stats)
    await session.commit()