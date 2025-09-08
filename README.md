🐉 Pokémon FastMCP Server

This project is a FastMCP server that connects to the PokéAPI
 and provides two main features:

Resources – Enter a Pokémon’s name and instantly fetch its details (stats, abilities, etc.).

Tools – Run a simple battle simulation between Pokémon.

It is designed to be tested and explored using MCP Inspector.

🚀 Features

🔍 Fetch Pokémon Data: Get information like stats, abilities, and types directly from PokéAPI.

⚔️ Battle Simulation Tool: Try a quick Pokémon battle between two Pokémon and see who wins.

🖥️ User-Friendly Testing: Use MCP Inspector to explore resources and tools with no coding required.

📦 Requirements

Before you start, make sure you have:

Python 3.9+ installed

Node.js + npm installed (for MCP Inspector)

Internet connection (to fetch Pokémon data)


⚙️ Setup & Installation
1️⃣ Clone the project / Donwload & extract from zip file

git clone https://github.com/PixelPioneer1807/Pokemon-battle-simulation_MCP.git
cd your_extracted_folder

2️⃣ Create and activate virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate

3️⃣ Install dependencies
pip install -r requirements.txt

First run:

python test_server.py

See if the server is running, you'll see output like:

Testing server startup...
Current directory: C:\Users\HP\Documents\pokemon_fastmcp_server
Python executable: C:\Users\HP\Documents\pokemon_fastmcp_server\.venv\Scripts\python.exe
✅ server.py found
Starting server process...
✅ Server started successfully and is still running!

🎉 Server test passed!

if you get an error fix it then move forward

4️⃣ Install MCP Inspector (for testing)
npm install -g @modelcontextprotocol/inspector

▶️ Running the Server with Inspector

Once everything is installed, run:
mcp-inspector python server.py

This will:

Start your FastMCP server (server.py)

Open MCP Inspector in your browser at given link, you can either enter your session token or open inspector with token prefilled
if you are not going with the prefilled option, when open the link shown in terminal add your session token in cofiguration -> PROXY SESSION TOKEN to start your mcp server

🎮 How to Use

Open MCP Inspector in your browser.

In the top sidebar:

Resources templates → List Templates -> get_pokemon -> Enter a Pokémon name (e.g., pikachu) to fetch details from PokéAPI.

Tools → Use the Battle Simulation tool, choose two Pokémon, 

{
  "pokemon1_name": "pikachu",
  "pokemon2_name": "bulbasaur"
}
 
use the upper json format, see who wins replace with any pokemon names

No coding required — just type in Pokémon names and click run ✅

✅ So the flow is:

To get Pokémon data → use resource URIs like pokemon://pikachu.

To battle → send JSON with pokemon1_name and pokemon2_name.



🖥️ Testing with the Custom MCP Client

If you prefer testing in the terminal instead of MCP Inspector, you can use the included mcp_client.py script.

Run the client:

python mcp_client.py


You’ll see an interactive prompt where you can type commands like:

lookup pikachu
battle charmander vs squirtle
exit

Example 

> battle squirtle vs arceus

--- Pokédex Entry ---
Name: Squirtle (ID: 7)
Sprite: https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/7.png
Evolution Line: Squirtle -> Wartortle -> Blastoise
...

--- Pokédex Entry ---
Name: Arceus (ID: 493)
Evolution Line: Arceus
...

🏆 BATTLE RESULT: Arceus wins! 🏆
This way, you can test battles and Pokémon lookups without needing MCP Inspector.