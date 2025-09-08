import asyncio
import logging
import sys
from fastmcp import FastMCP
from sqlmodel.ext.asyncio.session import AsyncSession

# Import our services and the custom exception
from app.services import poke_api_client, battle_engine, database_client
from app.services.poke_api_client import PokemonNotFoundError
from app.models.pydantic_models import PokemonData, BattleRequest, BattleResponse

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create MCP server - this MUST be at module level for fastmcp CLI to find it
mcp = FastMCP("Pokémon MCP Server")

@mcp.resource("pokemon://{name}")
async def get_pokemon(name: str) -> dict:
    """Get pokemon data"""
    try:
        await database_client.init_db()
        async with AsyncSession(database_client.engine) as session:
            result = await poke_api_client.get_pokemon_details(name, session)
            
            # Return data in the format your client expects
            base_stats = []
            if hasattr(result, 'stats') and result.stats:
                if isinstance(result.stats, dict):
                    base_stats = [
                        {"name": stat_name.replace('_', '-'), "base_stat": stat_value} 
                        for stat_name, stat_value in result.stats.items()
                    ]
                elif isinstance(result.stats, list):
                    base_stats = result.stats
            
            # Check for base_stats attribute as well
            if not base_stats and hasattr(result, 'base_stats'):
                base_stats = result.base_stats
            
            abilities = []
            if hasattr(result, 'abilities') and result.abilities:
                for ability in result.abilities:
                    if isinstance(ability, dict):
                        abilities.append({
                            "name": ability.get('name', str(ability)),
                            "is_hidden": ability.get('is_hidden', False)
                        })
                    elif hasattr(ability, 'name'):
                        # Handle Pydantic model or object with name attribute
                        abilities.append({
                            "name": getattr(ability, 'name', str(ability)),
                            "is_hidden": getattr(ability, 'is_hidden', False)
                        })
                    else:
                        # Handle string representation - extract the name
                        ability_str = str(ability)
                        if "name='" in ability_str:
                            name_start = ability_str.find("name='") + 6
                            name_end = ability_str.find("'", name_start)
                            ability_name = ability_str[name_start:name_end] if name_end > name_start else str(ability)
                            is_hidden = "is_hidden=True" in ability_str
                        else:
                            ability_name = ability_str
                            is_hidden = False
                        abilities.append({
                            "name": ability_name,
                            "is_hidden": is_hidden
                        })
            
            return {
                "name": result.name,
                "id": result.id,
                "sprite_url": getattr(result, 'sprite_url', None),
                "base_stats": base_stats,
                "abilities": abilities,
                "types": result.types if hasattr(result, 'types') else [],
                "moves": result.moves if hasattr(result, 'moves') else [],
                "evolution": getattr(result, 'evolution', {})
            }
    except PokemonNotFoundError as e:
        logger.error(f"Pokemon not found: {e}")
        raise Exception(f"Pokemon '{name}' not found")
    except Exception as e:
        logger.error(f"Error getting pokemon: {e}")
        raise Exception(f"Failed to get pokemon: {str(e)}")

@mcp.tool()
async def battle_simulator(req: dict) -> dict:
    """Battle two pokemon - expects req with pokemon1_name and pokemon2_name"""
    try:
        pokemon1_name = req.get("pokemon1_name")
        pokemon2_name = req.get("pokemon2_name")
        
        if not pokemon1_name or not pokemon2_name:
            raise Exception("Both pokemon1_name and pokemon2_name are required")
            
        await database_client.init_db()
        async with AsyncSession(database_client.engine) as session:
            pokemon1_data = await poke_api_client.get_pokemon_details(pokemon1_name, session)
            pokemon2_data = await poke_api_client.get_pokemon_details(pokemon2_name, session)
            
            engine = battle_engine.BattleEngine(pokemon1_data, pokemon2_data)
            result = engine.simulate_battle()
            
            return {
                "winner": result["winner"],
                "battle_log": result["battle_log"]
            }
    except PokemonNotFoundError as e:
        logger.error(f"Pokemon not found during battle: {e}")
        raise Exception(f"Pokemon not found: {str(e)}")
    except Exception as e:
        logger.error(f"Battle error: {e}")
        raise Exception(f"Battle failed: {str(e)}")

if __name__ == "__main__":
    try:
        logger.info("Starting Pokemon MCP Server...")
        # Use stdio transport for MCP client communication
        mcp.run(transport="stdio")
    except Exception as e:
        logger.error(f"Server failed: {e}", exc_info=True)
        sys.exit(1)