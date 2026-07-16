import streamlit as np
import streamlit as st
import pandas as pd

# Set page config
st.set_page_config(page_title="Prestige HVAC Quote Helper - Trane Edition", layout="wide")

# Custom CSS for styling
st.markdown("""
<style>
    .reportview-container {
        background: #f0f2f6;
    }
    .card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }
    .price-card {
        background-color: #e8f4f8;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #1f77b4;
        margin-bottom: 10px;
    }
    .price-value {
        font-size: 24px;
        font-weight: bold;
        color: #1f77b4;
    }
    .price-label {
        font-size: 14px;
        color: #555555;
    }
</style>
""", unsafe_allowed_html=True)

# Title
st.title("Prestige HVAC Quote Helper - Trane Edition")

# Load data
@st.cache_data
def load_data():
    # Load the Excel file
    # Replace with your actual file path or URL
    sheet_url = "https://docs.google.com/spreadsheets/d/1aRef-chlSkfAL6IUc7-sNcX3c7JmIgon/export?format=xlsx"
    
    xls = pd.ExcelFile(sheet_url)
    df_dict = {}
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        # Strip whitespace from column names
        df.columns = df.columns.str.strip()
        df_dict[sheet] = df
    return df_dict

try:
    data_dict = load_data()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# Available sheets (System Types)
system_types = list(data_dict.keys())

# Sidebar Selection
st.sidebar.header("System Settings")
selected_system_type = st.sidebar.selectbox("Select System Type", system_types)

# Get data for selected system type
df_selected = data_dict[selected_system_type].copy()

# Ensure we have clean column names and handle duplicates immediately
df_selected.columns = df_selected.columns.str.strip()

# De-duplicate column names by appending suffixes if duplicates exist
df_selected.columns = [
    f"{col}_{i}" if df_selected.columns.tolist().count(col) > 1 else col 
    for i, col in enumerate(df_selected.columns)
]

# Clean price columns to ensure they are numeric
price_cols = [
    'System Cost', 'Sub-Total', 'Cost - 10% Margin', 'Cost - 15% Margin',
    'Cost - 20% Margin', 'Price - 30% Margin', 'Price - 35% Margin',
    'Price - 40% Margin', 'Price - 45% Margin', 'Price - 50% Margin'
]

for col in price_cols:
    if col in df_selected.columns:
        # Clean single columns safely
        df_selected[col] = df_selected[col].astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False)
        df_selected[col] = pd.to_numeric(df_selected[col], errors='coerce').fillna(0.0)
    else:
        # Handle duplicated columns (e.g., 'System Cost_0', 'System Cost_1') safely
        matching_cols = [c for c in df_selected.columns if c.startswith(f"{col}_")]
        for m_col in matching_cols:
            df_selected[m_col] = df_selected[m_col].astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False)
            df_selected[m_col] = pd.to_numeric(df_selected[m_col], errors='coerce').fillna(0.0)

# Main Form
st.header(f"Configure {selected_system_type}")

col1, col2 = st.columns(2)

with col1:
    # 1. Size
    if 'Size (Tons)' in df_selected.columns:
        sizes = sorted(df_selected['Size (Tons)'].dropna().unique())
        selected_size = st.selectbox("Select System Size (Tons)", sizes)
        df_filtered = df_selected[df_selected['Size (Tons)'] == selected_size]
    elif 'Size' in df_selected.columns:
        sizes = sorted(df_selected['Size'].dropna().unique())
        selected_size = st.selectbox("Select System Size", sizes)
        df_filtered = df_selected[df_selected['Size'] == selected_size]
    else:
        st.warning("No 'Size' column found in this sheet.")
        df_filtered = df_selected.copy()

    # 2. Outdoor Model (if applicable)
    outdoor_col = [c for c in df_filtered.columns if 'Outdoor' in c or 'OD' in c or 'Condenser' in c]
    if outdoor_col:
        outdoor_col = outdoor_col[0]
        outdoor_models = sorted(df_filtered[outdoor_col].dropna().astype(str).unique())
        selected_outdoor = st.selectbox("Select Outdoor Unit Model", outdoor_models)
        df_filtered = df_filtered[df_filtered[outdoor_col] == selected_outdoor]
    else:
        selected_outdoor = None

    # 3. Indoor Model (if applicable)
    indoor_col = [c for c in df_filtered.columns if 'Indoor' in c or 'ID' in c or 'Coil' in c or 'Furnace' in c or 'Air Handler' in c]
    if indoor_col:
        indoor_col = indoor_col[0]
        indoor_models = sorted(df_filtered[indoor_col].dropna().astype(str).unique())
        selected_indoor = st.selectbox("Select Indoor Unit Model", indoor_models)
        df_filtered = df_filtered[df_filtered[indoor_col] == selected_indoor]
    else:
        selected_indoor = None

with col2:
    # 4. Heat Kit / Electric Heat (if applicable)
    heat_col = [c for c in df_filtered.columns if 'Heat Kit' in c or 'Electric Heat' in c or 'KW' in c]
    if heat_col:
        heat_col = heat_col[0]
        heat_kits = sorted(df_filtered[heat_col].dropna().astype(str).unique())
        # Add an "Any/None" option if there are multiple choices
        selected_heat = st.selectbox("Select Heat Kit / Electric Heat", heat_kits)
        df_filtered = df_filtered[df_filtered[heat_col] == selected_heat]
    else:
        selected_heat = None

# Matchups and Pricing Output
st.markdown("---")
st.subheader("Matchup Results & Pricing")

if df_filtered.empty:
    st.info("No matchups found matching the selected criteria. Try adjusting your selections.")
else:
    # If there are multiple rows, let user select a specific matchup ID or row
    if len(df_filtered) > 1:
        st.warning(f"Found {len(df_filtered)} matching matchups. Showing the first match. Use more filters above if needed.")
    
    # Get the single active matchup row
    matchup_row = df_filtered.iloc[0]
    
    # Display equipment details
    st.markdown('<div class="card">', unsafe_allowed_html=True)
    st.markdown("### Equipment Matchup Details")
    
    # Show columns that are not pricing columns
    detail_cols = [c for c in df_filtered.columns if c not in price_cols and not any(c.startswith(f"{p}_") for p in price_cols)]
    
    cols = st.columns(3)
    for idx, col in enumerate(detail_cols):
        with cols[idx % 3]:
            # Remove deduplication suffix from UI labels
            label = col.split('_')[0] if '_' in col else col
            st.write(f"**{label}:** {matchup_row[col]}")
    st.markdown('</div>', unsafe_allowed_html=True)
    
    # Display pricing cards
    st.markdown("### Estimated Margins & Pricing")
    
    # Resolve duplicated columns back to single values for clean pricing display
    def get_price_value(col_name):
        if col_name in matchup_row:
            return matchup_row[col_name]
        matching = [c for c in matchup_row.index if c.startswith(f"{col_name}_")]
        if matching:
            return matchup_row[matching[0]]
        return 0.0

    p_cols = st.columns(4)
    
    margins_to_show = [
        ('Price - 30% Margin', "30% Margin Price"),
        ('Price - 35% Margin', "35% Margin Price"),
        ('Price - 40% Margin', "40% Margin Price"),
        ('Price - 45% Margin', "45% Margin Price"),
    ]
    
    for idx, (col_name, label) in enumerate(margins_to_show):
        price_val = get_price_value(col_name)
        with p_cols[idx]:
            st.markdown(f"""
            <div class="price-card">
                <div class="price-label">{label}</div>
                <div class="price-value">${price_val:,.2f}</div>
            </div>
            """, unsafe_allowed_html=True)

    # Secondary Pricing Details Row
    st.markdown("#### Internal Cost Reference")
    c_cols = st.columns(4)
    
    costs_to_show = [
        ('System Cost', "Equipment Cost"),
        ('Sub-Total', "Job Sub-Total"),
        ('Cost - 10% Margin', "10% Margin Cost"),
        ('Cost - 15% Margin', "15% Margin Cost")
    ]
    
    for idx, (col_name, label) in enumerate(costs_to_show):
        cost_val = get_price_value(col_name)
        with c_cols[idx]:
            st.write(f"**{label}:** ${cost_val:,.2f}")