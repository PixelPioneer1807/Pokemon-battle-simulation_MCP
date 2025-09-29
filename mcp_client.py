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
        self.request_id += 1
        request = { "jsonrpc": "2.0", "method": method, "params": params, "id": self.request_id }
        request_str = json.dumps(request) + "\n"
        self.process.stdin.write(request_str.encode("utf-8"))
        await self.process.stdin.drain()
        response_str = await self.process.stdout.readline()
        if not response_str: raise Exception("No response from server")
        return json.loads(response_str)

    async def initialize(self):
        init_request = { "jsonrpc": "2.0", "method": "initialize", "params": { "protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "pokemon-client", "version": "1.0.0"} }, "id": 1 }
        init_str = json.dumps(init_request) + "\n"
        self.process.stdin.write(init_str.encode("utf-8"))
        await self.process.stdin.drain()
        await self.process.stdout.readline() # Read and discard the response
        initialized_notif = { "jsonrpc": "2.0", "method": "notifications/initialized", "params": {} }
        init_str = json.dumps(initialized_notif) + "\n"
        self.process.stdin.write(init_str.encode("utf-8"))
        await self.process.stdin.drain()

    async def llm_battle_simulator(self, pokemon1_name: str, pokemon2_name: str):
        return await self._send_request("tools/call", {
            "name": "llm_battle_simulator",
            "arguments": { "req": { "pokemon1_name": pokemon1_name, "pokemon2_name": pokemon2_name } }
        })

def print_narrative(text, delay=0.02, slow_after_colon=False):
    for i, char in enumerate(text):
        print(char, end='', flush=True)
        time.sleep(delay)
        if slow_after_colon and char == ':':
            time.sleep(0.3)
    print()

async def main():
    print("Starting MCP server...")
    process = await create_subprocess_exec(
        sys.executable, "server.py", stdin=PIPE, stdout=PIPE, stderr=PIPE
    )
    client = MCPClient(process)
    
    try:
        await asyncio.sleep(3)
        if process.returncode is not None:
            print("FATAL: Server failed to start!")
            stderr = await process.stderr.read()
            print(f"--- SERVER ERROR ---\n{stderr.decode()}")
            return
            
        await client.initialize()
        print_narrative("\n=== Pokémon LLM Battle Agent Client ===")
        print("Commands: 'battle <pokemon1> vs <pokemon2>' or 'exit'")
        print("-" * 40)

        while True:
            command = input("> ").lower().strip()
            if command == "exit": break

            parts = command.split()
            if parts[0] == "battle" and "vs" in parts and len(parts) == 4:
                p1_name, p2_name = parts[1], parts[3]
                try:
                    print_narrative(f"\nRequesting an LLM-simulated battle for {p1_name.capitalize()} vs {p2_name.capitalize()}...")
                    battle_response = await client.llm_battle_simulator(p1_name, p2_name)
                    
                    if "result" in battle_response:
                        battle_data = battle_response['result']['structuredContent']
                        winner = battle_data.get('winner', 'Unknown')
                        battle_log = battle_data.get('battle_log', [])
                        commentary_log = battle_data.get('commentary_log', [])
                        
                        commentary_iter = iter(commentary_log)

                        print_narrative("\n--- BATTLE START ---", delay=0.05)
                        for line in battle_log:
                            if "### --- Turn" in line:
                                time.sleep(1)
                                print_narrative(f"\n{line}", delay=0.05)
                                try:
                                    # Print commentary for the turn
                                    next(commentary_iter) # Skip the '---' separator
                                    print_narrative(f"🎤: \"{next(commentary_iter)}\"", delay=0.04, slow_after_colon=True)
                                except StopIteration:
                                    pass
                            elif "**LLM Strategy**" in line:
                                print_narrative(f"🧠 {line}", delay=0.01)
                            elif line.strip() != "---":
                                print(line)

                        print_narrative(f"\n🏆 BATTLE RESULT: {winner.capitalize()} wins! 🏆", delay=0.05)

                    elif "error" in battle_response:
                        print(f"\n--- SERVER ERROR ---\n{json.dumps(battle_response['error'], indent=2)}")

                except Exception as e:
                    print(f"An error occurred in the client: {e}")
            else:
                print("Invalid command. Use format: battle <pokemon1> vs <pokemon2>")
    
    finally:
        print_narrative("Shutting down server...")
        process.terminate()
        await process.wait()

if __name__ == "__main__":
    asyncio.run(main())