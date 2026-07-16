import streamlit as st
import pandas as pd

st.set_page_config(page_title="Prestige Quick Quote Tool - Trane Edition", layout="centered")

st.image("https://callprestigehvac.com/wp-content/uploads/2024/04/prestige-logo.png", width=200) # Optional: uses your web logo if available
st.title("Prestige Quick Quote Tool - Trane Edition")

# 1. Load and parse the Excel file
@st.cache_data
def load_and_parse_data(file_path):
    # Read the raw sheet without headers first to locate the tables
    df_raw = pd.read_excel(file_path, header=None)
    
    systems = {}
    current_system_name = None
    table_start_idx = None
    
    # Iterate through rows to find system headers and partition the tables
    for idx, row in df_raw.iterrows():
        val = str(row[0]).strip()
        
        # Identify the main category headers
        if "Air Conditioner with 80% AFUE" in val or "Air Conditioner with Air Handler" in val or "Heat Pump with Air Handler" in val:
            # If we were already tracking a table, save it before starting the next one
            if current_system_name and table_start_idx is not None:
                systems[current_system_name] = (table_start_idx, idx)
            current_system_name = val
            table_start_idx = idx + 1 # The row immediately after is the column headers ("Ton", "SEER2", etc.)
            
    # Save the last table section
    if current_system_name and table_start_idx is not None:
        systems[current_system_name] = (table_start_idx, len(df_raw))
        
    parsed_systems = {}
    
    # Extract and clean each table section
    for system_name, (start, end) in systems.items():
        # Get the subset of rows for this table
        sub_df = df_raw.iloc[start:end].copy()
        
        # Set the first row of this subset as the header
        sub_df.columns = sub_df.iloc[0]
        sub_df = sub_df[1:] # Drop the header row from the data rows
        
        # Clean column names (strip whitespace)
        sub_df.columns = [str(col).strip() for col in sub_df.columns]
        
        # Drop completely empty rows or rows where 'Ton' is empty
        sub_df = sub_df.dropna(subset=['Ton'])
        
        # Convert numeric columns to appropriate types
        sub_df['Ton'] = pd.to_numeric(sub_df['Ton'], errors='coerce')
        sub_df = sub_df.dropna(subset=['Ton']) # Remove any header repetitions or non-numeric rows
        
        parsed_systems[system_name] = sub_df
        
    return parsed_systems

# Adjust this file name to match your repository deployment file name
excel_file = "Trane Matchup 2026.xlsx"

try:
    system_tables = load_and_parse_data(excel_file)
    
    # 2. Sidebar/Dropdown Selection
    st.subheader("Select System Configuration")
    
    # Dropdown for System Type
    system_options = list(system_tables.keys())
    selected_system = st.selectbox("Select System Type", system_options)
    
    # Get the dataframe for the selected system
    df_selected = system_tables[selected_system]
    
    # Dropdown for Ton (dynamic based on selected system)
    ton_options = sorted(df_selected['Ton'].unique())
    # Format options nicely (e.g., 1.5, 2.0, 2.5)
    selected_ton = st.selectbox("Select Tonnage (Ton)", ton_options, format_func=lambda x: f"{x:.1f} Ton")
    
    # 3. Retrieve and Display Matchup details
    matched_row = df_selected[df_selected['Ton'] == selected_ton].iloc[0]
    
    st.markdown("---")
    st.subheader(f"System Details: {selected_ton:.1f} Ton")
    
    # Create clean display layout
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"**SEER2:** {matched_row.get('SEER2', 'N/A')}")
        st.markdown(f"**Max Amp:** {matched_row.get('Max Amp', 'N/A')}")
        st.markdown(f"**Line Size:** {matched_row.get('Line Size', 'N/A')}")
        
    with col2:
        # Format total cost nicely
        total_val = matched_row.get('Total', 'N/A')
        st.metric(label="Total System Cost", value=f"{total_val}")
    
    st.markdown("### Component Breakdown")
    
    # Determine component labels based on system type
    third_component_label = "Coil"
    if "Air Handler" in selected_system:
        if "Heat Pump" in selected_system:
            third_component_label = "Heat Kit"
        else:
            third_component_label = "Coil / TXV / Heat Kit"
            
    # Find column headers dynamically to avoid KeyErrors if they differ slightly
    outdoor_col = [c for c in df_selected.columns if 'Outdoor' in c][0]
    indoor_col = [c for c in df_selected.columns if 'Indoor' in c][0]
    
    # The 9th column (index 8) is typically the third component
    third_col = df_selected.columns[8] 
    
    # Price columns can sometimes be duplicated, so we index by positional locations
    prices = [i for i, col in enumerate(df_selected.columns) if col == 'Price']
    
    outdoor_price = matched_row.iloc[prices[0]] if len(prices) > 0 else "N/A"
    indoor_price = matched_row.iloc[prices[1]] if len(prices) > 1 else "N/A"
    third_price = matched_row.iloc[prices[2]] if len(prices) > 2 else "N/A"
    
    # Display details in a structured table
    breakdown_data = {
        "Component": ["Outdoor Unit", "Indoor Unit", third_component_label],
        "Model Number": [matched_row[outdoor_col], matched_row[indoor_col], matched_row[third_col]],
        "Price": [outdoor_price, indoor_price, third_price]
    }
    
    st.table(pd.DataFrame(breakdown_data))
    
    if 'Supplies#' in matched_row:
        st.info(f"**Supplies Kit required:** #{matched_row['Supplies#']}")

except FileNotFoundError:
    st.error(f"Could not find the data file '{excel_file}'. Please make sure it is uploaded in the same directory as this app.")
except Exception as e:
    st.error(f"Error initializing database or processing file: {e}")