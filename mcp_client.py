import asyncio
import json
import sys
import time
from asyncio.subprocess import PIPE, create_subprocess_exec

class MCPClient:
    def __init__(self, process):
        self.process = process
        self.request_id = 0

    async def _send_request(self, method: str, params: dict) -> dict:
        """Sends a JSON-RPC request to the server's stdin."""
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self.request_id,
        }
        
        request_str = json.dumps(request) + "\n"
        print(f"Sending: {request_str.strip()}")  # Debug output
        
        self.process.stdin.write(request_str.encode("utf-8"))
        await self.process.stdin.drain()

        # Read response
        response_str = await self.process.stdout.readline()
        print(f"Received: {response_str.decode().strip()}")  # Debug output
        
        if not response_str:
            raise Exception("No response from server")
            
        try:
            return json.loads(response_str)
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON response: {response_str}")
            raise e

    async def initialize(self):
        """Initialize the MCP connection"""
        try:
            # Send initialization request
            init_request = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "resources": {"subscribe": True},
                        "tools": {}
                    },
                    "clientInfo": {
                        "name": "pokemon-client",
                        "version": "1.0.0"
                    }
                },
                "id": 1
            }
            
            init_str = json.dumps(init_request) + "\n"
            self.process.stdin.write(init_str.encode("utf-8"))
            await self.process.stdin.drain()
            
            # Read initialization response
            response_str = await self.process.stdout.readline()
            print(f"Init response: {response_str.decode().strip()}")
            
            # Send initialized notification
            initialized_request = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {}
            }
            
            init_str = json.dumps(initialized_request) + "\n"
            self.process.stdin.write(init_str.encode("utf-8"))
            await self.process.stdin.drain()
            
        except Exception as e:
            print(f"Initialization failed: {e}")
            raise

    async def get_pokemon(self, name: str):
        """Calls the 'pokemon' resource on the MCP server."""
        return await self._send_request("resources/read", {
            "uri": f"pokemon://{name}"
        })

    async def battle_simulator(self, pokemon1_name: str, pokemon2_name: str):
        """Calls the 'battle_simulator' tool on the MCP server."""
        return await self._send_request("tools/call", {
            "name": "battle_simulator",
            "arguments": {
                "req": {
                    "pokemon1_name": pokemon1_name, 
                    "pokemon2_name": pokemon2_name
                }
            }
        })

def print_narrative(text, delay=0.03):
    """Prints text with a slight delay to simulate narration."""
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()

async def display_pokemon_info(data: dict):
    """Formats and prints the Pokémon data."""
    # Handle MCP response structure
    try:
        if "result" in data and "contents" in data["result"]:
            content = data["result"]["contents"][0] if data["result"]["contents"] else {}
            if "text" in content:
                # Parse the JSON string from the text field
                pokemon = json.loads(content["text"])
            else:
                pokemon = content
        elif "result" in data:
            pokemon = data["result"]
        else:
            print("Error: Could not parse Pokémon data from response.")
            print(f"Raw data: {data}")
            return
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"Error parsing Pokemon data: {e}")
        print(f"Raw data: {data}")
        return

    print("\n--- Pokédex Entry ---")
    print(f"Name: {pokemon.get('name', 'N/A').capitalize()} (ID: {pokemon.get('id', 'N/A')})")
    if pokemon.get('sprite_url'):
        print(f"Sprite: {pokemon.get('sprite_url')}")
    if pokemon.get('evolution', {}).get('chain'):
        print(f"Evolution Line: {' -> '.join(e.capitalize() for e in pokemon['evolution']['chain'])}")
    
    print("\nTypes:")
    for ptype in pokemon.get('types', []):
        print(f"  - {ptype.capitalize()}")
    
    print("\nBase Stats:")
    for stat in pokemon.get('base_stats', []):
        print(f"  - {stat.get('name', '').replace('-', ' ').title()}: {stat.get('base_stat')}")
    
    print("\nAbilities:")
    for ability in pokemon.get('abilities', []):
        # Handle nested ability structure
        ability_name = ability.get('name')
        if isinstance(ability_name, dict):
            ability_name = ability_name.get('name', 'Unknown')
        is_hidden = ability.get('is_hidden', False)
        print(f"  - {ability_name.replace('-', ' ').title()}{' (Hidden)' if is_hidden else ''}")
    
    print("\nMoves (sample):")
    for move in pokemon.get('moves', [])[:5]:  # Show first 5 moves
        power = move.get('power', 'N/A')
        move_type = move.get('move_type', 'unknown').capitalize()
        damage_class = move.get('damage_class', 'unknown').capitalize()
        print(f"  - {move.get('name', 'Unknown').replace('-', ' ').title()} (Power: {power}, Type: {move_type}, Class: {damage_class})")
    
    if len(pokemon.get('moves', [])) > 5:
        print(f"  ... and {len(pokemon['moves']) - 5} more moves")
    
    print("---------------------\n")

async def main():
    """Starts the server, connects the client, and runs the command loop."""
    print("Starting MCP server...")
    
    # Start the server process
    process = await create_subprocess_exec(
        sys.executable, "server.py", stdin=PIPE, stdout=PIPE, stderr=PIPE
    )
    
    client = MCPClient(process)
    
    try:
        # Wait for FastMCP server to fully start
        print("Waiting for server to initialize...")
        await asyncio.sleep(3)
        
        # Check if server is still running
        if process.returncode is not None:
            print("Server failed to start!")
            return
            
        print("Server started, initializing MCP connection...")
        
        # Initialize MCP connection
        await client.initialize()
        
        print_narrative("MCP Client Initialized. Connected to stdio server.")
        print("You can give commands like:")
        print("  - 'lookup pikachu'")
        print("  - 'battle charmander vs squirtle'")
        print("  - 'exit'")
        print("-" * 20)

        while True:
            command = input("> ").lower().strip()

            if command == "exit":
                print_narrative("Shutting down client and server.")
                break
            
            elif command == "list-resources":
                try:
                    response = await client.list_resources()
                    print(f"Available resources: {json.dumps(response, indent=2)}")
                except Exception as e:
                    print(f"Error listing resources: {e}")
                continue
                    
            elif command == "list-tools":
                try:
                    response = await client.list_tools()
                    print(f"Available tools: {json.dumps(response, indent=2)}")
                except Exception as e:
                    print(f"Error listing tools: {e}")
                continue
            
            parts = command.split()
            
            if parts[0] == "lookup" and len(parts) == 2:
                try:
                    response = await client.get_pokemon(parts[1])
                    await display_pokemon_info(response)
                except Exception as e:
                    print(f"Error: {e}")

            elif parts[0] == "battle" and "vs" in parts and len(parts) == 4:
                p1_name, p2_name = parts[1], parts[3]
                print("Fetching Pokémon data for context...")
                
                try:
                    p1_response = await client.get_pokemon(p1_name)
                    p2_response = await client.get_pokemon(p2_name)

                    await display_pokemon_info(p1_response)
                    await display_pokemon_info(p2_response)
                    input("Press Enter to start the battle...")
                    
                    battle_response = await client.battle_simulator(p1_name, p2_name)
                    
                    if "result" in battle_response:
                        result_data = battle_response['result']
                        
                        # Try to get battle data from structuredContent first
                        battle_data = None
                        if "structuredContent" in result_data:
                            battle_data = result_data["structuredContent"]
                        elif "content" in result_data and result_data["content"]:
                            # Parse from content array
                            content_item = result_data["content"][0]
                            if content_item.get("type") == "text":
                                try:
                                    battle_data = json.loads(content_item["text"])
                                except json.JSONDecodeError:
                                    print("Failed to parse battle data from content")
                        
                        if battle_data and "battle_log" in battle_data:
                            winner = battle_data.get('winner', 'Unknown')
                            battle_log = battle_data.get('battle_log', [])
                            
                            print_narrative(f"\n🏆 BATTLE RESULT: {winner} wins! 🏆\n")
                            print_narrative("=== BATTLE LOG ===\n")
                            
                            for line in battle_log:
                                print_narrative(line, delay=0.02)
                                # Add small pause for readability on important lines
                                if any(keyword in line.lower() for keyword in ["turn", "winner", "fainted", "battle start"]):
                                    time.sleep(0.3)
                                else:
                                    time.sleep(0.1)
                            
                            print_narrative(f"\n🎉 {winner} is victorious! 🎉")
                        else:
                            print(f"Could not parse battle results. Raw response: {battle_response}")
                    else:
                        print(f"Error from server: {battle_response}")
                        
                except Exception as e:
                    print(f"Error during battle: {e}")
            else:
                print("Invalid command. Please use the format 'lookup <pokemon>' or 'battle <pokemon1> vs <pokemon2>'.")
    
    except Exception as e:
        print(f"Client error: {e}")
    finally:
        # Clean up
        process.terminate()
        await process.wait()

if __name__ == "__main__":
    asyncio.run(main())