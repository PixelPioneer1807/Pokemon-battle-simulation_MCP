import streamlit as st
import json
import subprocess
import time
import sys
import os
import requests
import threading
from queue import Queue, Empty

class SimpleMCPClient:
    """Simplified MCP client using subprocess and HTTP-like communication"""
    
    def __init__(self):
        self.process = None
        self.request_id = 0
    
    def start_server(self):
        """Start the MCP server process"""
        try:
            self.process = subprocess.Popen(
                [sys.executable, "-u", "server.py"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # Wait for server to start
            time.sleep(3)
            
            # Check if process is running
            if self.process.poll() is not None:
                stdout, stderr = self.process.communicate()
                raise Exception(f"Server failed to start. stderr: {stderr}, stdout: {stdout}")
            
            # Initialize MCP connection
            self._send_init_messages()
            
            return True
            
        except Exception as e:
            raise Exception(f"Failed to start server: {str(e)}")
    
    def _send_init_messages(self):
        """Send MCP initialization messages"""
        # Send initialize request
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
                    "name": "pokemon-streamlit-client",
                    "version": "1.0.0"
                }
            },
            "id": 1
        }
        
        self._write_request(init_request)
        response = self._read_response()
        
        # Send initialized notification
        initialized_request = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {}
        }
        self._write_request(initialized_request)
    
    def _write_request(self, request):
        """Write a request to the server"""
        request_str = json.dumps(request) + "\n"
        self.process.stdin.write(request_str)
        self.process.stdin.flush()
    
    def _read_response(self):
        """Read a response from the server"""
        try:
            response_line = self.process.stdout.readline()
            if not response_line:
                raise Exception("No response from server")
            return json.loads(response_line)
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON response: {response_line}")
    
    def get_pokemon(self, name):
        """Get Pokemon data"""
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "method": "resources/read",
            "params": {"uri": f"pokemon://{name}"},
            "id": self.request_id
        }
        
        self._write_request(request)
        return self._read_response()
    
    def battle_simulator(self, pokemon1_name, pokemon2_name):
        """Run battle simulation"""
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "battle_simulator",
                "arguments": {
                    "req": {
                        "pokemon1_name": pokemon1_name,
                        "pokemon2_name": pokemon2_name
                    }
                }
            },
            "id": self.request_id
        }
        
        self._write_request(request)
        return self._read_response()
    
    def close(self):
        """Close the server process"""
        if self.process:
            self.process.terminate()
            self.process.wait()

@st.cache_resource
def get_mcp_client():
    """Get or create MCP client"""
    client = SimpleMCPClient()
    try:
        client.start_server()
        return client
    except Exception as e:
        raise Exception(f"Failed to start MCP client: {str(e)}")

def parse_pokemon_data(response):
    """Parse Pokemon data from MCP response"""
    if "result" in response and "contents" in response["result"]:
        content = response["result"]["contents"][0] if response["result"]["contents"] else {}
        if "text" in content:
            return json.loads(content["text"])
    return None

def display_pokemon_card(pokemon_data, col):
    """Display Pokemon information in a card format"""
    with col:
        st.subheader(f"🔴 {pokemon_data['name'].title()}")
        
        # Sprite
        if pokemon_data.get('sprite_url'):
            st.image(pokemon_data['sprite_url'], width=150)
        
        # Basic Info
        st.write(f"**ID:** {pokemon_data.get('id', 'Unknown')}")
        st.write(f"**Types:** {', '.join(t.title() for t in pokemon_data.get('types', []))}")
        
        # Evolution
        if pokemon_data.get('evolution', {}).get('chain'):
            evolution_chain = " → ".join(p.title() for p in pokemon_data['evolution']['chain'])
            st.write(f"**Evolution:** {evolution_chain}")
        
        # Stats
        if pokemon_data.get('base_stats'):
            st.write("**Base Stats:**")
            for stat in pokemon_data['base_stats']:
                st.write(f"  • {stat['name'].replace('-', ' ').title()}: {stat['base_stat']}")
        
        # Abilities
        if pokemon_data.get('abilities'):
            st.write("**Abilities:**")
            for ability in pokemon_data['abilities']:
                hidden = " (Hidden)" if ability.get('is_hidden') else ""
                st.write(f"  • {ability['name'].title()}{hidden}")
        
        # Top Moves
        if pokemon_data.get('moves'):
            st.write("**Signature Moves:**")
            for move in pokemon_data['moves'][:3]:
                power = move.get('power', 'N/A')
                move_type = move.get('move_type', 'Unknown').title()
                st.write(f"  • {move['name'].replace('-', ' ').title()} (⚡{power}, {move_type})")

def main():
    st.set_page_config(
        page_title="Pokemon Battle Simulator", 
        page_icon="⚡",
        layout="wide"
    )
    
    st.title("⚡ Pokemon Battle Simulator MCP")
    st.markdown("*Powered by FastMCP & AI Battle Engine*")
    
    # Initialize MCP client
    try:
        with st.spinner("Starting MCP server..."):
            client = get_mcp_client()
        st.success("MCP server started successfully!")
    except Exception as e:
        st.error("Failed to start MCP server")
        st.error(f"Error: {str(e)}")
        st.write("Make sure server.py is working by running: `python server.py`")
        st.stop()
    
    # Sidebar for Pokemon lookup
    st.sidebar.header("🔍 Pokemon Lookup")
    lookup_name = st.sidebar.text_input("Enter Pokemon name:", placeholder="pikachu")
    
    if st.sidebar.button("Look Up Pokemon") and lookup_name:
        with st.spinner(f"Fetching {lookup_name.title()} data..."):
            try:
                response = client.get_pokemon(lookup_name.lower())
                pokemon_data = parse_pokemon_data(response)
                
                if pokemon_data:
                    st.sidebar.success(f"Found {pokemon_data['name'].title()}!")
                    
                    # Store in session state
                    if 'looked_up_pokemon' not in st.session_state:
                        st.session_state.looked_up_pokemon = []
                    
                    if pokemon_data not in st.session_state.looked_up_pokemon:
                        st.session_state.looked_up_pokemon.append(pokemon_data)
                        if len(st.session_state.looked_up_pokemon) > 10:
                            st.session_state.looked_up_pokemon.pop(0)
                    
                    # Display in main area
                    st.header(f"📋 {pokemon_data['name'].title()} Details")
                    display_pokemon_card(pokemon_data, st)
                    
                else:
                    st.sidebar.error("Pokemon not found!")
                    
            except Exception as e:
                st.sidebar.error(f"Error: {str(e)}")
    
    # Battle Section
    st.header("⚔️ Battle Simulator")
    
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col1:
        st.subheader("Fighter 1")
        pokemon1 = st.text_input("Pokemon 1:", placeholder="pikachu", key="p1")
    
    with col3:
        st.subheader("Fighter 2")
        pokemon2 = st.text_input("Pokemon 2:", placeholder="charmander", key="p2")
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        battle_button = st.button("🥊 BATTLE!", type="primary", use_container_width=True)
    
    if battle_button and pokemon1 and pokemon2:
        # Create progress tracking
        progress_container = st.empty()
        
        try:
            with progress_container.container():
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                status_text.text("Fetching Pokemon data...")
                progress_bar.progress(20)
                
                # Fetch Pokemon data
                response1 = client.get_pokemon(pokemon1.lower())
                progress_bar.progress(40)
                
                response2 = client.get_pokemon(pokemon2.lower())
                progress_bar.progress(60)
                
                pokemon1_data = parse_pokemon_data(response1)
                pokemon2_data = parse_pokemon_data(response2)
                
                if not pokemon1_data:
                    progress_container.empty()
                    st.error(f"Pokemon '{pokemon1}' not found!")
                    st.stop()
                    
                if not pokemon2_data:
                    progress_container.empty()
                    st.error(f"Pokemon '{pokemon2}' not found!")
                    st.stop()
                
                status_text.text("Preparing battle arena...")
                progress_bar.progress(70)
                
                # Clear progress and show Pokemon cards
                progress_container.empty()
                
                col1, col2 = st.columns(2)
                
                # Display Pokemon cards
                st.subheader("🥊 Battle Contestants")
                display_pokemon_card(pokemon1_data, col1)
                display_pokemon_card(pokemon2_data, col2)
                
                # Battle progress
                battle_progress = st.empty()
                
                with battle_progress.container():
                    battle_bar = st.progress(0)
                    battle_status = st.empty()
                    
                    battle_status.text("Initializing battle...")
                    battle_bar.progress(10)
                    
                    battle_status.text("AI analyzing movesets...")
                    battle_bar.progress(30)
                    
                    battle_status.text("Battle in progress...")
                    battle_bar.progress(60)
                    
                    # Run battle
                    battle_response = client.battle_simulator(pokemon1.lower(), pokemon2.lower())
                    battle_bar.progress(90)
                    
                    battle_status.text("Processing results...")
                    battle_bar.progress(100)
                    
                    # Clear battle progress
                    battle_progress.empty()
                
                # Battle Results Section
                st.subheader("⚔️ Battle Results")
                
                if "result" in battle_response:
                    result_data = battle_response['result']
                    
                    # Get battle data
                    battle_data = None
                    if "structuredContent" in result_data:
                        battle_data = result_data["structuredContent"]
                    elif "content" in result_data and result_data["content"]:
                        content_item = result_data["content"][0]
                        if content_item.get("type") == "text":
                            battle_data = json.loads(content_item["text"])
                    
                    if battle_data and "battle_log" in battle_data:
                        winner = battle_data.get('winner', 'Unknown')
                        battle_log = battle_data.get('battle_log', [])
                        
                        # Winner announcement with color
                        if winner.lower() == pokemon1.lower():
                            st.success(f"🏆 **{winner.title()} Wins!** 🏆")
                        else:
                            st.success(f"🏆 **{winner.title()} Wins!** 🏆")
                        
                        # Battle summary
                        st.info(f"Battle concluded after {len([line for line in battle_log if 'Turn' in line and '---' in line])} turns")
                        
                        # Battle log in expandable section
                        with st.expander("📜 View Complete Battle Log", expanded=False):
                            # Format battle log nicely
                            log_text = ""
                            for line in battle_log:
                                if "Turn" in line and "---" in line:
                                    log_text += f"\n**{line}**\n"
                                elif line.startswith("Battle Start:"):
                                    log_text += f"## {line}\n"
                                elif line.startswith("  - "):
                                    log_text += f"{line}\n"
                                elif "used" in line and ("dealt" in line or "effective" in line):
                                    log_text += f"*{line}*\n"
                                elif "fainted" in line or "winner" in line:
                                    log_text += f"**{line}**\n"
                                elif "burned" in line or "status" in line:
                                    log_text += f"*{line}*\n"
                                else:
                                    log_text += f"{line}\n"
                            
                            st.markdown(log_text)
                    else:
                        st.error("Could not parse battle results")
                        st.json(battle_response)  # Show raw response for debugging
                else:
                    st.error("Battle failed")
                    if "error" in battle_response:
                        st.error(f"Error: {battle_response['error']}")
                        
        except Exception as e:
            progress_container.empty()
            error_msg = str(e)
            if "timeout" in error_msg.lower():
                st.error("Battle timed out. The server may be overloaded.")
                st.info("Try again with simpler Pokemon or wait a moment.")
            elif "not found" in error_msg.lower():
                st.error("One or both Pokemon were not found in the database.")
            else:
                st.error(f"Battle error: {error_msg}")
            st.info("Check Pokemon names and try again.")
    
    # Recent lookups
    if 'looked_up_pokemon' in st.session_state and st.session_state.looked_up_pokemon:
        st.sidebar.header("📚 Recent Lookups")
        for pokemon in reversed(st.session_state.looked_up_pokemon[-5:]):
            if st.sidebar.button(f"{pokemon['name'].title()}", key=f"recent_{pokemon['id']}"):
                display_pokemon_card(pokemon, st)

if __name__ == "__main__":
    main()