import streamlit as st
import pandas as pd
import openpyxl

# Page Configuration matching Amana UI style
st.set_page_config(page_title="Prestige HVAC Quote Helper - Trane Edition", layout="wide")

# Custom CSS to match Amana's clean card designs, buttons, and layout
st.markdown("""
    <style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 1.5rem;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        font-weight: bold;
    }
    div.element-container img {
        border-radius: 10px;
    }
    .system-card {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .metric-label {
        font-weight: bold;
        color: #495057;
    }
    .metric-value {
        font-family: monospace;
        background-color: #e9ecef;
        padding: 2px 6px;
        border-radius: 4px;
        color: #212529;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Prestige HVAC Quote Helper")
st.subheader("Trane Edition (2026 Matchups)")

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
    # Header Parsing matching existing sheet morphology
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
            parsed_columns.append((current_category, clean_metric, df_raw.columns[col_idx]))

    system_types = sorted(list(set([item[0] for item in parsed_columns if item[0]])))

    # SIDEBAR: Aligned with Amana's filtering controls and markup math settings
    st.sidebar.header("Filter & Settings")
    
    selected_system = st.sidebar.selectbox("Select System Type", system_types)

    # Standard Pricing Markup slider matching Amana logic
    markup_percentage = st.sidebar.slider(
        "Standard Price Markup (%)", 
        min_value=0, 
        max_value=150, 
        value=35, 
        step=5,
        help="Applies a percentage markup to the cost pricing before calculating the final quote."
    )
    
    # Optional Custom Dollar Adjustment matching Amana features
    custom_adjustment = st.sidebar.number_input(
        "Flat Adjustments ($ +/-)", 
        value=0.0, 
        step=50.0,
        help="Add or subtract a flat dollar value to the calculated quote total."
    )

    if st.sidebar.button("Reset Filters"):
        st.rerun()

    # Get metrics specific to the selected system type
    system_cols = [item for item in parsed_columns if item[0] == selected_system]

    if system_cols:
        sys_df = pd.DataFrame()
        for _, metric, original_col in system_cols:
            sys_df[metric] = df_raw[original_col]
            
        sys_df = sys_df.iloc[5:].reset_index(drop=True)

        # Locate Tonnage configuration column
        ton_col_key = None
        for col_name in sys_df.columns:
            if col_name.strip().lower() == "ton":
                ton_col_key = col_name
                break
                
        if not ton_col_key:
            for col_name in sys_df.columns:
                if "ton" in col_name.lower():
                    ton_col_key = col_name
                    break

        if ton_col_key:
            sys_df = sys_df.dropna(subset=[ton_col_key])
            
            def safe_parse_ton_display(val):
                if pd.isnull(val):
                    return ""
                val_str = str(val).strip()
                if val_str == "":
                    return ""
                try:
                    return f"{float(val_str):.1f} Ton"
                except ValueError:
                    return ""

            sys_df["Ton_Display"] = sys_df[ton_col_key].apply(safe_parse_ton_display)
            sys_df = sys_df[sys_df["Ton_Display"] != ""]
            tonnages = sys_df["Ton_Display"].unique()

            if len(tonnages) > 0:
                # Top Layout matching Amana system design split
                col1, col2 = st.columns([1, 3])

                with col1:
                    st.markdown("### Select Capacity")
                    selected_ton = st.radio("Tonnage Size", tonnages, label_visibility="collapsed")

                filtered_df = sys_df[sys_df["Ton_Display"] == selected_ton].copy()

                # Clean cost helper matching original pricing logic
                def clean_price(val):
                    if pd.isnull(val):
                        return 0.0
                    val_str = str(val).replace('$', '').replace(',', '').strip()
                    try:
                        return float(val_str)
                    except ValueError:
                        return 0.0

                price_cols = [col for col in filtered_df.columns if "price" in col.lower()]
                for p_col in price_cols:
                    filtered_df[p_col] = filtered_df[p_col].apply(clean_price)

                total_col_key = None
                for col in filtered_df.columns:
                    if col.lower() == "total":
                        total_col_key = col
                        break

                if total_col_key:
                    filtered_df[total_col_key] = filtered_df[total_col_key].apply(clean_price)

                # Output Matchups in main layout column
                with col2:
                    st.markdown(f"### Current Matchups: {selected_system} ({selected_ton})")
                    
                    for idx, row in filtered_df.iterrows():
                        # Styled container block following the updated Amana aesthetic
                        st.markdown('<div class="system-card">', unsafe_allow_html=True)
                        
                        outdoor_unit = row.get("Outdoor", "N/A")
                        indoor_unit = row.get("Indoor", "N/A")
                        coil_unit = row.get("Coil w/ orifice", row.get("Coil", "N/A"))
                        seer = row.get("SEER2", "N/A")
                        max_amp = row.get("Max Amp", "N/A")
                        line_size = row.get("Line Size", "N/A")
                        
                        # Pricing calculations
                        all_prices = [row[col] for col in price_cols if isinstance(row[col], float)]
                        out_price = all_prices[0] if len(all_prices) > 0 else 0.0
                        ind_price = all_prices[1] if len(all_prices) > 1 else 0.0
                        coil_price = all_prices[2] if len(all_prices) > 2 else 0.0
                        
                        calculated_total_cost = out_price + ind_price + coil_price
                        sheet_total_cost = row.get(total_col_key, calculated_total_cost) if total_col_key else calculated_total_cost
                        
                        # Apply Amana-style markup and adjustments math
                        markup_factor = 1 + (markup_percentage / 100.0)
                        final_quoted_total = (sheet_total_cost * markup_factor) + custom_adjustment

                        # 3-Column Item Detail Layout
                        s_col1, s_col2, s_col3 = st.columns(3)
                        with s_col1:
                            st.markdown(f"<span class='metric-label'>Outdoor Unit:</span><br><code style='font-size:1.1em;'>{outdoor_unit}</code><br><small style='color: gray;'>Cost: ${out_price:,.2f}</small>", unsafe_allow_html=True)
                            st.markdown(f"<span class='metric-label'>Line Size:</span> <span class='metric-value'>{line_size}</span>", unsafe_allow_html=True)
                        with s_col2:
                            st.markdown(f"<span class='metric-label'>Indoor Unit:</span><br><code style='font-size:1.1em;'>{indoor_unit}</code><br><small style='color: gray;'>Cost: ${ind_price:,.2f}</small>", unsafe_allow_html=True)
                            st.markdown(f"<span class='metric-label'>SEER2:</span> <span class='metric-value'>{seer}</span>", unsafe_allow_html=True)
                        with s_col3:
                            st.markdown(f"<span class='metric-label'>Coil Unit:</span><br><code style='font-size:1.1em;'>{coil_unit}</code><br><small style='color: gray;'>Cost: ${coil_price:,.2f}</small>", unsafe_allow_html=True)
                            st.markdown(f"<span class='metric-label'>Max Amp:</span> <span class='metric-value'>{max_amp}</span>", unsafe_allow_html=True)

                        st.markdown("---")
                        
                        # Highlighting the calculated Quote Price vs Raw Cost
                        quote_col1, quote_col2 = st.columns(2)
                        with quote_col1:
                            st.markdown(f"<h4 style='margin:0;'>Est. Quote Total: <span style='color: #2e7d32;'>${final_quoted_total:,.2f}</span></h4>", unsafe_allow_html=True)
                        with quote_col2:
                            st.markdown(f"<p style='text-align: right; margin: 0; color: gray;'>Base Dealer Cost: ${sheet_total_cost:,.2f}</p>", unsafe_allow_html=True)
                            
                        st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.warning("No valid tonnage values found for this system configuration.")
        else:
            st.error(f"Could not locate a Tonnage ('Ton') column for '{selected_system}' inside your Excel file.")
    else:
        st.error("No valid system configuration structures parsed. Check the headers in your Excel sheet.")
else:
    st.info("Please verify that 'Trane Matchup 2026.xlsx' is present in your root directory.")