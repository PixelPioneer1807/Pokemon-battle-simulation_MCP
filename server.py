# In server.py
import asyncio
import logging
import sys
from fastmcp import FastMCP
from sqlmodel.ext.asyncio.session import AsyncSession
from dotenv import load_dotenv

from app.services import poke_api_client, battle_engine, database_client
from app.services.poke_api_client import PokemonNotFoundError

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("Pokémon LLM Battle Agent Server")

@mcp.resource("pokemon://{name}")
async def get_pokemon(name: str) -> dict:
    # This function remains the same, it's a useful resource.
    try:
        await database_client.init_db()
        async with AsyncSession(database_client.engine) as session:
            result = await poke_api_client.get_pokemon_details(name, session)
            # The existing data formatting logic stays here...
            return {
                "name": result.name,
                "id": result.id,
                "sprite_url": getattr(result, 'sprite_url', None),
                "base_stats": result.base_stats,
                "abilities": result.abilities,
                "types": result.types,
                "moves": result.moves,
                "evolution": getattr(result, 'evolution', {})
            }
    except PokemonNotFoundError as e:
        logger.error(f"Pokemon not found: {e}")
        raise Exception(f"Pokemon '{name}' not found")
    except Exception as e:
        logger.error(f"Error getting pokemon: {e}")
        raise Exception(f"Failed to get pokemon: {str(e)}")


@mcp.tool()
async def llm_battle_simulator(req: dict) -> dict:
    """
    Simulates a Pokémon battle where an LLM acts as the strategist and commentator.
    Expects req with pokemon1_name and pokemon2_name.
    """
    try:
        pokemon1_name = req.get("pokemon1_name")
        pokemon2_name = req.get("pokemon2_name")

        if not pokemon1_name or not pokemon2_name:
            raise Exception("Both pokemon1_name and pokemon2_name are required")

        await database_client.init_db()
        async with AsyncSession(database_client.engine) as session:
            # Fetch data for both Pokémon
            pokemon1_data = await poke_api_client.get_pokemon_details(pokemon1_name, session)
            pokemon2_data = await poke_api_client.get_pokemon_details(pokemon2_name, session)

            # Initialize the battle engine with the data
            engine = battle_engine.BattleEngine(pokemon1_data, pokemon2_data)
            
            # Run the simulation, which is now an async process controlled by the LLM
            result = await engine.simulate_battle()

            # Return the full result dictionary
            return result

    except PokemonNotFoundError as e:
        logger.error(f"Pokemon not found during battle: {e}")
        raise Exception(f"Pokemon not found: {str(e)}")
    except Exception as e:
        logger.error(f"Battle error: {e}")
        raise Exception(f"Battle failed: {str(e)}")

if __name__ == "__main__":
    try:
        logger.info("Starting Pokémon LLM Agent MCP Server...")
        mcp.run(transport="stdio")
    except Exception as e:
        logger.error(f"Server failed: {e}", exc_info=True)
        sys.exit(1)