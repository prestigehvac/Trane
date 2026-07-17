import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Prestige Quick Quote Tool - Trane Edition", 
    layout="centered",
    page_icon="https://prestigehvac.com/wp-content/uploads/2026/06/prestige-logo-circle-1.jpg"
)

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

# --- Sidebar Admin & Pricing Parameters ---
st.sidebar.header("⚙️ Admin Controls")

# Simple password protection
admin_password = st.sidebar.text_input("Enter Admin Password", type="password")

# Only show the file uploader if the password is correct
if admin_password == "Pr3st1g375098":
    uploaded_file = st.sidebar.file_uploader("Upload New Distributor Pricing Spreadsheet", type=["xlsx"])
    st.sidebar.success("Access Granted!")
else:
    uploaded_file = None
    if admin_password: # Only show error if they actually typed something wrong
        st.sidebar.error("Incorrect Password")

# 1. Load and parse the Excel file
@st.cache_data
def load_and_parse_data(file_path):
    target_file = uploaded_file if uploaded_file is not None else file_path
    df_raw = pd.read_excel(target_file, header=None)
    systems = {}
    current_system_name = None
    table_start_idx = None
    
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
    
    # --- Pricing Calculations ---
    base_total_val = matched_row.get('Total', 0)
    try:
        base_equipment_cost = float(base_total_val)
    except (ValueError, TypeError):
        base_equipment_cost = 0.0

    marked_up_equipment = base_equipment_cost * markup_multiplier
    total_customer_investment = marked_up_equipment + labor_material_cost

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**SEER2:** {matched_row.get('SEER2', 'N/A')}")
        st.markdown(f"**Max Amp:** {matched_row.get('Max Amp', 'N/A')}")
        st.markdown(f"**Line Size:** {matched_row.get('Line Size', 'N/A')}")
        
    with col2:
        st.metric(label="Total System Cost (Marked Up Equipment)", value=f"${marked_up_equipment:,.2f}")
    
    # Final total investment display block
    st.markdown("---")
    st.subheader("Final Pricing")
    inv_col1, inv_col2 = st.columns(2)
    with inv_col1:
        st.write(f"Marked Up Equipment: `${marked_up_equipment:,.2f}`")
        st.write(f"Labor & Materials: `${labor_material_cost:,.2f}`")
    with inv_col2:
        st.metric(label="Total Customer Investment", value=f"${total_customer_investment:,.2f}")

    st.markdown("---")
    st.markdown("### Component Breakdown")
    
    third_component_label = "Coil"
    if "Air Handler" in selected_system:
        if "Heat Pump" in selected_system:
            third_component_label = "Heat Kit"
        else:
            third_component_label = "Coil / TXV / Heat Kit"

    outdoor_col = [c for c in df_selected.columns if 'Outdoor' in c][0]
    indoor_col = [c for c in df_selected.columns if 'Indoor' in c][0]
    third_col = df_selected.columns[8]

    prices = [i for i, col in enumerate(df_selected.columns) if col == 'Price']
    outdoor_price = matched_row.iloc[prices[0]] if len(prices) > 0 else "N/A"
    indoor_price = matched_row.iloc[prices[1]] if len(prices) > 1 else "N/A"
    third_price = matched_row.iloc[prices[2]] if len(prices) > 2 else "N/A"

    def format_price(val):
        try:
            return f"${float(val):,.2f}"
        except (ValueError, TypeError):
            return str(val)

    breakdown_data = {
        "Component": ["Outdoor Unit", "Indoor Unit", third_component_label],
        "Model Number": [matched_row[outdoor_col], matched_row[indoor_col], matched_row[third_col]],
        "Price": [format_price(outdoor_price), format_price(indoor_price), format_price(third_price)]
    }
    st.table(pd.DataFrame(breakdown_data))

    if 'Supplies#' in matched_row:
        st.info(f"**Supplies Kit required:** #{matched_row['Supplies#']}")

except FileNotFoundError:
    st.error(f"Could not find the data file '{excel_file}'. Please make sure it is uploaded in the same directory as this app.")
except Exception as e:
    st.error(f"Error initializing database or processing file: {e}")