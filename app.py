import streamlit as st
import pandas as pd
import requests
import io

# Set page configurations
st.set_page_config(
    page_title="Prestige Quick Quote Tool - Trane Edition", 
    layout="centered"
)

# Display Company Logo above the title
st.image("https://prestigeairtx.com/wp-content/uploads/2022/11/Prestige-Logo.png", width=250)

st.title("Prestige Quick Quote Tool - Trane Edition")

# Direct Export Link for your Trane Matchup Google Sheet
sheet_url = "https://docs.google.com/spreadsheets/d/1aRef-chlSkfAL6IUc7-sNcX3c7JmIgon/export?format=xlsx"

@st.cache_data
def load_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        # Read without headers to parse multi-table structure manually
        df = pd.read_excel(io.BytesIO(response.content), header=None)
        return df
    except Exception as e:
        st.error(f"Error downloading Google Sheet: {e}")
        return None

df_raw = load_data(sheet_url)

if df_raw is not None:
    # Identify system section header locations
    sections = {}
    current_section = None
    section_start_idx = None
    
    # Exactly matching target sections from the Sheet
    target_systems = [
        "Air Conditioner with 80% AFUE Gas Furnace and Cased Coil R-454b 14.3 SEER2 w/ fixed orifice",
        "Air Conditioner with Air Handler and Heat Kit R-454b 14.3 SEER2",
        "Heat Pump with Air Handler and Heat Kit R-454b 14.3 SEER2"
    ]
    
    for idx, row in df_raw.iterrows():
        row_str = row.astype(str).tolist()
        matched_system = None
        for cell in row_str:
            cell_clean = cell.strip()
            if cell_clean in target_systems:
                matched_system = cell_clean
                break
        
        if matched_system:
            if current_section:
                sections[current_section] = (section_start_idx, idx)
            current_section = matched_system
            section_start_idx = idx
            
    if current_section:
        sections[current_section] = (section_start_idx, len(df_raw))
        
    # System selection UI
    system_type = st.selectbox("Select System Type", list(sections.keys()))
    
    if system_type:
        start_idx, end_idx = sections[system_type]
        section_df = df_raw.iloc[start_idx:end_idx].reset_index(drop=True)
        
        # Locate header row containing column labels (e.g., "Ton")
        header_row_idx = None
        for r_idx, row in section_df.iterrows():
            if "Ton" in row.astype(str).values:
                header_row_idx = r_idx
                break
                
        if header_row_idx is not None:
            # Set columns based on the matched headers row
            headers = section_df.iloc[header_row_idx].tolist()
            headers = [str(h).strip() if pd.notna(h) else f"Col_{i}" for i, h in enumerate(headers)]
            
            # Isolate rows containing values
            data_df = section_df.iloc[header_row_idx + 1:].copy()
            data_df.columns = headers
            
            # Remove empty and helper text rows to strictly parse tonnage numerical values
            data_df = data_df[data_df["Ton"].notna()]
            data_df["Ton"] = pd.to_numeric(data_df["Ton"], errors='coerce')
            data_df = data_df[data_df["Ton"].notna()]
            
            # Clean currency formatting
            def clean_price(val):
                if pd.isna(val):
                    return 0.0
                val_str = str(val).replace('$', '').replace(',', '').strip()
                try:
                    return float(val_str)
                except ValueError:
                    return 0.0
            
            # Select Tonnage UI
            tonnages = sorted(data_df["Ton"].unique())
            selected_ton = st.selectbox("Select Tonnage (Tons)", tonnages)
            
            row_match = data_df[data_df["Ton"] == selected_ton]
            
            if not row_match.empty:
                row_match = row_match.iloc[0]
                
                st.subheader(f"System Configuration: {selected_ton} Tons")
                
                # Extract dynamic variable column names (such as "Coil w/ orifice", "Coil w/ TXV", or "Heat Kit")
                cols = list(row_match.index)
                third_col_name = cols[8] if len(cols) > 8 else "Auxiliary Component"
                
                # Fetch Models
                outdoor_model = row_match.get("Outdoor", "N/A")
                indoor_model = row_match.get("Indoor", "N/A")
                third_model = row_match.iloc[8] if len(row_match) > 8 else "N/A"
                
                # Fetch and clean Prices
                outdoor_price = clean_price(row_match.iloc[5] if len(row_match) > 5 else 0)
                indoor_price = clean_price(row_match.iloc[7] if len(row_match) > 7 else 0)
                third_price = clean_price(row_match.iloc[9] if len(row_match) > 9 else 0)
                total_price = clean_price(row_match.get("Total", 0))
                
                # Key Metrics Display
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("SEER2 Rating", row_match.get("SEER2", "N/A"))
                    st.metric("Max Amp", row_match.get("Max Amp", "N/A"))
                with col2:
                    st.metric("Line Size", row_match.get("Line Size", "N/A"))
                    st.metric("Supplies Group", row_match.get("Supplies#", "N/A"))
                
                st.markdown("### Equipment Breakdown")
                
                breakdown_df = pd.DataFrame({
                    "Component": ["Outdoor Unit", "Indoor Unit", third_col_name],
                    "Model": [outdoor_model, indoor_model, third_model],
                    "Price": [f"${outdoor_price:,.2f}", f"${indoor_price:,.2f}", f"${third_price:,.2f}"]
                })
                st.table(breakdown_df)
                
                st.success(f"### **Total Cost: ${total_price:,.2f}**")
            else:
                st.warning("No configuration found for this Tonnage.")
        else:
            st.error("Could not parse column headers ('Ton') in this sheet section.")
else:
    st.error("Could not retrieve or read the data structure from your Excel Spreadsheet.")