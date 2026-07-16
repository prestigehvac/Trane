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
    st.image(
        "https://prestigehvac.com/wp-content/uploads/2026/06/prestige-logo-circle-1.jpg",
        use_container_width=True
    )

st.title("Prestige Quick Quote Tool - Trane Edition")

# --- DATA STORAGE & DB CONNECTIONS ---
@st.cache_data
def load_excel_data():
    # Corrected: Read from "Sheet1" where your Trane matchup data actually is
    df_raw = pd.read_excel("Trane Matchup 2026.xlsx", sheet_name="Sheet1", header=None)
    return df_raw

df_raw = load_excel_data()

if df_raw is not None:
    # Rebuild headers from Trane layout (rows 3 and 4)
    header_row_category = df_raw.iloc[3]
    header_row_metric = df_raw.iloc[4]

    current_category = None
    parsed_columns = []

    for col_idx in range(len(df_raw.columns)):
        cat_val = header_row_category.iloc[col_idx]
        metric_val = header_row_metric.iloc[col_idx]

        if pd.notnull(cat_val) and str(cat_val).strip() != "":
            current_category = str(cat_val).strip()

        if pd.notnull(metric_val) and str(metric_val).strip() != "":
            clean_metric = str(metric_val).strip()
            display_name = f"{current_category} | {clean_metric}" if current_category else clean_metric
            parsed_columns.append((col_idx, display_name))

    col_indices = [p[0] for p in parsed_columns]
    col_names = [p[1] for p in parsed_columns]

    df_clean = df_raw.iloc[5:].copy()
    df_clean = df_clean.iloc[:, col_indices]
    df_clean.columns = col_names
    df_clean = df_clean.dropna(how='all')

    # Helper function for system tonnage options
    def safe_parse_ton_display(val):
        if pd.isnull(val):
            return None
        s = str(val).strip()
        if not s:
            return None
        if "Ton" in s:
            return s
        try:
            f_val = float(s)
            if f_val.is_integer():
                return f"{int(f_val)} Ton"
            else:
                return f"{f_val} Ton"
        except ValueError:
            return s

    # Price cleaning helper
    def clean_price(val):
        if pd.isnull(val):
            return 0.0
        s = str(val).replace('$', '').replace(',', '').strip()
        try:
            return float(s)
        except ValueError:
            return 0.0

    # Drop blank rows missing crucial system items
    system_cols = [c for c in df_clean.columns if "System" in c or "Condenser" in c or "Furnace" in c or "Coil" in c or "Air Handler" in c]
    if len(system_cols) > 0:
        first_sys_col = system_cols[0]
        df_clean = df_clean.dropna(subset=[first_sys_col])

    # Dynamic Tonnage Filter
    all_tons = []
    ton_col = None
    for c in df_clean.columns:
        if "Ton" in c:
            ton_col = c
            raw_vals = df_clean[c].dropna().unique()
            for r in raw_vals:
                parsed = safe_parse_ton_display(r)
                if parsed and parsed not in all_tons:
                    all_tons.append(parsed)
            break

    # Build the DB for SQL querying matching Amana UI flow
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    df_clean.to_sql("trane_systems", conn, if_exists="replace", index=False)

    tonnages = [t for t in sorted(all_tons) if t is not None]
    selected_ton = st.selectbox("Select Tonnage", tonnages)

    # Sidebar Pricing matching Amana app variables and sidebar look
    st.sidebar.header("Pricing Calculator")
    markup_multiplier = st.sidebar.slider("Markup Multiplier", 1.0, 3.0, 1.8, step=0.05)
    flat_labor = st.sidebar.number_input("Labor & Material Cost ($)", value=1700)

    # Dynamically select condenser based on tonnage selection
    condenser_col = [c for c in df_clean.columns if "Condenser" in c][0]
    price_col = [c for c in df_clean.columns if "Price" in c][0]  # Grab primary condenser price column

    # Get active models to show in dropdown
    df_filtered_ton = df_clean.copy()
    df_filtered_ton['temp_ton_clean'] = df_filtered_ton[ton_col].apply(safe_parse_ton_display)
    df_filtered_ton = df_filtered_ton[df_filtered_ton['temp_ton_clean'] == selected_ton]

    if not df_filtered_ton.empty:
        condensers_list = df_filtered_ton[condenser_col].dropna().unique()
        selected_condenser = st.selectbox("Select Condenser Model", condensers_list)

        # Retrieve matched system combinations for selected Condenser
        display_df = df_filtered_ton[df_filtered_ton[condenser_col] == selected_condenser].copy()
        display_df = display_df.drop(columns=['temp_ton_clean'], errors='ignore')

        # Find total column
        total_col = [c for c in display_df.columns if "Total" in c or "Price" in c][-1] # Get matchup total price column

        # Calculate Retail and Total Customer Investment matching Amana's database columns addition
        raw_totals = display_df[total_col].astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False).astype(float)
        display_df["Retail Equipment Price"] = raw_totals * markup_multiplier
        display_df["Total Customer Investment"] = display_df["Retail Equipment Price"] + flat_labor

        # Format Currency
        display_df["Retail Equipment Price"] = display_df["Retail Equipment Price"].map('${:,.2f}'.format)
        display_df["Total Customer Investment"] = display_df["Total Customer Investment"].map('${:,.2f}'.format)

        st.subheader("Available Matchups & Customer Pricing")
        st.dataframe(display_df, use_container_width=True)
    else:
        st.warning("⚠️ No system configurations found matching criteria.")

    conn.close()