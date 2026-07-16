import streamlit as st
import pandas as pd
import re

# Set Page Config
st.set_page_config(
    page_title="Prestige HVAC Quote Helper - Trane Edition",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
    <style>
    .metric-card {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #dee2e6;
        margin-bottom: 15px;
    }
    .stButton>button {
        width: 100%;
    }
    </style>
""", unsafe_style_url="")

# Helper to load all sheet names
def get_all_sheets(file_url_or_path):
    try:
        xls = pd.ExcelFile(file_url_or_path)
        return xls.sheet_names
    except Exception as e:
        st.error(f"Error reading Excel file structure: {e}")
        return []

# Helper to clean currency values
def clean_price(val):
    if pd.isna(val) or val == "" or str(val).strip().lower() in ["n/a", "none", "-"]:
        return 0.0
    try:
        if isinstance(val, (int, float)):
            return float(val)
        cleaned = re.sub(r'[^\d\.\-]', '', str(val))
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0

# Helper to extract Tonnage from headers or cell content
def parse_tonnage_from_text(text):
    if not text or pd.isna(text):
        return None
    text_str = str(text).lower().strip()
    # Match patterns like "3 ton", "3.5 ton", "3.5t"
    match = re.search(r'(\d+(?:\.\d+)?)\s*(?:ton|t\b)', text_str)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    return None

# Load Excel data from the configured file ID
@st.cache_data(ttl=600)
def load_hvac_sheet(file_url, sheet_name):
    try:
        df = pd.read_excel(file_url, sheet_name=sheet_name)
        return df
    except Exception as e:
        st.error(f"Error loading sheet '{sheet_name}': {e}")
        return None

# Process the loaded sheet to map columns and structured matchups
def process_matchups(df):
    if df is None or df.empty:
        return []

    # Strip column headers
    df.columns = [str(c).strip() for c in df.columns]
    
    # Try to find target system column keys
    col_mapping = {}
    for col in df.columns:
        col_lower = col.lower()
        if "outdoor" in col_lower or "model" in col_lower or "system" in col_lower:
            col_mapping["system_model"] = col
        elif "price" in col_lower and "system" in col_lower:
            col_mapping["system_price"] = col
        elif "ton" in col_lower:
            col_mapping["tonnage"] = col
        elif "seer" in col_lower:
            col_mapping["seer"] = col
        elif "ahri" in col_lower:
            col_mapping["ahri"] = col
        elif "indoor" in col_lower or "furnace" in col_lower or "air handler" in col_lower:
            col_mapping["indoor_model"] = col
        elif "coil" in col_lower:
            col_mapping["coil_model"] = col

    # Build matches row by row
    matched_items = []
    current_ton = None
    
    for idx, row in df.iterrows():
        # Fallback check: Look at the row values to see if they define tonnage headers
        row_str = " ".join([str(val) for val in row.values if pd.notna(val)])
        row_ton = parse_tonnage_from_text(row_str)
        if row_ton is not None:
            current_ton = row_ton
            continue
            
        # Extract fields based on mapping
        ton_val = row.get(col_mapping.get("tonnage"), None) if "tonnage" in col_mapping else None
        ton = parse_tonnage_from_text(ton_val) if ton_val else current_ton
        
        system_model = row.get(col_mapping.get("system_model"), None) if "system_model" in col_mapping else None
        if pd.isna(system_model) or str(system_model).strip() == "":
            continue # Skip spacing/metadata rows
            
        system_price = clean_price(row.get(col_mapping.get("system_price"), 0))
        seer = row.get(col_mapping.get("seer"), "N/A")
        ahri = row.get(col_mapping.get("ahri"), "N/A")
        
        # Indoor Match detail parsing
        indoor = row.get(col_mapping.get("indoor_model"), "N/A")
        coil = row.get(col_mapping.get("coil_model"), "N/A")

        matched_items.append({
            "ton": ton if ton else "Unknown",
            "system_model": system_model,
            "system_price": system_price,
            "seer": seer,
            "ahri": ahri,
            "indoor": indoor,
            "coil": coil,
        })
        
    return matched_items

# --- Main App Execution ---

st.title("Prestige HVAC Quote Helper")
st.subheader("Trane Edition (2026 Matchups)")

# Using Google Sheets direct export link 
sheet_url = "https://docs.google.com/spreadsheets/d/1aRef-chlSkfAL6IUc7-sNcX3c7JmIgon/export?format=xlsx"

# Sidebar: Configurations and Adjustments
st.sidebar.header("Filter & Settings")

all_sheets = get_all_sheets(sheet_url)
if all_sheets:
    selected_sheet = st.sidebar.selectbox("Select System Type / Sheet", all_sheets)
else:
    selected_sheet = None

markup_percentage = st.sidebar.slider("Standard Price Markup (%)", min_value=0, max_value=200, value=80, step=5)
flat_adjustment = st.sidebar.number_input("Flat Adjustments ($ +/-)", value=0.0, step=50.0)

if st.sidebar.button("Reset Filters"):
    st.rerun()

# Processing Selected System Data
if selected_sheet:
    raw_df = load_hvac_sheet(sheet_url, selected_sheet)
    matchups = process_matchups(raw_df)
    
    if matchups:
        # Create DataFrame from matched options
        df_matchups = pd.DataFrame(matchups)
        
        # Filter: Unique Tonnages
        ton_options = sorted(list(set([m["ton"] for m in matchups if m["ton"] != "Unknown"])))
        selected_ton = st.selectbox("Select Tonnage Option (Tons)", ["All"] + [f"{t} Ton" for t in ton_options])
        
        # Display Grid
        for item in matchups:
            # Apply Tonnage filter
            if selected_ton != "All":
                target_ton = float(selected_ton.split()[0])
                if item["ton"] == "Unknown" or float(item["ton"]) != target_ton:
                    continue
                    
            # Pricing Formulas
            dealer_cost = item["system_price"]
            marked_up_price = dealer_cost * (1 + (markup_percentage / 100))
            final_price = marked_up_price + flat_adjustment
            
            with st.container():
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.markdown(f"### {item['system_model']} ({item['ton']} Ton)")
                    st.markdown(f"**Indoor Unit:** {item['indoor']} | **Coil:** {item['coil']}")
                    st.markdown(f"**SEER2:** {item['seer']} | **AHRI #:** {item['ahri']}")
                with col2:
                    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                    st.metric("Estimated Quote Price", f"${final_price:,.2f}")
                    st.markdown(f"<small>Base Equipment Cost: ${dealer_cost:,.2f}</small>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                with col3:
                    st.write("")
                    st.write("")
                    if st.button("Generate Quote Text", key=f"btn_{item['ahri']}_{item['system_model']}"):
                        quote_template = f"""
                        Prestige Heating & Air Proposal:
                        System: {item['system_model']} ({item['ton']} Ton, {item['seer']} SEER2)
                        Indoor Components: {item['indoor']} / {item['coil']}
                        AHRI Certified Reference: {item['ahri']}
                        Total Investment Option: ${final_price:,.2f} (Includes Standard Installation)
                        """
                        st.text_area("Copy proposal text:", value=quote_template.strip(), height=150)
                st.divider()
    else:
        st.info("Loaded successfully, but no matchups matched standard column patterns. Double-check your column naming conventions.")
else:
    st.warning("Please configure your Excel file setup on Google Sheets to load matchups.")