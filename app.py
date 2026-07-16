import streamlit as st
import pandas as pd

# ==========================================
# 1. PAGE SETUP (Relying on config.toml for Theme)
# ==========================================
st.set_page_config(
    page_title="Prestige HVAC Quote Helper - Trane Edition",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. ROBUST COLUMN MATCHING
# ==========================================
def find_column(df, target_name):
    """
    Finds a column name in df matching target_name, 
    ignoring case and whitespace.
    """
    target_clean = str(target_name).strip().lower()
    for col in df.columns:
        if str(col).strip().lower() == target_clean:
            return col
    # Fallback substring match
    for col in df.columns:
        if target_clean in str(col).strip().lower():
            return col
    return None

def clean_and_format_price(val):
    """Cleans numeric formats or currency strings safely."""
    if pd.isna(val):
        return 0.0
    val_str = str(val).replace('$', '').replace(',', '').strip()
    try:
        return float(val_str)
    except ValueError:
        return 0.0

# ==========================================
# 3. DATA LOADING & MULTI-TABLE SPLITTING
# ==========================================
SHEET_ID = "1aRef-chlSkfAL6IUc7-sNcX3c7JmIgon"
GID = "2046850502"
csv_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(ttl=600)
def load_and_split_data(url):
    df_raw = pd.read_csv(url, header=None)
    
    sections = {}
    current_section_name = None
    section_rows = []
    
    for idx, row in df_raw.iterrows():
        row_values = [str(x).strip() for x in row.values if pd.notna(x)]
        
        # Identify section headers
        if len(row_values) == 1 and "seer2" in row_values[0].lower():
            if current_section_name and section_rows:
                sections[current_section_name] = pd.DataFrame(section_rows)
            current_section_name = row_values[0]
            section_rows = []
        elif current_section_name is not None:
            section_rows.append(row.values)
            
    # Save final section
    if current_section_name and section_rows:
        sections[current_section_name] = pd.DataFrame(section_rows)
        
    # Format tables properly
    final_sections = {}
    for name, df_sec in sections.items():
        if not df_sec.empty:
            df_sec.columns = df_sec.iloc[0]
            df_sec = df_sec[1:].reset_index(drop=True)
            df_sec = df_sec.dropna(how='all')
            final_sections[name] = df_sec
            
    return final_sections

try:
    all_tables = load_and_split_data(csv_url)
except Exception as e:
    st.error(f"Failed to load Google Sheet data: {e}")
    st.stop()

# ==========================================
# 4. SIDEBAR NAVIGATION
# ==========================================
# Image Logo header exactly matching Amana style
st.sidebar.image("https://prestigetranequoter.streamlit.app/~/+/media/79b47e8ef6e61e06fa4df9fe6a0b943715dfc640e0231cf4c478e9b6.png", use_container_width=True)
st.sidebar.markdown("## Prestige Quote Helper")

if not all_tables:
    st.warning("No matchup tables found in the Google Sheet.")
    st.stop()

# Dropdowns
system_types = list(all_tables.keys())
selected_system = st.sidebar.selectbox("Select System Type", system_types)

df_clean = all_tables[selected_system]

# Safely extract dynamic columns using the helper
ton_col = find_column(df_clean, "Ton")
outdoor_col = find_column(df_clean, "Outdoor")
indoor_col = find_column(df_clean, "Indoor")
total_col = find_column(df_clean, "Total")

if not ton_col:
    st.error("Could not locate the 'Ton' column in the layout.")
    st.stop()

# Clean and filter the available ton options
raw_tons = df_clean[ton_col].dropna().astype(str).str.strip()
raw_tons = raw_tons[raw_tons.str.match(r'^\d+(\.\d+)?$')].unique()
raw_tons = sorted(raw_tons, key=float)

selected_ton = st.sidebar.selectbox("Select System Tonnage", raw_tons)

# Retrieve matching row
df_filtered = df_clean[df_clean[ton_col].astype(str).str.strip() == str(selected_ton)]

if df_filtered.empty:
    st.warning("No matches found for the selected tonnage.")
    st.stop()

row_match = df_filtered.iloc[0]

# Quote Settings
markup = st.sidebar.slider("Quote Markup Percentage (%)", min_value=0, max_value=100, value=35, step=5)

# ==========================================
# 5. MAIN DISPLAY LAYOUT
# ==========================================
st.title("Prestige Quick Quote Tool - Trane Edition")
st.write("---")

st.markdown(f"### Configured System: **{selected_system}**")

# Calculate price securely
total_raw_price = 0.0
if total_col:
    total_raw_price = clean_and_format_price(row_match[total_col])
else:
    # Fallback to summing any columns containing 'price' in the title
    for idx, col in enumerate(df_clean.columns):
        if "price" in str(col).lower():
            total_raw_price += clean_and_format_price(row_match.iloc[idx])

marked_up_total = total_raw_price * (1 + (markup / 100))

# Display Cards Side-by-Side
col1, col2 = st.columns(2)

with col1:
    st.subheader("Equipment Specifications")
    
    if outdoor_col:
        st.info(f"**Outdoor Unit (Condenser):** {row_match[outdoor_col]}")
    if indoor_col:
        st.info(f"**Indoor Unit (Air Handler / Furnace):** {row_match[indoor_col]}")
        
    # Print remaining matched sheet metadata fields
    for col in df_clean.columns:
        if col not in [ton_col, outdoor_col, indoor_col, total_col] and "price" not in str(col).lower():
            if pd.notna(row_match[col]) and str(row_match[col]).strip() != "":
                st.write(f"**{col}:** {row_match[col]}")

with col2:
    st.subheader("Pricing Breakdown")
    st.metric(label="Base Wholesale Price", value=f"${total_raw_price:,.2f}")
    st.metric(label="Markup Applied", value=f"{markup}%")
    st.write("---")
    st.metric(label="Customer Quote Price", value=f"${marked_up_total:,.2f}")