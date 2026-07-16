import pandas as pd
import sqlite3
import streamlit as st

st.set_page_config(
    page_title="Prestige Quick Quote Tool - Trane Edition", 
    page_icon="https://prestigehvac.com/wp-content/uploads/2026/06/prestige-logo-circle-1.jpg",
    layout="wide"
)

# --- 1. LOGO CENTERING (SAME AS AMANA) ---
col1, col2, col3 = st.columns([4.25, 1.5, 4.25])

with col2:
    # Display and center the logo above the title
    st.image(
        "https://prestigehvac.com/wp-content/uploads/2026/06/prestige-logo-circle-1.jpg",
        use_container_width=True
    )

# Placing st.title AFTER the logo columns forces it to sit underneath the logo
st.title("Prestige Quick Quote Tool - Trane Edition")

# --- 2. CACHED DATA LOADING & CLEANING ---
@st.cache_data
def load_trane_excel_data():
    df = pd.read_excel("Trane Matchup 2026.xlsx", sheet_name="Sheet1", header=4)
    
    # Strip prefixes like "Air Conditioner with 80% AFUE Gas Furnace.../" from headers
    cleaned_cols = []
    for col in df.columns:
        if "/" in col:
            cleaned_cols.append(col.split("/")[-1].strip())
        else:
            cleaned_cols.append(col.strip())
    df.columns = cleaned_cols
    
    # Ensure there are no duplicate column names by renaming the multiple 'Price' fields
    price_counter = 0
    new_cols = []
    for col in df.columns:
        if col == "Price":
            if price_counter == 0:
                new_cols.append("Outdoor Price")
            elif price_counter == 1:
                new_cols.append("Indoor Price")
            else:
                new_cols.append("Coil Price")
            price_counter += 1
        else:
            new_cols.append(col)
    df.columns = new_cols
    
    # Clean up empty rows
    df = df.dropna(subset=["Ton"])
    return df

def get_database_connection():
    df = load_trane_excel_data()
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    df.to_sql("trane_systems", conn, if_exists="replace", index=False)
    return conn

# Establish database connection
try:
    conn = get_database_connection()
    
    # --- 3. TECHNICIAN DROP-DOWNS ---
    # Tonnage selection
    tonnages = pd.read_sql("SELECT DISTINCT [Ton] FROM trane_systems", conn)["Ton"].tolist()
    selected_ton = st.selectbox("Select Tonnage", sorted(tonnages))
    
    # Filter outdoor models based on Tonnage
    outdoors_df = pd.read_sql(
        f"SELECT DISTINCT [Outdoor], [Outdoor Price] FROM trane_systems WHERE [Ton] = {selected_ton}", 
        conn
    )
    
    if not outdoors_df.empty:
        outdoors_df['display_name'] = outdoors_df['Outdoor'] + " — " + outdoors_df['Outdoor Price'].astype(str)
        selected_display = st.selectbox("Select Outdoor Unit Model", outdoors_df['display_name'])
        selected_outdoor = selected_display.split(" — ")[0]
    else:
        selected_outdoor = None
        
    # --- 4. MARKUP CALCULATOR SIDEBAR ---
    st.sidebar.header("Pricing Calculator")
    markup_multiplier = st.sidebar.slider("Markup Multiplier", 1.0, 3.0, 1.8, step=0.05)
    flat_labor = st.sidebar.number_input("Labor & Material Cost ($)", value=1700)

    # --- 5. EXECUTE SEARCH & DISPLAY RESULTS ---
    if selected_outdoor:
        query = f"""
            SELECT 
                [SEER2], [Max Amp], [Line Size], 
                [Outdoor], [Outdoor Price], 
                [Indoor], [Indoor Price], 
                [Coil w/ orifice], [Coil Price], 
                [Total] 
            FROM trane_systems 
            WHERE [Ton] = {selected_ton} AND [Outdoor] = '{selected_outdoor}'
        """
        results = pd.read_sql(query, conn)
        
        if not results.empty:
            # Strip currency symbols to calculate
            raw_totals = results["Total"].astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False).astype(float)
            results["Retail Equipment Price"] = raw_totals * markup_multiplier
            results["Total Customer Investment"] = results["Retail Equipment Price"] + flat_labor
            
            # Format outputs elegantly
            results["Retail Equipment Price"] = results["Retail Equipment Price"].map('${:,.2f}'.format)
            results["Total Customer Investment"] = results["Total Customer Investment"].map('${:,.2f}'.format)
            
            st.subheader("Available Matchup & Customer Pricing")
            st.dataframe(results, use_container_width=True)
        else:
            st.info("No matching systems found for this combination.")
            
    conn.close()

except Exception as e:
    st.error(f"Error initializing database or processing file: {e}")