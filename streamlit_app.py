import streamlit as st
import asyncio
from sqlmodel.ext.asyncio.session import AsyncSession

from app.services import poke_api_client, battle_engine, database_client
from app.services.poke_api_client import PokemonNotFoundError

def run_async(coro):
    return asyncio.run(coro)

async def get_pokemon_data(pokemon_name):
    try:
        await database_client.init_db()
        async with AsyncSession(database_client.engine) as session:
            return await poke_api_client.get_pokemon_details(pokemon_name, session)
    except PokemonNotFoundError:
        return None
    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None

st.set_page_config(page_title="Pokémon Battle Simulator", page_icon="⚔️", layout="wide")

st.title("🐉 Pokémon Battle Simulator")
st.markdown("Choose two Pokémon and watch them battle!")

col1, col2 = st.columns(2)

with col1:
    pokemon1_name = st.text_input("Enter the first Pokémon's name:", "pikachu").lower()

with col2:
    pokemon2_name = st.text_input("Enter the second Pokémon's name:", "bulbasaur").lower()

if 'battle_result' not in st.session_state:
    st.session_state.battle_result = None

if st.button("Start Battle!", use_container_width=True):
    if pokemon1_name and pokemon2_name:
        with st.spinner(f"Simulating battle between {pokemon1_name.capitalize()} and {pokemon2_name.capitalize()}..."):
            p1_data = run_async(get_pokemon_data(pokemon1_name))
            p2_data = run_async(get_pokemon_data(pokemon2_name))

            if p1_data and p2_data:
                engine = battle_engine.BattleEngine(p1_data, p2_data)
                st.session_state.battle_result = engine.simulate_battle()
                st.session_state.p1_data = p1_data
                st.session_state.p2_data = p2_data
            else:
                st.error("Could not fetch data for one or both Pokémon. Please check the names and try again.")
    else:
        st.warning("Please enter the names of both Pokémon.")

st.divider()

# --- Display Results Section ---
if st.session_state.battle_result:
    result = st.session_state.battle_result
    p1_data = st.session_state.p1_data
    p2_data = st.session_state.p2_data

    winner = result.get('winner', 'Unknown')
    st.header(f"🏆 Battle Result: {winner.capitalize()} wins! 🏆")

    # Display Pokémon Info Side-by-Side
    info_col1, info_col2 = st.columns(2)
    with info_col1:
        st.subheader(p1_data.name.capitalize())
        if p1_data.sprite_url:
            st.image(p1_data.sprite_url, width=150)
        st.write(f"**Types:** {', '.join(t.capitalize() for t in p1_data.types)}")
        st.write("**Base Stats:**")
        for stat in p1_data.base_stats:
            st.write(f"  - {stat.name.replace('-', ' ').title()}: {stat.base_stat}")


    with info_col2:
        st.subheader(p2_data.name.capitalize())
        if p2_data.sprite_url:
            st.image(p2_data.sprite_url, width=150)
        st.write(f"**Types:** {', '.join(t.capitalize() for t in p2_data.types)}")
        st.write("**Base Stats:**")
        for stat in p2_data.base_stats:
            st.write(f"  - {stat.name.replace('-', ' ').title()}: {stat.base_stat}")

    # Display Battle Log
    st.subheader("📜 Battle Log")
    with st.expander("Click to see the full battle log"):
        for line in result.get('battle_log', []):
            if "Turn" in line:
                st.markdown(f"**{line}**")
            elif any(keyword in line for keyword in ["super effective", "not very effective", "fainted"]):
                st.info(line)
            elif "wins!" in line:
                st.success(line)
            else:
                st.text(line)