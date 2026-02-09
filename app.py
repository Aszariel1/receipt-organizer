import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from processor import extract_receipt_data
from database import (init_db, save_receipt, get_all_receipts, delete_receipt, update_receipt,
                      create_vendor_map_table, update_vendor_map, get_category_for_vendor,
                      save_budget, load_budget, load_currency, save_currency)
from sync_manager import pull_from_cloud

# Initialize Database
init_db()
create_vendor_map_table()

st.set_page_config(page_title="Receipt Organizer", layout="wide")

# # LOGIN GATE
if "current_user" not in st.session_state:
    url_user = st.query_params.get("user", "")
    if url_user:
        st.session_state.current_user = url_user
        st.rerun()

    st.markdown("<h1 style='text-align: center;'>Receipt Organizer</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Please enter your username</p>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        input_user = st.text_input("Username", key="login_input").strip().lower()
        if st.button("Login", use_container_width=True):
            if input_user:
                st.query_params["user"] = input_user
                st.session_state.current_user = input_user
                with st.spinner(f"Loading data..."):
                    conn = sqlite3.connect('expenses.db')
                    conn.execute("DELETE FROM receipts")
                    conn.commit()
                    conn.close()
                    pull_from_cloud(input_user)
                st.rerun()
    st.stop()

# # MAIN LOGIC
user_name = st.session_state.current_user

# --- SIDEBAR ---
if st.sidebar.button("Logout", key="sb_logout"):
    st.session_state.clear()
    st.query_params.clear()
    st.rerun()

st.sidebar.divider()
st.sidebar.header("Upload New Receipt")
uploaded_file = st.sidebar.file_uploader("Upload Image", type=["jpg", "png", "jpeg"])

st.sidebar.header("Budget Settings")
saved_budget = load_budget()
monthly_budget = st.sidebar.number_input("Set Monthly Budget", min_value=0.0, value=saved_budget, step=50.0)
if monthly_budget != saved_budget:
    save_budget(monthly_budget)
    st.rerun()

currency_list = ["USD", "RON", "EUR", "GBP", "CAD"]
saved_curr = load_currency()
selected_currency = st.sidebar.selectbox("Select Currency", options=currency_list,
                                         index=currency_list.index(saved_curr))
if selected_currency != saved_curr:
    save_currency(selected_currency)
    st.rerun()

# --- DATA LOADING ---
history_df = get_all_receipts()
total_spent = history_df['total'].sum() if not history_df.empty else 0.0
progress_percentage = min(total_spent / monthly_budget, 1.0) if monthly_budget > 0 else 0

# --- UPLOAD LOGIC & SMART MAPPING ---
if uploaded_file:
    if "last_file" not in st.session_state or st.session_state.last_file != uploaded_file.name:
        st.session_state.saved_to_cloud = False
        st.session_state.last_file = uploaded_file.name

    with st.spinner("Analyzing..."):
        result = extract_receipt_data(uploaded_file)
        st.sidebar.subheader("Verify Data")
        v = st.sidebar.text_input("Vendor", value=result['vendor'])
        t = st.sidebar.number_input("Total", value=result['total'])
        d = st.sidebar.text_input("Date", value=result['date'])

        # SMART MAPPING LOGIC
        cats = ["Food & Dining", "Travel", "Supplies", "Services", "Groceries", "Transport", "Miscellaneous"]

        # Check if we have seen this vendor before
        remembered_cat = get_category_for_vendor(v)
        if remembered_cat:
            default_cat = remembered_cat
        else:
            default_cat = result.get('category', "Miscellaneous")

        idx = cats.index(default_cat) if default_cat in cats else 6
        c = st.sidebar.selectbox("Category", cats, index=idx)

        if st.sidebar.button("✅ Save Expense"):
            if not st.session_state.get('saved_to_cloud'):
                save_receipt({"vendor": v, "total": t, "date": d, "category": c, "raw_text": result['raw_text']},
                             user_name)
                # Update memory for next time
                update_vendor_map(v, c)
                st.session_state.saved_to_cloud = True
                pull_from_cloud(user_name)
                st.rerun()

# --- VISUAL DASHBOARD ---
st.title("Receipt Expense Organizer")

if not history_df.empty:
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Expenses", f"{total_spent:,.2f} {selected_currency}")
    biggest = history_df.loc[history_df['total'].idxmax()]
    m2.metric("Biggest Spender", f"{biggest['vendor']}", f"{biggest['total']:,.2f} {selected_currency}")
    top_c = history_df['category'].value_counts().idxmax()
    m3.metric("Top Category", top_c)

    st.divider()
    st.markdown(f"**Budget Usage:** {total_spent:,.2f} / {monthly_budget:,.2f} {selected_currency}")
    st.progress(progress_percentage)

    st.subheader("Recent Transactions")
    display_df = history_df.copy()
    display_df['total'] = display_df['total'].apply(lambda x: f"{x:,.2f} {selected_currency}")
    st.dataframe(display_df[['vendor', 'total', 'date', 'category']], use_container_width=True, hide_index=True)

    st.divider()
    col_pie, col_line = st.columns(2)
    with col_pie:
        st.subheader("Spending by Category")
        fig_pie = px.pie(history_df, values='total', names='category', hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_line:
        st.subheader("Spending Timeline")
        try:
            df_plot = history_df.copy()
            df_plot['date_dt'] = pd.to_datetime(df_plot['date'], dayfirst=True, errors='coerce')
            df_plot = df_plot.dropna(subset=['date_dt']).sort_values('date_dt')
            if not df_plot.empty:
                fig_line = px.line(df_plot, x='date_dt', y='total', markers=True,
                                   color='category', hover_data=['vendor'],
                                   labels={'date_dt': 'Date', 'total': f'Amount ({selected_currency})'})
                st.plotly_chart(fig_line, use_container_width=True)
        except:
            st.info("Timeline rendering...")

    # --- MANAGEMENT SECTION ---
    st.divider()
    if "show_manage" not in st.session_state: st.session_state.show_manage = False

    if st.button("Manage Transactions", key="toggle_mgr"):
        st.session_state.show_manage = not st.session_state.show_manage

    if st.session_state.show_manage:
        manage_df = history_df.copy()
        manage_df.insert(0, '#', range(1, len(manage_df) + 1))

        edited = st.data_editor(
            manage_df,
            column_config={
                "id": None, "raw_text": None,
                "total": st.column_config.NumberColumn(f"total ({selected_currency})",
                                                       format=f"%.2f {selected_currency}")
            },
            hide_index=True, use_container_width=True, key="main_editor"
        )

        ctrl_col1, ctrl_col2 = st.columns([1, 4])
        with ctrl_col1:
            if st.button("Save Edits", use_container_width=True):
                for _, row in edited.iterrows():
                    if pd.notna(row['id']):
                        update_receipt(row['id'], row['vendor'], row['total'], row['date'], row['category'])
                        update_vendor_map(row['vendor'], row['category'])  # Update mapping on edit too
                pull_from_cloud(user_name)
                st.rerun()
        with ctrl_col2:
            row_to_del = st.selectbox("Select Row # to Delete", options=manage_df['#'], label_visibility="collapsed")

        if st.button("🗑️ Delete Selected Row", type="primary", use_container_width=True):
            selected_row = manage_df.loc[manage_df['#'] == row_to_del]
            if not selected_row.empty:
                real_id_val = selected_row['id'].values[0]
                if pd.notna(real_id_val):
                    delete_receipt(int(real_id_val))
                    pull_from_cloud(user_name)
                    st.rerun()
else:
    st.info("No receipts found.")