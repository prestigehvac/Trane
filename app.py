import streamlit as st
import pandas as pd

st.set_page_config(page_title="Prestige Quick Quote Tool - Trane Edition", layout="centered")

# Perfect centering for the logo and shrinking it to 120px
st.markdown(
    """
    <div style="display: flex; justify-content: center;">
        <img src="https://prestigehvac.com/wp-content/uploads/2026/06/prestige-logo-circle-1.jpg" width="120">
    </div>
    """,
    unsafe_allow_html=True
)

# Centering the title text cleanly
st.markdown("<h1 style='text-align: center;'>Prestige Quick Quote Tool - Trane Edition</h1>", unsafe_allow_html=True)

# --- NEW: Sidebar Admin & Pricing Parameters ---
st.sidebar.header("⚙️ Admin Controls")
# Placeholder file uploader for future spreadsheet switching
uploaded_file = st.sidebar.file_uploader("Upload New Distributor Pricing Spreadsheet", type=["xlsx"])

st.sidebar.header("Pricing Calculator")
markup_multiplier = st.sidebar.slider("Markup Multiplier", min_value=1.00, max_value=3.00, value=1.80, step=0.05)
labor_material_cost = st.sidebar.number_input("Labor & Material Cost ($)", min_value=0.0, value=1700.0, step=100.0)

# 1. Load and parse the Excel file
@st.cache_data
def load_and_parse_data(file_path):
    # Use uploaded file if available, otherwise fallback to default sheet
    target_file = uploaded_file if uploaded_file is not None else file_path
    
    # Read the raw sheet without headers first to locate the tables
    df_raw = pd.read_excel(target_file, header=None)
    systems = {}
    current_system_name = None
    table_start_idx = None
    
    # Iterate through rows to find system headers and partition the tables
    for idx, row in df_raw.iterrows():
        val = str(row[0]).strip()
        if "Air Conditioner with 80% AFUE" in val or "Air Conditioner with Air Handler" in val or "Heat Pump with Air Handler" in val:
            if current_system_name and table_start_idx is not None:
                systems[current_system_name] = (table_start_idx, idx)
            current_system_name = val
            table_start_idx = idx + 1
            
    if current_system_name and table_start_idx is not None:
        systems[current_system_name] = (table_start_idx, len(df_raw))
        
    parsed_systems = {}
    for system_name, (start, end) in systems.items():
        sub_df = df_raw.iloc[start:end].copy()
        sub_df.columns = sub_df.iloc[0]
        sub_df = sub_df[1:]
        sub_df.columns = [str(col).strip() for col in sub_df.columns]
        sub_df = sub_df.dropna(subset=['Ton'])
        sub_df['Ton'] = pd.to_numeric(sub_df['Ton'], errors='coerce')
        sub_df = sub_df.dropna(subset=['Ton'])
        parsed_systems[system_name] = sub_df
    return parsed_systems

excel_file = "Trane Matchup 2026.xlsx"
try:
    system_tables = load_and_parse_data(excel_file)
    
    # 2. Dropdown Selection
    st.subheader("Select System Configuration")
    system_options = list(system_tables.keys())
    selected_system = st.selectbox("Select System Type", system_options)
    
    df_selected = system_tables[selected_system]
    ton_options = sorted(df_selected['Ton'].unique())
    selected_ton = st.selectbox("Select Tonnage (Ton)", ton_options, format_func=lambda x: f"{x:.1f} Ton")
    
    # 3. Retrieve and Display Matchup details
    matched_row = df_selected[df_selected['Ton'] == selected_ton].iloc[0]
    st.markdown("---")
    st.subheader(f"System Details: {selected_ton:.1f} Ton")
    
    # --- Updated Pricing Calculations ---
    base_total_val = matched_row.get('Total', 0)
    try:
        base_equipment_cost = float(base_total_val)
    except (ValueError, TypeError):
        base_equipment_cost = 0.0

    # Calculate marked up equipment cost and combined total investment
    marked_up_equipment = base_equipment_cost * markup_multiplier
    total_customer_investment = marked_up_equipment + labor_material_cost

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**SEER2:** {matched_row.get('SEER2', 'N/A')}")
        st.markdown(f"**Max Amp:** {matched_row.get('Max Amp', 'N/A')}")
        st.markdown(f"**Line Size:** {matched_row.get('Line Size', 'N/A')}")
        
    with col2:
        st.metric(label="Total System Cost (Marked Up Equipment)", value=f"${marked_up_equipment:,.2f}")
    
    # New final total display block
    st.markdown("---")
    st.subheader("💳 Final Pricing")
    inv_col1, inv_col2 = st.columns(2)
    with inv_col1:
        st.write(f"Marked Up Equipment: `${marked_up_equipment:,.2f}`")
        st.write(f"Labor & Materials: `${labor_material_cost:,.2f}`")
    with inv_col2:
        st.metric(label="Total Customer Investment", value=f"${total_customer_investment:,.2f}")

    st.markdown("---")
    st.markdown("### Component Breakdown")
    # ... keep the rest of your original component breakdown table code here ...