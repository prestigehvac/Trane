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
    """
    if not os.path.exists(file_path):
        st.error(f"Could not find the Excel file: '{file_path}' in the current directory.")
        return None

    # Load starting at row index 4 (row 5) where headers reside
    df_headers = pd.read_excel(file_path, sheet_name="Sheet1", header=4)
    return df_headers

df_raw = load_and_preprocess_data(EXCEL_FILE)

if df_raw is not None:
    # 1. Parse and extract system types from columns safely
    parsed_columns = []
    systems = set()
    
    for col in df_raw.columns:
        col_str = str(col).strip()
        if "/" in col_str:
            # Split from the right side at the last slash to preserve names like "w/ fixed orifice"
            parts = col_str.rsplit("/", 1)
            system_name = parts[0].strip()
            metric_name = parts[1].strip()
            parsed_columns.append((system_name, metric_name, col))
            systems.add(system_name)
        else:
            parsed_columns.append(("General", col_str, col))

    # Convert systems set to a sorted list
    system_list = sorted(list(systems))

    # --- Sidebar Admin & Inputs ---
    st.sidebar.header("⚙️ Admin Controls")
    
    uploaded_file = st.sidebar.file_uploader("Upload New Trane Pricing Excel", type=["xlsx"])
    if uploaded_file is not None:
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
        # Build a temporary slice representing this system's columns
        sys_df = pd.DataFrame()
        for _, metric, original_col in system_cols:
            sys_df[metric] = df_raw[original_col]
        
        # Guard against a missing "Ton" column key by finding the closest match
        ton_col_key = "Ton"
        if "Ton" not in sys_df.columns:
            for col_name in sys_df.columns:
                if "ton" in col_name.lower():
                    ton_col_key = col_name
                    break

        if ton_col_key in sys_df.columns:
            # Clean empty values on the tonnage column
            sys_df = sys_df.dropna(subset=[ton_col_key])
            
            # Helper to safely parse tonnage numbers and ignore text strings
            def safe_parse_ton_display(val):
                if pd.isnull(val):
                    return ""
                val_str = str(val).strip()
                if val_str == "":
                    return ""
                try:
                    return f"{float(val_str):.1f} Ton"
                except ValueError:
                    return "" # Gracefully ignore non-numbers (e.g. headers or text)

            # Convert Tonnage to clean strings using our safe helper
            sys_df["Ton_Display"] = sys_df[ton_col_key].apply(safe_parse_ton_display)
            
            # Filter out empty display values
            sys_df = sys_df[sys_df["Ton_Display"] != ""]
            tonnages = sys_df["Ton_Display"].unique()

            if len(tonnages) > 0:
                with col2:
                    selected_ton = st.selectbox(
                        "Select Tonnage",
                        options=tonnages
                    )

                # Filter database by Selected Tonnage
                matched_row = sys_df[sys_df["Ton_Display"] == selected_ton]

                if not matched_row.empty:
                    row = matched_row.iloc[0]
                    
                    # Extract models and specifications safely using get fallbacks
                    outdoor_model = row.get("Outdoor", "N/A")
                    indoor_model = row.get("Indoor", "N/A")
                    
                    # Dynamic check for coil name variations in headers
                    coil_col_key = "Coil w/ orifice"
                    for col_name in sys_df.columns:
                        if "coil" in col_name.lower():
                            coil_col_key = col_name
                            break
                    
                    coil_model = row.get(coil_col_key, "N/A")
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

                    # Reconstruct component and total prices directly from the original DataFrame row
                    orig_row = df_raw.loc[matched_row.index[0]]
                    
                    prices = []
                    for item in system_cols:
                        if item[1] == "Price":
                            prices.append(clean_price(orig_row[item[2]]))
                    
                    outdoor_cost = prices[0] if len(prices) > 0 else 0.0
                    indoor_cost = prices[1] if len(prices) > 1 else 0.0
                    coil_cost = prices[2] if len(prices) > 2 else 0.0
                    
                    # Find the Total column safely
                    total_col_key = None
                    for item in system_cols:
                        if item[1] == "Total":
                            total_col_key = item[2]
                            break
                    
                    distributor_total = 0.0
                    if total_col_key:
                        distributor_total = clean_price(orig_row[total_col_key])
                    
                    if distributor_total == 0.0:
                        distributor_total = outdoor_cost + indoor_cost + coil_cost

                    # Calculate Retail Price
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
                st.warning("No valid numeric tonnages found in the selected system dataset.")
        else:
            st.error("Could not locate a Tonnage ('Ton') column for the selected system inside your Excel file.")
    else:
        st.error("No valid multi-level system headers matched your Trane matchup dataset. Please check the Excel format.")