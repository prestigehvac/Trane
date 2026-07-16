import streamlit as st
import pandas as pd
import openpyxl

st.set_page_config(page_title="Prestige HVAC Quote Helper - Trane Edition", layout="wide")

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

    st.sidebar.header("Filter Systems")
    selected_system = st.sidebar.selectbox("Select System Type", system_types)

    system_cols = [item for item in parsed_columns if item[0] == selected_system]

    if system_cols:
        sys_df = pd.DataFrame()
        for _, metric, original_col in system_cols:
            sys_df[metric] = df_raw[original_col]
            
        sys_df = sys_df.iloc[5:].reset_index(drop=True)

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
                col1, col2 = st.columns([1, 3])

                with col1:
                    st.markdown("### Matchup Options")
                    selected_ton = st.selectbox("Select Tonnage Size", tonnages)

                filtered_df = sys_df[sys_df["Ton_Display"] == selected_ton].copy()

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

                with col2:
                    st.markdown(f"### Matchups for {selected_system} ({selected_ton})")
                    
                    for idx, row in filtered_df.iterrows():
                        with st.container():
                            st.markdown("---")
                            
                            outdoor_unit = row.get("Outdoor", "N/A")
                            indoor_unit = row.get("Indoor", "N/A")
                            coil_unit = row.get("Coil w/ orifice", row.get("Coil", "N/A"))
                            seer = row.get("SEER2", "N/A")
                            max_amp = row.get("Max Amp", "N/A")
                            line_size = row.get("Line Size", "N/A")
                            
                            all_prices = [row[col] for col in price_cols if isinstance(row[col], float)]
                            
                            out_price = all_prices[0] if len(all_prices) > 0 else 0.0
                            ind_price = all_prices[1] if len(all_prices) > 1 else 0.0
                            coil_price = all_prices[2] if len(all_prices) > 2 else 0.0
                            
                            calculated_total = out_price + ind_price + coil_price
                            sheet_total = row.get(total_col_key, calculated_total) if total_col_key else calculated_total

                            s_col1, s_col2, s_col3 = st.columns(3)
                            with s_col1:
                                st.markdown(f"**Outdoor Unit:**  \n`{outdoor_unit}`  \n(${out_price:,.2f})")
                                st.markdown(f"**Line Size:** `{line_size}`")
                            with s_col2:
                                st.markdown(f"**Indoor Unit:**  \n`{indoor_unit}`  \n(${ind_price:,.2f})")
                                st.markdown(f"**SEER2:** `{seer}`")
                            with s_col3:
                                st.markdown(f"**Coil:**  \n`{coil_unit}`  \n(${coil_price:,.2f})")
                                st.markdown(f"**Max Amp:** `{max_amp}`")

                            st.markdown(f"### **Total Matchup Price: ${sheet_total:,.2f}**")
            else:
                st.warning("No valid tonnage values found for this system configuration.")
        else:
            st.error(f"Could not locate a Tonnage ('Ton') column for '{selected_system}' inside your Excel file.")
    else:
        st.error("No valid system configuration structures parsed. Check the headers in your Excel sheet.")
else:
    st.info("Please verify that 'Trane Matchup 2026.xlsx' is present in your root directory.")