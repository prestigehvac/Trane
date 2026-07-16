import streamlit as st
import pandas as pd
import os

# Helper to read colors directly from the .streamlit/config.toml palette
def get_theme_color(key, default):
    config_path = os.path.join(".streamlit", "config.toml")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                for line in f:
                    if "=" in line:
                        k, v = line.split("=", 1)
                        if k.strip() == key:
                            return v.strip().strip('"').strip("'")
        except Exception:
            pass
    return default

# Dynamically fetch colors from your config.toml
primary_color = get_theme_color("primaryColor", "#FF4B4B")
text_color = get_theme_color("textColor", "#FFFFFF")
background_color = get_theme_color("backgroundColor", "#1E1E2F")

# Styling blocks mapped to config.toml
st.markdown(f"""
    <style>
    .stApp {{
        background-color: {background_color};
        color: {text_color};
    }}
    h1, h2, h3, .stMarkdown p strong {{
        color: {primary_color} !important;
    }}
    div[data-testid="stBlock"] {{
        border: 1px solid {primary_color}33;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
    }}
    </style>
""", unsafe_allow_html=True)

# Logo & Title
st.image("https://prestigeheatingandair.com/wp-content/uploads/2021/08/logo.png", width=150)
st.title("Prestige Quick Quote Tool - Trane Edition")

file_path = "Trane Matchup 2026.xlsx"

# Define row ranges for each specific system type in Sheet1
SYSTEM_MAPPING = {
    "Air Conditioner with 80% AFUE Gas Furnace and Cased Coil R-454b 14.3 SEER2 w/ fixed orifice": {
        "skiprows": 4, 
        "nrows": 8,
        "coil_header": "Coil w/ orifice"
    },
    "Air Conditioner with Air Handler and Heat Kit R-454b 14.3 SEER2": {
        "skiprows": 15, 
        "nrows": 8,
        "coil_header": "Coil w/ TXV"
    },
    "Heat Pump with Air Handler and Heat Kit R-454b 14.3 SEER2": {
        "skiprows": 25, 
        "nrows": 8,
        "coil_header": "Heat Kit"
    }
}

if not os.path.exists(file_path):
    st.error(f"Error: '{file_path}' not found. Please ensure the file is in the repository.")
else:
    # Dropdown to select the system type
    selected_system = st.selectbox("Select System Type", list(SYSTEM_MAPPING.keys()))

    if selected_system:
        cfg = SYSTEM_MAPPING[selected_system]
        
        # Load the targeted table block from Sheet1
        df = pd.read_excel(
            file_path, 
            sheet_name="Sheet1", 
            header=0, 
            skiprows=cfg["skiprows"], 
            nrows=cfg["nrows"]
        )
        
        # Clean up column names
        df.columns = df.columns.str.strip()
        df_clean = df.dropna(how='all')

        # Clean mapping function for specific header columns
        def find_col(suffix):
            for col in df_clean.columns:
                if col.endswith(suffix) or col == suffix:
                    return col
            return None

        ton_col = find_col("Ton")
        seer_col = find_col("SEER2")
        outdoor_col = find_col("Outdoor")
        indoor_col = find_col("Indoor")
        coil_col = find_col(cfg["coil_header"])
        total_col = find_col("Total")

        if ton_col and total_col:
            # Drop down for Ton options
            raw_vals = df_clean[ton_col].dropna().unique()
            ton_values = sorted([float(val) for val in raw_vals if isinstance(val, (int, float)) or str(val).replace('.', '', 1).isdigit()])

            selected_ton = st.selectbox("Select Tonnage", ton_values)

            if selected_ton:
                match_df = df_clean[df_clean[ton_col] == selected_ton]

                if not match_df.empty:
                    st.success(f"Matched Options for {selected_ton} Tons:")

                    for idx, row in match_df.iterrows():
                        with st.container():
                            st.markdown(f"### Option {idx + 1}")
                            
                            outdoor = row.get(outdoor_col, "N/A")
                            indoor = row.get(indoor_col, "N/A")
                            coil = row.get(coil_col, "N/A")
                            total_price = row.get(total_col, "N/A")
                            seer = row.get(seer_col, "N/A")

                            col1, col2 = st.columns(2)
                            with col1:
                                st.write(f"**Outdoor Unit:** {outdoor}")
                                st.write(f"**Indoor Unit:** {indoor}")
                                st.write(f"**{cfg['coil_header']}:** {coil}")
                            with col2:
                                st.write(f"**SEER2:** {seer}")
                                if isinstance(total_price, (int, float)):
                                    st.subheader(f"Total: ${total_price:,.2f}")
                                elif isinstance(total_price, str) and "$" in total_price:
                                    st.subheader(f"Total: {total_price.strip()}")
                                else:
                                    st.subheader(f"Total: ${total_price}")
                            st.markdown("---")
                else:
                    st.warning("No matched options found for this tonnage.")
        else:
            st.error("Could not map the Excel columns. Check the structure of the Sheet.")