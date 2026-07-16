import streamlit as st
import pandas as pd
import numpy as np
import os

# Set page config
st.set_page_config(
    page_title="Prestige HVAC Quote Helper - Trane Edition",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title & Brand Header
st.title("Prestige Quick Quote Tool (Trane Edition)")
st.markdown("---")

# File configuration
EXCEL_FILE = "Trane Matchup 2026.xlsx"

@st.cache_data
def load_and_preprocess_data(file_path):
    """
    Loads and cleans the Trane Matchup multi-column sheet.
    Dynamically identifies system types (column prefixes) and handles
    clean price/float conversions.
    """
    if not os.path.exists(file_path):
        st.error(f"Could not find the Excel file: '{file_path}' in the current directory.")
        return None

    # Load sheet. Trane matchup sheets often use hierarchical or wide layouts.
    df = pd.read_excel(file_path, sheet_name="Sheet1", header=None)
    
    # Let's inspect the headers to group them.
    # We find system names in the top rows or as prefixes in the columns.
    # Based on the schema, column names are styled as: 'System Name/Metric'
    # We reconstruct a clean dataframe from this layout.
    df_headers = pd.read_excel(file_path, sheet_name="Sheet1", header=4) # Headers start around row 5 (index 4)
    
    return df_headers

df_raw = load_and_preprocess_data(EXCEL_FILE)

if df_raw is not None:
    # 1. Parse and extract system types from columns
    # We split columns on '/' to find the categories/systems and their corresponding sub-metrics
    parsed_columns = []
    systems = set()
    
    for col in df_raw.columns:
        if "/" in str(col):
            parts = str(col).split("/")
            system_name = parts[0].strip()
            metric_name = parts[1].strip()
            parsed_columns.append((system_name, metric_name, col))
            systems.add(system_name)
        else:
            parsed_columns.append(("General", str(col).strip(), col))

    # Convert systems set to a sorted list
    system_list = sorted(list(systems))

    # --- Sidebar Admin & Inputs ---
    st.sidebar.header("⚙️ Admin Controls")
    
    # Upload fallback if they ever need to update it
    uploaded_file = st.sidebar.file_uploader("Upload New Trane Pricing Excel", type=["xlsx"])
    if uploaded_file is not None:
        # Save temporary or overwrite
        with open(EXCEL_FILE, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.sidebar.success("Pricing file updated successfully! Refreshing...")
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.header("Pricing Calculator")
    
    markup_multiplier = st.sidebar.slider(
        "Markup Multiplier",
        min_value=1.00,
        max_value=3.00,
        value=1.80,
        step=0.05
    )
    
    labor_material_cost = st.sidebar.number_input(
        "Labor & Material Cost ($)",
        min_value=0.0,
        value=1700.0,
        step=100.0
    )

    # --- Main Calculator Logic ---
    st.subheader("Configure System Estimate")
    col1, col2 = st.columns(2)

    with col1:
        selected_system = st.selectbox(
            "Select Trane System Type",
            options=system_list if system_list else ["No Systems Found"]
        )

    # Extract rows specifically for the chosen system type
    system_cols = [item for item in parsed_columns if item[0] == selected_system]
    
    if system_cols:
        # Build a temporary slice of the dataframe specifically representing this system's columns
        sys_df = pd.DataFrame()
        for _, metric, original_col in system_cols:
            sys_df[metric] = df_raw[original_col]
        
        # Clean any completely empty rows
        sys_df = sys_df.dropna(subset=["Ton"])
        
        # Convert Tonnage to clean strings/floats for matching
        sys_df["Ton_Display"] = sys_df["Ton"].apply(lambda x: f"{float(x):.1f} Ton" if pd.notnull(x) else "")
        tonnages = sys_df["Ton_Display"].unique()

        with col2:
            selected_ton = st.selectbox(
                "Select Tonnage",
                options=tonnages
            )

        # Filter database by Selected Tonnage
        matched_row = sys_df[sys_df["Ton_Display"] == selected_ton]

        if not matched_row.empty:
            # Safely grab the data from the first matched row
            row = matched_row.iloc[0]
            
            # Extract models and base cost
            outdoor_model = row.get("Outdoor", "N/A")
            indoor_model = row.get("Indoor", "N/A")
            coil_model = row.get("Coil w/ orifice", "N/A")
            seer2_rating = row.get("SEER2", "N/A")
            max_amp = row.get("Max Amp", "N/A")
            line_size = row.get("Line Size", "N/A")
            
            # Extract and parse prices (handling '$' and commas safely)
            def clean_price(val):
                if pd.isna(val):
                    return 0.0
                val_str = str(val).replace("$", "").replace(",", "").strip()
                try:
                    return float(val_str)
                except ValueError:
                    return 0.0

            outdoor_price = clean_price(row.get("Price", 0.0))
            # Some spreadsheets have multiple 'Price' headers under a merged block.
            # Let's retrieve by exact indexes or specific fallback keys if prices differ:
            raw_row_dict = matched_row.to_dict(orient='records')[0]
            
            # Reconstruct component and total prices directly from the original DataFrame row
            orig_row = df_raw.loc[matched_row.index[0]]
            
            # Find the pricing values
            prices = []
            for item in system_cols:
                if item[1] == "Price":
                    prices.append(clean_price(orig_row[item[2]]))
            
            outdoor_cost = prices[0] if len(prices) > 0 else 0.0
            indoor_cost = prices[1] if len(prices) > 1 else 0.0
            coil_cost = prices[2] if len(prices) > 2 else 0.0
            
            # Use original total column price or sum them
            distributor_total = clean_price(orig_row[[c[2] for c in system_cols if c[1] == "Total"][0]])
            if distributor_total == 0.0:
                distributor_total = outdoor_cost + indoor_cost + coil_cost

            # Calculate Retail Price matching your multiplier math:
            # Formula: (Distributor Cost * Markup Multiplier) + Labor & Material Costs
            calculated_retail_price = (distributor_total * markup_multiplier) + labor_material_cost

            st.markdown("---")
            st.subheader("Available Matchups & Customer Pricing")

            # Layout results
            res_col1, res_col2 = st.columns(2)
            
            with res_col1:
                st.metric(
                    label="Estimated Customer Investment", 
                    value=f"${calculated_retail_price:,.2f}",
                    help="Calculated as: (Equipment Cost * Multiplier) + Labor & Material Costs"
                )
                
                st.markdown("#### System Specifications")
                st.write(f"**SEER2 Rating:** {seer2_rating}")
                st.write(f"**Max Amp Breaker:** {max_amp}")
                st.write(f"**Refrigerant Line Size:** {line_size}")

            with res_col2:
                st.markdown("#### Equipment Breakdown")
                st.info(f"**Outdoor Condenser Model:** `{outdoor_model}`")
                st.info(f"**Indoor Furnace/Air Handler:** `{indoor_model}`")
                st.info(f"**Cased Coil:** `{coil_model}`")

            # Expandable technical comparison details 
            with st.expander("Show Distributor Pricing Summary (Internal Use Only)"):
                st.table(pd.DataFrame({
                    "Component": ["Outdoor Condenser", "Indoor Unit", "Coil System", "Total Distributor Cost"],
                    "Model": [outdoor_model, indoor_model, coil_model, "---"],
                    "Unit Cost": [f"${outdoor_cost:,.2f}", f"${indoor_cost:,.2f}", f"${coil_cost:,.2f}", f"${distributor_total:,.2f}"]
                }))
        else:
            st.warning("No pricing rows found matching this tonnage configuration.")
    else:
        st.error("No valid multi-level system headers matched your Trane matchup dataset. Please check the Excel format.")