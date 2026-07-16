import pandas as pd
import sqlite3
import streamlit as st

st.set_page_config(
    page_title="Prestige HVAC Quote Helper - Trane Edition", 
    page_icon="https://prestigehvac.com/wp-content/uploads/2026/06/prestige-logo-circle-1.jpg",
    layout="wide"
)

# --- FORCE THE PALETTE FROM CONFIG.TOML ---
st.markdown(
    """
    <style>
    /* Main App Background (backgroundColor) */
    .stApp {
        background-color: #1c0b7c !important;
    }
    
    /* Main Page Texts (textColor) */
    .stApp, .stApp p, .stApp h1, .stApp h2, .stApp h3, .stApp span, .stApp label {
        color: #fbfbfc !important;
    }
    
    /* Sidebar Background (secondaryBackgroundColor) */
    [data-testid="stSidebar"] {
        background-color: #1c65f8 !important;
    }
    
    /* Sidebar Texts (textColor) */
    [data-testid="stSidebar"] * {
        color: #fbfbfc !important;
    }
    
    /* Selectboxes and input dropdowns inside sidebar & page (Light background for high legibility) */
    [data-testid="stSidebar"] div[data-baseweb="input"] input, 
    [data-testid="stSidebar"] div[role="combobox"],
    div[data-baseweb="select"] > div {
        background-color: #fbfbfc !important;
        color: #1c0b7c !important;
    }
    
    /* Primary Accent Color (primaryColor) - Slider Track & Handle */
    div.stSlider > div[data-baseweb="slider"] > div > div {
        background: #f70015 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
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
    df_raw = pd.read_excel("Trane Matchup 2026.xlsx", sheet_name="Sheet1", header=None)
    return df_raw

df_raw = load_excel_data()

if df_raw is not None:
    # Handle the merged cells in row 3 (Category Row)
    header_row_category = df_raw.iloc[3].ffill()
    header_row_metric = df_raw.iloc[4]

    parsed_columns = []

    for col_idx in range(len(df_raw.columns)):
        cat_val = header_row_category.iloc[col_idx]
        metric_val = header_row_metric.iloc[col_idx]

        clean_category = str(cat_val).strip() if pd.notnull(cat_val) else ""
        clean_metric = str(metric_val).strip() if pd.notnull(metric_val) else ""

        if clean_metric:
            display_name = f"{clean_category} | {clean_metric}" if clean_category else clean_metric
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

    # Find columns
    ton_col = None
    condenser_col = None
    total_col = None

    for col in df_clean.columns:
        col_lower = col.lower()
        if "| ton" in col_lower:
            ton_col = col
        elif "| outdoor" in col_lower:
            condenser_col = col
        elif "| total" in col_lower:
            total_col = col

    # Parse Tonnage values
    all_tons = []
    raw_vals = df_clean[ton_col].dropna().unique()
    for r in raw_vals:
        parsed = safe_parse_ton_display(r)
        if parsed and parsed not in all_tons:
            all_tons.append(parsed)

    # Sidebar Pricing
    st.sidebar.header("Pricing Calculator")
    markup_multiplier = st.sidebar.slider("Markup Multiplier", 1.0, 3.0, 1.8, step=0.05)
    flat_labor = st.sidebar.number_input("Labor & Material Cost ($)", value=1700)

    if all_tons:
        tonnages = [t for t in sorted(all_tons) if t is not None]
        selected_ton = st.selectbox("Select Tonnage", tonnages)

        # Filter systems based on selected tonnage
        df_filtered_ton = df_clean.copy()
        df_filtered_ton['temp_ton_clean'] = df_filtered_ton[ton_col].apply(safe_parse_ton_display)
        df_filtered_ton = df_filtered_ton[df_filtered_ton['temp_ton_clean'] == selected_ton]

        if not df_filtered_ton.empty:
            condensers_list = df_filtered_ton[condenser_col].dropna().unique()
            
            # Format dropdown display
            display_options = []
            for cond in condensers_list:
                row_match = df_filtered_ton[df_filtered_ton[condenser_col] == cond]
                if not row_match.empty:
                    tot_p = row_match[total_col].iloc[0]
                    display_options.append(f"{cond} — {tot_p}")

            selected_display = st.selectbox("Select Condenser Model", display_options)
            selected_condenser = selected_display.split(" — ")[0]

            # Match system configurations for selected Condenser
            display_df = df_filtered_ton[df_filtered_ton[condenser_col] == selected_condenser].copy()
            display_df = display_df.drop(columns=['temp_ton_clean'], errors='ignore')

            # Clean prices and calculate markup and totals
            raw_totals = display_df[total_col].astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False).astype(float)
            display_df["Retail Equipment Price"] = raw_totals * markup_multiplier
            display_df["Total Customer Investment"] = display_df["Retail Equipment Price"] + flat_labor

            # Format outputs as currency
            display_df["Retail Equipment Price"] = display_df["Retail Equipment Price"].map('${:,.2f}'.format)
            display_df["Total Customer Investment"] = display_df["Total Customer Investment"].map('${:,.2f}'.format)

            # Clean up headers for the table display
            final_columns = {}
            for col in display_df.columns:
                parts = col.split("|")
                final_columns[col] = parts[-1].strip() if len(parts) > 1 else col
                
            display_df = display_df.rename(columns=final_columns)

            st.subheader("Available Matchups & Customer Pricing")
            st.dataframe(display_df, use_container_width=True)
        else:
            st.warning("⚠️ No system configurations found matching criteria.")
    else:
        st.warning("⚠️ No tonnage information found in the document.")