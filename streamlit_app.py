import streamlit as st
import asyncio
from sqlmodel.ext.asyncio.session import AsyncSession
from dotenv import load_dotenv
import os

from app.services import poke_api_client, battle_engine, database_client
from app.services.poke_api_client import PokemonNotFoundError

# Load environment variables from your .env file
load_dotenv()

# --- Async Helper Functions ---
def run_async(coro):
    """Helper to run async code in Streamlit's sync environment."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

async def get_pokemon_data(pokemon_name):
    """Fetches comprehensive data for a single Pokémon."""
    async with AsyncSession(database_client.engine) as session:
        return await poke_api_client.get_pokemon_details(pokemon_name, session)

async def run_battle(p1_name, p2_name):
    """Initializes and runs the entire battle simulation."""
    await database_client.init_db()
    p1_data = await get_pokemon_data(p1_name)
    p2_data = await get_pokemon_data(p2_name)

    if p1_data and p2_data:
        engine = battle_engine.BattleEngine(p1_data, p2_data)
        return await engine.simulate_battle(), p1_data, p2_data
    return None, None, None

# --- Streamlit Page Configuration ---
st.set_page_config(page_title="Pokémon LLM Battle Simulator", page_icon="⚔️", layout="wide")

# --- Main App UI ---
st.title("🐉 LLM-Powered Pokémon Battle Simulator")
st.markdown("An AI agent that uses an LLM to strategize and commentate Pokémon battles.")

# --- Pokémon Selection ---
col1, col2 = st.columns(2)
with col1:
    pokemon1_name = st.text_input("Enter the first Pokémon's name:", "snorlax").lower()
with col2:
    pokemon2_name = st.text_input("Enter the second Pokémon's name:", "gengar").lower()

if 'battle_result' not in st.session_state:
    st.session_state.battle_result = None

# --- Battle Button ---
if st.button("Simulate Battle!", use_container_width=True, type="primary"):
    st.session_state.battle_result = None # Clear previous results
    if pokemon1_name and pokemon2_name:
        with st.spinner(f"The LLM is simulating a strategic battle... This may take a moment."):
            result, p1_data, p2_data = run_async(run_battle(pokemon1_name, pokemon2_name))
            if result:
                st.session_state.battle_result = result
                st.session_state.p1_data = p1_data
                st.session_state.p2_data = p2_data
            else:
                st.error("Could not fetch data for one or both Pokémon. Please check the names.")
    else:
        st.warning("Please enter the names of both Pokémon.")

st.divider()

# --- Results Display ---
if st.session_state.battle_result:
    result = st.session_state.battle_result
    p1_data = st.session_state.p1_data
    p2_data = st.session_state.p2_data
    winner = result.get('winner', 'Unknown')

    st.header(f"🏆 Battle Result: {winner.capitalize()} wins! 🏆")

    # Display Pokémon info with sprites
    info_col1, info_col2 = st.columns(2)
    with info_col1:
        st.subheader(p1_data.name.capitalize())
        if p1_data.sprite_url: st.image(p1_data.sprite_url, width=150)
    with info_col2:
        st.subheader(p2_data.name.capitalize())
        if p2_data.sprite_url: st.image(p2_data.sprite_url, width=150)

    # --- Tabs for Commentary and Detailed Log ---
    tab1, tab2 = st.tabs(["🎤 LLM Commentary", "📜 Detailed Battle & Strategy Log"])

    with tab1:
        st.header("🎤 LLM Commentary")
        commentary_log = result.get('commentary_log', [])
        for i, line in enumerate(commentary_log):
            if "---" in line: continue
            st.markdown(f"**Turn { (i // 2) + 1 }:** {line}")

    with tab2:
        st.header("📜 Detailed Battle & Strategy Log")
        for line in result.get('battle_log', []):
            st.markdown(line, unsafe_allow_html=True)