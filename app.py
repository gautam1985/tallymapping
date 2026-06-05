import streamlit as st
import pandas as pd
import matcher
import io

st.set_page_config(page_title="Tally Automation Companion", layout="wide")
st.title("📊 Tally Accounting Automation Companion")

# --- SIDEBAR: CLIENT MANAGER ---
st.sidebar.header("🏢 Client Control Deck")

with st.sidebar.expander("➕ Add New Client"):
    new_client_name = st.text_input("Enter Company Name", key="add_name")
    if st.button("Register Client"):
        if new_client_name:
            if matcher.add_new_client(new_client_name):
                st.success(f"Added!")
                st.rerun()

client_list = matcher.get_all_clients()

if not client_list:
    st.info("👈 Please add your first client company in the sidebar to begin!")
else:
    selected_client = st.sidebar.selectbox("🎯 Active Client", client_list)
    
    with st.sidebar.expander("🗑️ Remove a Client"):
        client_to_remove = st.selectbox("Select Client to Delete", client_list, key="remove_select")
        if st.button("⚠️ Force Delete Client & Memory"):
            if matcher.remove_client(client_to_remove):
                st.success(f"Removed {client_to_remove}!")
                st.rerun()

    st.sidebar.markdown("---")

    # --- MAIN ENGINE SETUP ---
    st.subheader("📁 Upload Configuration Files")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### **Client Raw Sheet Settings**")
        data_file = st.file_uploader("Upload Client's Raw Excel Sheet (Transactions)", type=["xlsx", "xls"], key=f"data_{selected_client}")
        ledger_col = st.text_input("Ledger/Party Column Name in Raw Sheet:", "Supplier")
        item_col = st.text_input("Item Column Name (Leave default if none):", "Item Name")

    with col2:
        st.markdown("##### **Tally Master Sheet Settings**")
        master_file = st.file_uploader("Upload Tally Masters Sheet", type=["xlsx", "xls"], key=f"master_{selected_client}")
        
        sub_col1, sub_col2 = st.columns(2)
        with sub_col1:
            ledger_sheet_name = st.text_input("Ledger Sheet Name:", "Sheet1")
            tally_ledger_master_col = st.text_input("Ledger Column Header:", "Ledger Name")
        with sub_col2:
            item_sheet_name = st.text_input("Item Sheet Name:", "Sheet2")
            tally_item_master_col = st.text_input("Item Column Header:", "Item Name")

    # --- PROCESSING ENGINE ---
    if data_file and master_file:
        try:
            df_raw = pd.read_excel(data_file)
            
            has_ledgers = ledger_col in df_raw.columns if ledger_col else False
            has_items = item_col in df_raw.columns if item_col else False
            
            final_ledger_mappings = {}
            final_item_mappings = {}

            # --- PROCESS LEDGERS (IF COL EXISTS) ---
            if has_ledgers:
                df_ledger_master = pd.read_excel(master_file, sheet_name=ledger_sheet_name)
                tally_ledgers = df_ledger_master[tally_ledger_master_col].dropna().unique().tolist()
                unique_excel_ledgers = df_raw[ledger_col].dropna().unique().tolist()
                
                st.markdown("### 🔍 Step 1: Review Ledger Mappings")
                for l_item in unique_excel_ledgers:
                    s_name, score = matcher.smart_match(l_item, tally_ledgers, selected_client, "Ledger")
                    
                    if score == 100.0:
                        col_text, col_chk = st.columns([3, 1])
                        with col_text:
                            st.markdown(f"🟩 **Historical Match:** `{l_item}` ➡️ `{s_name}`")
                        with col_chk:
                            edit_mode = st.checkbox("Change", key=f"chk_l_{selected_client}_{l_item}")
                        
                        if edit_mode:
                            d_idx = tally_ledgers.index(s_name) if s_name in tally_ledgers else 0
                            user_choice = st.selectbox(f"Override '{l_item}':", tally_ledgers, index=d_idx, key=f"ov_l_{selected_client}_{l_item}")
                            final_ledger_mappings[l_item] = user_choice
                        else:
                            final_ledger_mappings[l_item] = s_name
                    else:
                        ca, cb = st.columns([2, 2])
                        with ca: st.warning(f"🟨 **Ledger Review Required:** `{l_item}`")
                        with cb:
                            d_idx = tally_ledgers.index(s_name) if s_name in tally_ledgers else 0
                            user_choice = st.selectbox(f"Map Ledger '{l_item}':", tally_ledgers, index=d_idx, key=f"l_{selected_client}_{l_item}")
                            final_ledger_mappings[l_item] = user_choice
            else:
                st.info(f"ℹ️ Ledger column processing skipped (Column '{ledger_col}' not found or box left blank).")

            st.markdown("---")

            # --- PROCESS ITEMS (ONLY IF COL EXISTS) ---
            if has_items:
                df_item_master = pd.read_excel(master_file, sheet_name=item_sheet_name)
                tally_items = df_item_master[tally_item_master_col].dropna().unique().tolist()
                unique_excel_items = df_raw[item_col].dropna().unique().tolist()
                
                st.markdown("### 🔍 Step 2: Review Item Mappings")
                for i_item in unique_excel_items:
                    s_name, score = matcher.smart_match(i_item, tally_items, selected_client, "Item")
                    
                    if score == 100.0:
                        col_text, col_chk = st.columns([3, 1])
                        with col_text:
                            st.markdown(f"🟩 **Historical Match:** `{i_item}` ➡️ `{s_name}`")
                        with col_chk:
                            edit_mode = st.checkbox("Change", key=f"chk_i_{selected_client}_{i_item}")
                        
                        if edit_mode:
                            d_idx = tally_items.index(s_name) if s_name in tally_items else 0
                            user_choice = st.selectbox(f"Override '{i_item}':", tally_items, index=d_idx, key=f"ov_i_{selected_client}_{i_item}")
                            final_item_mappings[i_item] = user_choice
                        else:
                            final_item_mappings[i_item] = s_name
                    else:
                        ca, cb = st.columns([2, 2])
                        with ca: st.warning(f"🟨 **Item Review Required:** `{i_item}`")
                        with cb:
                            d_idx = tally_items.index(s_name) if s_name in tally_items else 0
                            user_choice = st.selectbox(f"Map Item '{i_item}':", tally_items, index=d_idx, key=f"i_{selected_client}_{i_item}")
                            final_item_mappings[i_item] = user_choice
            else:
                st.info(f"ℹ️ Item column processing skipped (Column '{item_col}' not found or box left blank).")

            # --- COMBINED SAVE & EXPORT TRACKER ---
            st.markdown("---")
            if has_ledgers or has_items:
                if st.button("💾 Save All Decisions & Compile Final Excel"):
                    if has_ledgers:
                        for k, v in final_ledger_mappings.items():
                            matcher.save_mapping(selected_client, "Ledger", k, v)
                        df_raw['Tally_Mapped_Ledger'] = df_raw[ledger_col].map(final_ledger_mappings)
                        
                    if has_items:
                        for k, v in final_item_mappings.items():
                            matcher.save_mapping(selected_client, "Item", k, v)
                        df_raw['Tally_Mapped_Item'] = df_raw[item_col].map(final_item_mappings)
                    
                    st.success(f"🧠 {selected_client}'s adjustments successfully saved to memory!")
                    
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        df_raw.to_excel(writer, index=False)
                    
                    st.download_button(
                        label=f"📥 Download One-Click Tally Import File",
                        data=buffer.getvalue(),
                        file_name=f"{selected_client}_Tally_Ready.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            else:
                st.error("❌ Neither the Ledger column nor Item column was found in the raw excel file.")
                
        except Exception as e:
            st.error(f"⚠️ Formatting mismatch error. Please verify your settings boxes. Details: {e}")