import streamlit as st
import pandas as pd
import plotly.express as px
from processor import extract_receipt_data
from database import init_db, save_receipt, get_all_receipts, delete_receipt, update_receipt

# Initialize Database
init_db()

st.set_page_config(page_title="Receipt Organizer", layout="wide")
st.title("Receipt Expense Organizer")

# --- SIDEBAR: UPLOAD ---
st.sidebar.header("Upload New Receipt")
uploaded_file = st.sidebar.file_uploader("Upload Image", type=["jpg", "png", "jpeg"])

if uploaded_file:
    with st.spinner("Analyzing Receipt..."):
        result = extract_receipt_data(uploaded_file)

        st.sidebar.subheader("Verify Data")
        vendor = st.sidebar.text_input("Vendor", value=result['vendor'])
        total = st.sidebar.number_input("Total", value=result['total'])
        date = st.sidebar.text_input("Date", value=result['date'])
        category = st.sidebar.selectbox("Category",
                                        ["Food & Dining", "Travel", "Supplies", "Services", "Miscellaneous"],
                                        index=["Food & Dining", "Travel", "Supplies", "Services",
                                               "Miscellaneous"].index(result['category']))

        if st.sidebar.button("✅ Save Expense"):
            final_data = {"vendor": vendor, "total": total, "date": date, "category": category,
                          "raw_text": result['raw_text']}
            save_receipt(final_data)
            st.sidebar.success("Saved!")
            st.rerun()

# --- MAIN DASHBOARD ---
history_df = get_all_receipts()

if not history_df.empty:
    # Top Stats
    total_spent = history_df['total'].sum()
    st.metric("Total Tracked Expenses", f"${total_spent:,.2f}")

    # Charts Row
    col1, col2 = st.columns(2)
    with col1:
        fig_pie = px.pie(history_df, values='total', names='category', title="Spending by Category", hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        # 1. Ensure date conversion is robust
        # 'errors=coerce' handles any messy strings by turning them into NaT (Not a Time)
        history_df['date_dt'] = pd.to_datetime(history_df['date'], dayfirst=True, errors='coerce')

        # Drop rows where date couldn't be parsed to avoid chart crashes
        df_sorted = history_df.dropna(subset=['date_dt']).sort_values('date_dt')

        if not df_sorted.empty:
            # Calculate the exact start and end dates from your data
            min_date = df_sorted['date_dt'].min()
            max_date = df_sorted['date_dt'].max()

            # 2. Create the line chart
            fig_line = px.line(
                df_sorted,
                x='date_dt',
                y='total',
                title="Spending Timeline",
                markers=True,
                labels={'date_dt': 'Timeline', 'total': 'Amount'}
            )

            # 3. FIX: Explicitly set the tick positions to your data limits
            fig_line.update_xaxes(
                type='date',
                tickmode='array',
                tickvals=[min_date, max_date],  # Force ticks ONLY at these two points
                ticktext=[min_date.strftime('%d/%m/%y'),
                          max_date.strftime('%d/%m/%y')],  # Force exact string format
                range=[min_date, max_date],  # Tighten the window so no padding exists
                showgrid=True
            )

            # Adjust layout to prevent the labels from being cut off at the edges
            fig_line.update_layout(margin=dict(l=20, r=20, t=40, b=20))

            st.plotly_chart(fig_line, use_container_width=True)

    # Data Table
    st.subheader("Recent Transactions")
    st.dataframe(history_df[['date', 'vendor', 'category', 'total']], use_container_width=True)
else:
    st.info("No receipts found. Upload an image in the sidebar to get started!")

st.divider()
st.subheader("Manage Transactions")
df = get_all_receipts()

if not df.empty:
    # 1. Interactive Data Editor
    st.write("*You can edit cells directly in the table below and click 'Save Changes'.*")

    # We use data_editor to allow inline editing
    df = get_all_receipts()
    df['date'] = pd.to_datetime(df['date'], dayfirst=True).dt.strftime('%d/%m/%y')
    edited_df = st.data_editor(
        df,
        column_order=("id", "date", "vendor", "total", "category"),
        disabled=["id"],  # Prevent users from changing the DB primary key
        key="receipt_editor",
        use_container_width=True
    )

    # 2. Save Changes Button (Update)
    if st.button("Save Table Changes"):
        for index, row in edited_df.iterrows():
            update_receipt(row['id'], row['vendor'], row['total'], row['date'], row['category'])
        st.success("Database updated!")
        st.rerun()

    # 3. Delete Section
    st.divider()
    st.subheader("Delete a Transaction")
    col_del1, col_del2 = st.columns([1, 3])

    with col_del1:
        id_to_delete = st.number_input("Enter ID to delete", min_value=1, step=1)
    with col_del2:
        st.write(" ")  # Alignment
        if st.button("Confirm Delete", type="primary"):
            delete_receipt(id_to_delete)
            st.warning(f"Record #{id_to_delete} deleted.")
            st.rerun()

else:
    st.info("No records to manage yet.")