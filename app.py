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
                            # Clean up quotes and whitespace from the color hex
                            return v.strip().strip('"').strip("'")
        except Exception:
            pass
    return default

# Dynamically fetch colors from your config.toml
primary_color = get_theme_color("primaryColor", "#FF4B4B")
text_color = get_theme_color("textColor", "#FFFFFF")
background_color = get_theme_color("backgroundColor", "#1E1E2F")

# Custom style blocks that adapt dynamically to your config.toml palette
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

# Logo
st.image("https://prestigeheatingandair.com/wp-content/uploads/2021/08/logo.png", width=150)
st.title("Prestige Quick Quote Tool - Trane Edition")

# File path
file_path = "Trane Matchup 2026.xlsx"

if not os.path.exists(file_path):
    st.error(f"Error: '{file_path}' not found. Please ensure the file is in the repository.")
else:
    # Load Excel File
    xls = pd.ExcelFile(file_path)
    sheet_names = xls.sheet_names

    # Select Sheet
    selected_sheet = st.selectbox("Select Equipment Type", sheet_names)

    if selected_sheet:
        # Read starting from row 5 (0-indexed 4) to skip title blocks
        df = pd.read_excel(xls, sheet_name=selected_sheet, header=4)
        
        # Clean column names
        df.columns = df.columns.str.strip()
        df_clean = df.dropna(how='all')

        # Find columns by suffix to handle merged/complex headers
        def find_col(suffix):
            for col in df_clean.columns:
                if col.endswith(suffix) or col == suffix:
                    return col
            return None

        ton_col = find_col("Ton")
        seer_col = find_col("SEER2")
        outdoor_col = find_col("Outdoor")
        indoor_col = find_col("Indoor")
        coil_col = find_col("Coil w/ orifice") or find_col("Coil w/ TXV") or find_col("Coil")
        total_col = find_col("Total")

        # Fallbacks
        if not ton_col:
            ton_col = [c for c in df_clean.columns if "ton" in c.lower()][0] if [c for c in df_clean.columns if "ton" in c.lower()] else None
        if not total_col:
            total_col = [c for c in df_clean.columns if "total" in c.lower()][-1] if [c for c in df_clean.columns if "total" in c.lower()] else None

        if ton_col and total_col:
            # Extract unique tonnage options
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
                                st.write(f"**Coil:** {coil}")
                            with col2:
                                st.write(f"**SEER2:** {seer}")
                                if isinstance(total_price, (int, float)):
                                    st.subheader(f"Total: ${total_price:,.2f}")
                                else:
                                    st.subheader(f"Total: {total_price}")
                            st.markdown("---")
                else:
                    st.warning("No matched options found for this tonnage.")
        else:
            st.error("Could not map the Excel columns. Please check your sheet headers.")