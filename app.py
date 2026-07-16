import streamlit as st
import pandas as pd
import openpyxl

# 1. Set page config matching Amana layout (no flame emoji)
st.set_page_config(
    page_title="Prestige HVAC Quote Helper - Trane Edition", 
    page_icon="https://prestigehvac.com/wp-content/uploads/2026/06/prestige-logo-circle-1.jpg",
    layout="wide"
)

# 2. Add Company Logo centered ABOVE the title matching Amana repo code sizing
st.markdown(
    """
    <div style="text-align: center;">
        <img src="https://raw.githubusercontent.com/prestigehvac/Amana/main/prestige_logo.png" width="300">
    </div>
    """,
    unsafe_allow_html=True
)

# 3. Main Title (Flame icon removed completely)
st.markdown("<h1 style='text-align: center;'>Prestige HVAC Quote Helper - Trane Edition</h1>", unsafe_allow_html=True)

# 4. Data File Definition
EXCEL_FILE = "Trane Matchup 2026.xlsx"

@st.cache_data
def load_and_preprocess_data(file_path):
    try:
        df = pd.read_excel(file_path, sheet_name="Sheet1", header=None)
        return df
    except Exception as e:
        st.error(f"Error loading Excel file: {e}")
        return None

df_raw = load_and_preprocess_data(EXCEL_FILE)

if df_raw is not None:
    header_row_category = df_raw.iloc[3]
    header_row_metric = df_raw.iloc[4]

    current_category = None
    parsed_columns = []

    for col_idx in range(len(df_raw.columns)):
        cat_val = header_row_category.iloc[col_idx]
        metric_val = header_row_metric.iloc[col_idx]

        if pd.notnull(cat_val) and str(cat_val).strip() != "":
            current_category = str(cat_val).strip()

        if pd.notnull(metric_val) and str(metric_val).strip() != "":
            clean_metric = str(metric_val).strip()
            display_name = f"{current_category} | {clean_metric}" if current_category else clean_metric
            parsed_columns.append((col_idx, display_name))

    col_indices = [p[0] for p in parsed_columns]
    col_names = [p[1] for p in parsed_columns]

    df_clean = df_raw.iloc[5:].copy()
    df_clean = df_clean.iloc[:, col_indices]
    df_clean.columns = col_names
    df_clean = df_clean.dropna(how='all')

    def safe_parse_ton_display(val):
        if pd.isnull(val):
            return None
        s = str(val).strip()
        if not s:
            return None
        if "Ton" in s:
            return s
        try:
            f_val = float(s)
            if f_val.is_integer():
                return f"{int(f_val)} Ton"
            else:
                return f"{f_val} Ton"
        except ValueError:
            return s

    def clean_price(val):
        if pd.isnull(val):
            return 0.0
        s = str(val).replace('$', '').replace(',', '').strip()
        try:
            return float(s)
        except ValueError:
            return 0.0

    system_cols = [c for c in df_clean.columns if "System" in c or "Condenser" in c or "Furnace" in c or "Coil" in c or "Air Handler" in c]
    if len(system_cols) > 0:
        first_sys_col = system_cols[0]
        df_clean = df_clean.dropna(subset=[first_sys_col])

    st.sidebar.header("Filter Systems")

    all_tons = []
    ton_col = None
    for c in df_clean.columns:
        if "Ton" in c:
            ton_col = c
            raw_vals = df_clean[c].dropna().unique()
            for r in raw_vals:
                parsed = safe_parse_ton_display(r)
                if parsed and parsed not in all_tons:
                    all_tons.append(parsed)
            break

    if all_tons:
        selected_ton = st.sidebar.selectbox("Select System Size (Tonnage)", sorted(all_tons))
    else:
        selected_ton = None

    filtered_df = df_clean.copy()
    if selected_ton and ton_col:
        filtered_df['temp_ton_clean'] = filtered_df[ton_col].apply(safe_parse_ton_display)
        filtered_df = filtered_df[filtered_df['temp_ton_clean'] == selected_ton]
        filtered_df = filtered_df.drop(columns=['temp_ton_clean'])

    if not filtered_df.empty:
        st.subheader(f"Available {selected_ton if selected_ton else ''} Trane Options")
        
        for idx, row in filtered_df.iterrows():
            with st.container():
                st.markdown("---")
                
                sys_title_parts = []
                for col_name in row.index:
                    if any(x in col_name for x in ["System", "Condenser", "Furnace", "Coil", "Air Handler"]):
                        val = row[col_name]
                        if pd.notnull(val) and str(val).strip():
                            sys_title_parts.append(str(val).strip())
                
                sys_title = " - ".join(sys_title_parts) if sys_title_parts else f"System Option {idx}"
                st.write(f"### {sys_title}")
                
                cols = st.columns(3)
                col_idx = 0
                
                price_col_name = None
                total_price = 0.0
                
                for col_name in row.index:
                    if "Price" in col_name or "Total" in col_name:
                        price_col_name = col_name
                        total_price = clean_price(row[col_name])
                        continue
                    
                    val = row[col_name]
                    if pd.notnull(val) and str(val).strip() != "":
                        with cols[col_idx % 3]:
                            st.write(f"**{col_name.split('|')[-1].strip()}:** {val}")
                        col_idx += 1
                
                st.markdown(f"<h3 style='color: #FF4B4B;'>Total Price: ${total_price:,.2f}</h3>", unsafe_allow_html=True)
                
                # Dynamic Quote Calculations mimicking layout
                markup = st.slider("Markup (%)", min_value=0, max_value=200, value=100, step=5, key=f"markup_{idx}")
                labor_cost = st.number_input("Labor Cost ($)", min_value=0, value=1200, step=100, key=f"labor_{idx}")
                permit_cost = st.number_input("Permit & Misc ($)", min_value=0, value=400, step=50, key=f"permit_{idx}")
                
                equipment_marked_up = total_price * (1 + (markup / 100.0))
                quote_total = equipment_marked_up + labor_cost + permit_cost
                
                st.markdown(f"#### Calculated Quote Price: **${quote_total:,.2f}**")
    else:
        st.info("No matching Trane systems found for the selected tonnage.")