import streamlit as st
import pandas as pd
import numpy as np

# Set Page Config
st.set_page_config(
    page_title="Prestige HVAC Quote Helper - Trane Edition",
    page_icon="https://prestigehvac.com/wp-content/uploads/2021/04/cropped-prestige-hvac-logo-1-32x32.png",
    layout="wide"
)

# Custom CSS for styling (using the correct unsafe_allow_html parameter and removing generic emojis)
st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border-left: 5px solid #E31B23;
    }
    .system-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
        border: 1px solid #e9ecef;
    }
</style>
""", unsafe_allow_html=True)

# Helper function to parse sections from the Trane Excel sheet
@st.cache_data
def load_and_parse_data():
    file_path = "Trane Matchup 2026.xlsx"
    df_raw = pd.read_excel(file_path, header=None)
    
    sections = {}
    current_section = None
    headers = None
    section_rows = []
    
    for idx, row in df_raw.iterrows():
        row_list = [str(val).strip() for val in row.values if pd.notna(val)]
        if not row_list:
            continue
            
        first_val = str(row.iloc[0]).strip()
        if "Air Conditioner" in first_val or "Heat Pump" in first_val:
            if current_section and section_rows:
                sections[current_section] = pd.DataFrame(section_rows, columns=headers)
            current_section = first_val
            headers = None
            section_rows = []
            continue
            
        if "Ton" in row_list or "Tonnage" in row_list:
            headers = [str(h).strip() for h in row.values if pd.notna(h)]
            continue
            
        if current_section and headers and len(row_list) >= len(headers) - 2:
            cleaned_row = [row.iloc[i] for i in range(len(headers))]
            section_rows.append(cleaned_row)
            
    if current_section and section_rows:
        sections[current_section] = pd.DataFrame(section_rows, columns=headers)
        
    return sections

try:
    all_sections = load_and_parse_data()
except Exception as e:
    st.error(f"Error loading Excel file: {e}")
    all_sections = {}

# --- SIDEBAR LOGO & FILTERS ---
st.sidebar.image("https://prestigehvac.com/wp-content/uploads/2021/04/cropped-prestige-hvac-logo-1.png", use_container_width=True)
st.sidebar.markdown("### **System Configurator**")

# 1. System Type Selection
system_types = list(all_sections.keys())
selected_system_type = st.sidebar.selectbox(
    "Select System Type",
    options=system_types if system_types else ["No data found"]
)

# Parse selected dataset
df_selected = all_sections.get(selected_system_type, pd.DataFrame())

if not df_selected.empty:
    # Clean up pricing columns to float
    for col in df_selected.columns:
        if 'Price' in col or 'Total' in col:
            df_selected[col] = df_selected[col].astype(str).str.replace('$', '').str.replace(',', '').str.strip()
            df_selected[col] = pd.to_numeric(df_selected[col], errors='coerce')

    # Convert Ton to float
    df_selected['Ton'] = pd.to_numeric(df_selected['Ton'], errors='coerce')
    df_selected = df_selected.dropna(subset=['Ton'])

    # 2. Tonnage Selection
    ton_options = sorted(df_selected['Ton'].unique())
    selected_ton = st.sidebar.selectbox("Select Tonnage (Tons)", options=ton_options)

    # Filter data
    filtered_df = df_selected[df_selected['Ton'] == selected_ton]

    # 3. Markup & Pricing Adjustments
    st.sidebar.markdown("---")
    st.sidebar.markdown("### **Pricing Configuration**")
    markup_pct = st.sidebar.slider("Markup Percentage (%)", min_value=0, max_value=100, value=30, step=5) / 100.0
    add_labor = st.sidebar.number_input("Additional Labor / Fees ($)", min_value=0, value=1200, step=100)

    # --- MAIN CONTENT AREA ---
    # Header featuring the Prestige Logo matching the Amana layout
    col_header1, col_header2 = st.columns([1, 4])
    with col_header1:
        st.image("https://prestigehvac.com/wp-content/uploads/2021/04/cropped-prestige-hvac-logo-1.png", width=150)
    with col_header2:
        st.title("Prestige HVAC Quote Helper")
        st.subheader(f"System: {selected_system_type}")

    if not filtered_df.empty:
        row = filtered_df.iloc[0]

        # Calculate final cost breakdowns
        equipment_total = row.get('Total', 0)
        marked_up_total = equipment_total * (1 + markup_pct)
        final_price = marked_up_total + add_labor

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Equipment Cost (Base)", f"${equipment_total:,.2f}")
        with col2:
            st.metric(f"With {int(markup_pct*100)}% Markup", f"${marked_up_total:,.2f}")
        with col3:
            st.metric("Final Quote Price", f"${final_price:,.2f}")

        # Specs Layout Card
        st.markdown('<div class="system-card">', unsafe_allow_html=True)
        st.markdown("### **System Specifications**")
        
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            st.write(f"**Tonnage:** {row.get('Ton')} Tons")
            st.write(f"**SEER2:** {row.get('SEER2')}")
        with col_s2:
            st.write(f"**Max Amp:** {row.get('Max Amp')}")
            st.write(f"**Line Size:** {row.get('Line Size')}")
        with col_s3:
            st.write(f"**Supplies ID:** #{int(row.get('Supplies#', 0)) if pd.notna(row.get('Supplies#')) else 'N/A'}")
        st.markdown('</div>', unsafe_allow_html=True)

        # Equipment Breakdown Cards
        st.markdown("### **Equipment Breakdown**")
        col_b1, col_b2, col_b3 = st.columns(3)

        with col_b1:
            st.info(f"**Outdoor Unit (Condenser)**\n\nModel: `{row.get('Outdoor')}`\n\nBase Price: ${row.get('Price', 0):,.2f}")
        
        with col_b2:
            st.success(f"**Indoor Unit (Furnace/Air Handler)**\n\nModel: `{row.get('Indoor')}`\n\nBase Price: ${row.get('Price.1', 0):,.2f}")

        # Find dynamic third column (Coil w/ orifice, Coil w/ TXV, or Heat Kit)
        third_col_name = [c for c in filtered_df.columns if 'Coil' in c or 'Heat Kit' in c]
        if third_col_name:
            col_label = third_col_name[0]
            with col_b3:
                st.warning(f"**Auxiliary Component ({col_label})**\n\nModel: `{row.get(col_label)}`\n\nBase Price: ${row.get('Price.2', 0):,.2f}")

    else:
        st.warning("No matches found for the selected Tonnage.")
else:
    st.info("Please select a valid system configuration from the sidebar.")