import pandas as pd
import sqlite3
import streamlit as st

st.set_page_config(
    page_title="Prestige HVAC Quote Helper - Trane Edition", 
    page_icon="https://prestigehvac.com/wp-content/uploads/2026/06/prestige-logo-circle-1.jpg",
    layout="wide"
)

# --- TECHNICIAN INTERFACE HEADER ---
col1, col2, col3 = st.columns([4.25, 1.5, 4.25])

with col2:
    # Centered company logo using the exact URL and structure from Amana
    st.image(
        "https://prestigehvac.com/wp-content/uploads/2026/06/prestige-logo-circle-1.jpg",
        use_container_width=True
    )

st.title("Prestige Quick Quote Tool - Trane Edition")

# --- DATA STORAGE & DB CONNECTIONS ---
@st.cache_data
def load_excel_data():
    # Load the Trane Matchup Excel Sheets
    df_gas = pd.read_excel("Trane Matchup 2026.xlsx", sheet_name="Gas Furnace Systems")
    df_ah = pd.read_excel("Trane Matchup 2026.xlsx", sheet_name="Air Handler Systems")
    return df_gas, df_ah

def get_database_connection():
    df_gas, df_ah = load_excel_data()
    
    # Establish a fresh, live in-memory database
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    
    # Dump the Trane dataframes into the live connection
    df_gas.to_sql("gas_furnaces", conn, if_exists="replace", index=False)
    df_ah.to_sql("air_handlers", conn, if_exists="replace", index=False)
    return conn

conn = get_database_connection()

# Flexible verification check
inspector = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)
existing_tables = inspector['name'].tolist()

if not existing_tables:
    st.warning("⚠️ No catalog data found in the system database yet.")
else:
    system_type = st.selectbox("Select System Type", ["Air Handler Systems", "Gas Furnace Systems"])
    target_table = "air_handlers" if system_type == "Air Handler Systems" else "gas_furnaces"
    condenser_col = "Condenser/HP Model" if system_type == "Air Handler Systems" else "Condenser Model"

    tonnages = pd.read_sql(f"SELECT DISTINCT Tonnage FROM {target_table}", conn)["Tonnage"].tolist()
    selected_ton = st.selectbox("Select Tonnage", tonnages)
    
    price_col = "Base Unit Price" if system_type == "Air Handler Systems" else "Condenser Price"
        
    condensers = pd.read_sql(f"SELECT DISTINCT [{condenser_col}], [{price_col}] FROM {target_table} WHERE Tonnage='{selected_ton}'", conn)
        
    if not condensers.empty:
        condensers['display_name'] = condensers[condenser_col].astype(str) + " — " + condensers[price_col].astype(str)
        selected_display = st.selectbox("Select Condenser Model", condensers['display_name'])
        selected_condenser = selected_display.split(" — ")[0]
    else:
        selected_condenser = None
    
    if system_type == "Air Handler Systems":
        query = f"SELECT [Air Handler Model], [Air Handler HxWxD], [Air Handler Price], [Heat Kit], [Heat Kit Price], [SEER(2)], [Total] FROM air_handlers WHERE [Condenser/HP Model]='{selected_condenser}'"
    else:
        query = f"SELECT [Furnace Model], [Furnace Dimensions], [Furnace Price], [Evap Coil], [Evap Coil Price], [SEER(2)], [Total] FROM gas_furnaces WHERE [Condenser Model]='{selected_condenser}'"
        
    results = pd.read_sql(query, conn)
    
    # Matching Amana layout exactly for sidebar and pricing calculations
    st.sidebar.header("Pricing Calculator")
    markup_multiplier = st.sidebar.slider("Markup Multiplier", 1.0, 3.0, 1.8, step=0.05)
    flat_labor = st.sidebar.number_input("Labor & Material Cost ($)", value=1700)

    if not results.empty:
        raw_totals = results["Total"].astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False).astype(float)
        results["Retail Equipment Price"] = raw_totals * markup_multiplier
        results["Total Customer Investment"] = results["Retail Equipment Price"] + flat_labor
        
        results["Retail Equipment Price"] = results["Retail Equipment Price"].map('${:,.2f}'.format)
        results["Total Customer Investment"] = results["Total Customer Investment"].map('${:,.2f}'.format)

    st.subheader("Available Matchups & Customer Pricing")
    st.dataframe(results, use_container_width=True)

conn.close()