import streamlit as st
import pandas as pd
import matcher
import io
import tempfile
import os

# Page configurations
st.set_page_config(page_title="Tally Automation Companion", layout="wide", page_icon="📊")

# Sidebar layout setup
with st.sidebar:
    st.title("🏢 Client Control Deck")
    
    # Client Addition Operations
    with st.expander("➕ Add New Client"):
        new_client_input = st.text_input("Enter Company Name:", key="new_client_name_field")
        if st.button("Register Client", use_container_width=True):
            if new_client_input.strip():
                if matcher.add_new_client(new_client_input):
                    st.success(f"Registered '{new_client_input}'!")
                    st.rerun()
                else:
                    st.error("Failed to register or client exists.")
            else:
                st.warning("Please enter a valid name.")

    # Fetch fresh client listing dynamically from cloud
    all_clients = matcher.get_all_clients()
    
    if all_clients:
        current_client = st.selectbox("🎯 Active Client", options=all_clients)
        
        with st.expander("🗑️ Remove a Client"):
            if st.button(f"Delete {current_client}", type="primary", use_container_width=True):
                if matcher.remove_client(current_client):
                    st.success("Deleted successfully!")
                    st.rerun()
    else:
        current_client = None
        st.info("Please add a client profile to get started.")

# --- MAIN SCREEN DASHBOARD DISPLAY ---
st.title("📊 Tally Accounting Automation Companion")

if not current_client:
    st.info("👉 Please add your first client company profile in the sidebar control deck to begin!")
else:
    st.subheader("📁 Upload Configuration Files")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Client Raw Sheet Settings")
        raw_file = st.file_uploader("Upload Client's Raw Excel Sheet (Transactions)", type=["xlsx", "xls"])
        raw_ledger_col = st.text_input("Ledger/Party Column Name in Raw Sheet:", value="Supplier Name")
        raw_item_col = st.text_input("Item Column Name (Leave default if none):", value="Item Name")

    with col2:
        st.markdown("### Tally Master Sheet Settings")
        master_file = st.file_uploader("Upload Tally Masters Sheet", type=["xlsx", "xls"])
        
        sub_col1, sub_col2 = st.columns(2)
        with sub_col1:
            master_ledger_sheet = st.text_input("Ledger Sheet Name:", value="party_master")
            master_ledger_col = st.text_input("Ledger Column Header:", value="PARTY NAME")
        with sub_col2:
            master_item_sheet = st.text_input("Item Sheet Name:", value="item_master")
            master_item_col = st.text_input("Item Column Header:", value="ITEM NAME")

    # Proceed only when both foundational files are uploaded
    if raw_file and master_file:
        try:
            df_raw = pd.read_excel(raw_file)
            
            has_ledgers = raw_ledger_col in df_raw.columns if raw_ledger_col else False
            has_items = raw_item_col in df_raw.columns if raw_item_col else False
            
            final_ledger_mappings = {}
            final_item_mappings = {}
            
            # --- PROCESS LEDGERS (IF COL EXISTS) ---
            if has_ledgers:
                df_master_ledgers = pd.read_excel(master_file, sheet_name=master_ledger_sheet)
                tally_masters_list = df_master_ledgers[master_ledger_col].dropna().astype(str).unique().tolist()
                raw_transaction_ledgers = df_raw[raw_ledger_col].dropna().astype(str).unique().tolist()
                
                st.markdown("---")
                st.subheader("🔍 Step 1: Review Ledger Mappings")
                
                for idx, raw_val in enumerate(raw_transaction_ledgers):
                    raw_str = str(raw_val).strip()
                    if not raw_str:
                        continue
                        
                    suggested_match, score = matcher.smart_match(raw_str, tally_masters_list, current_client, "Ledger")
                    
                    c_status, c_select, c_save = st.columns([2, 2, 1])
                    
                    with c_status:
                        if score == 100.0:
                            st.markdown(f"🟩 **Historical Match:** `{raw_str}` ➔ `{suggested_match}`")
                            final_match = suggested_match
                        else:
                            st.markdown(f"🟨 **Ledger Review Required:** `{raw_str}`")
                            final_match = suggested_match
                            
                    with c_select:
                        try:
                            def_idx = tally_masters_list.index(final_match)
                        except ValueError:
                            def_idx = 0
                            
                        chosen_match = st.selectbox(
                            f"Map Ledger '{raw_str}':",
                            options=tally_masters_list,
                            index=def_idx,
                            key=f"sel_led_{idx}_{raw_str}"
                        )
                        
                    with c_save:
                        force_save = st.checkbox("Change/Save", key=f"chk_led_{idx}_{raw_str}", value=(score < 100.0))
                        
                    if force_save or score < 100.0:
                        final_ledger_mappings[raw_str] = chosen_match
            else:
                st.info(f"ℹ️ Ledger column processing skipped (Column '{raw_ledger_col}' not found or box left blank).")

            # --- PROCESS ITEMS (ONLY IF COL EXISTS) ---
            if has_items:
                df_master_items = pd.read_excel(master_file, sheet_name=master_item_sheet)
                tally_items_list = df_master_items[master_item_col].dropna().astype(str).unique().tolist()
                raw_transaction_items = df_raw[raw_item_col].dropna().astype(str).unique().tolist()
                
                st.markdown("---")
                st.subheader("🔍 Step 2: Review Item Mappings")
                
                for idx, raw_val in enumerate(raw_transaction_items):
                    raw_str = str(raw_val).strip()
                    if not raw_str:
                        continue
                        
                    suggested_match, score = matcher.smart_match(raw_str, tally_items_list, current_client, "Item")
                    
                    c_status, c_select, c_save = st.columns([2, 2, 1])
                    
                    with c_status:
                        if score == 100.0:
                            st.markdown(f"🟩 **Historical Match:** `{raw_str}` ➔ `{suggested_match}`")
                            final_match = suggested_match
                        else:
                            st.markdown(f"🟨 **Item Review Required:** `{raw_str}`")
                            final_match = suggested_match
                            
                    with c_select:
                        try:
                            def_idx = tally_items_list.index(final_match)
                        except ValueError:
                            def_idx = 0
                            
                        chosen_match = st.selectbox(
                            f"Map Item '{raw_str}':",
                            options=tally_items_list,
                            index=def_idx,
                            key=f"sel_itm_{idx}_{raw_str}"
                        )
                        
                    with c_save:
                        force_save = st.checkbox("Change/Save", key=f"chk_itm_{idx}_{raw_str}", value=(score < 100.0))
                        
                    if force_save or score < 100.0:
                        final_item_mappings[raw_str] = chosen_match
            else:
                st.info(f"ℹ️ Item column processing skipped (Column '{raw_item_col}' not found or box left blank).")

            # --- STEP 3: COMMIT EXECUTION & EXCEL GENERATION ---
            st.markdown("---")
            if has_ledgers or has_items:
                if st.button("💾 Save All Decisions & Compile Final Excel", type="primary"):
                    success_count = 0
                    
                    # Save Ledger selections to Supabase
                    if has_ledgers and final_ledger_mappings:
                        for r_name, t_name in final_ledger_mappings.items():
                            try:
                                matcher.save_mapping(current_client, "Ledger", r_name, t_name)
                                success_count += 1
                            except Exception as e:
                                st.error(f"Error saving ledger '{r_name}': {e}")
                                
                    # Save Item selections to Supabase
                    if has_items and final_item_mappings:
                        for r_name, t_name in final_item_mappings.items():
                            try:
                                matcher.save_mapping(current_client, "Item", r_name, t_name)
                                success_count += 1
                            except Exception as e:
                                st.error(f"Error saving item '{r_name}': {e}")
                    
                    if success_count > 0:
                        st.success(f"✅ Cloud Sync Successful! Saved {success_count} adjustments globally.")
                    else:
                        st.info("ℹ️ Configuration reviewed. No new mapping adjustments needed to be written.")
                    
                    # Compile data sheet output dynamically
                    df_output = df_raw.copy()
                    
                    if has_ledgers:
                        full_ledger_dict = {}
                        for r_val in raw_transaction_ledgers:
                            r_str = str(r_val).strip()
                            m_best, _ = matcher.smart_match(r_str, tally_masters_list, current_client, "Ledger")
                            full_ledger_dict[r_str] = m_best
                        df_output["Mapped Tally Ledger Name"] = df_output[raw_ledger_col].astype(str).str.strip().map(full_ledger_dict)
                        
                    if has_items:
                        full_item_dict = {}
                        for r_val in raw_transaction_items:
                            r_str = str(r_val).strip()
                            m_best, _ = matcher.smart_match(r_str, tally_items_list, current_client, "Item")
                            full_item_dict[r_str] = m_best
                        df_output["Mapped Tally Item Name"] = df_output[raw_item_col].astype(str).str.strip().map(full_item_dict)
                    
                    output_buffer = io.BytesIO()
                    with pd.ExcelWriter(output_buffer, engine="xlsxwriter") as writer:
                        df_output.to_excel(writer, index=False, sheet_name="Automated Output")
                    processed_data = output_buffer.getvalue()
                    
                    st.download_button(
                        label="📥 Download Processed Tally Input Excel File",
                        data=processed_data,
                        file_name=f"{current_client}_automated_tally_sheet.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            else:
                st.error("❌ Neither the Ledger column nor Item column was found in the raw excel file.")
                
        except Exception as err:
            st.error(f"Formatting mismatch error. Please verify your settings boxes. Details: {err}")
