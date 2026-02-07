import streamlit as st
import pandas as pd
import plotly.express as px
from processor import extract_receipt_data
from database import (init_db, save_receipt, get_all_receipts, delete_receipt, update_receipt, create_vendor_map_table,
                      update_vendor_map, save_budget, load_budget, load_currency, save_currency)


# Initialize Database
init_db()
create_vendor_map_table()

st.set_page_config(page_title="Receipt Organizer", layout="wide")
st.title("Receipt Expense Organizer")

# First, get the data from the database
history_df = get_all_receipts()

# Calculate the total spent immediately
if not history_df.empty:
    total_spent = history_df['total'].sum()
else:
    total_spent = 0.0

# --- SIDEBAR: UPLOAD ---
st.sidebar.header("Upload New Receipt")
uploaded_file = st.sidebar.file_uploader("Upload Image", type=["jpg", "png", "jpeg"])

st.sidebar.header("Budget Settings")
saved_budget = load_budget()
monthly_budget = st.sidebar.number_input(
    "Set Monthly Budget",
    min_value=0.0,
    value=saved_budget,
    step=50.0
)
if monthly_budget != saved_budget:
    save_budget(monthly_budget)
    st.rerun()

# Calculate percentage
if monthly_budget > 0:
    progress_percentage = min(total_spent / monthly_budget, 1.0) # Cap at 100% for the bar
else:
    progress_percentage = 0

if uploaded_file:
    with st.spinner("Analyzing Receipt..."):
        result = extract_receipt_data(uploaded_file)

        st.sidebar.subheader("Verify Data")
        vendor = st.sidebar.text_input("Vendor", value=result['vendor'])
        total = st.sidebar.number_input("Total", value=result['total'])
        date = st.sidebar.text_input("Date", value=result['date'])

        # 1. Define the list of options available in the UI
        options = ["Food & Dining", "Travel", "Supplies", "Services", "Groceries", "Transport",
                   "Miscellaneous"]

        # 2. Safety Check: If the guessed category isn't in the list, default to "Miscellaneous"
        guessed_category = result.get('category', "Miscellaneous")
        if guessed_category in options:
            default_idx = options.index(guessed_category)
        else:
            default_idx = options.index("Miscellaneous")

        # 3. Use the safe index in the selectbox
        category = st.sidebar.selectbox("Category", options, index=default_idx)

        if st.sidebar.button("✅ Save Expense"):
            final_data = {"vendor": vendor, "total": total, "date": date, "category": category,
                          "raw_text": result['raw_text']}
            save_receipt(final_data)

            # This line tells the app to remember this vendor/category combo
            update_vendor_map(vendor, category)

            st.sidebar.success("Saved!")
            st.rerun()


# --- CURRENCY SETTINGS ---
currency_list = ["USD", "RON", "EUR", "GBP", "CAD"]
saved_curr = load_currency()

selected_currency = st.sidebar.selectbox(
    "Select Currency",
    options=currency_list,
    index=currency_list.index(saved_curr)
)

if selected_currency != saved_curr:
    save_currency(selected_currency)
    st.rerun()



# --- MAIN DASHBOARD ---
history_df = get_all_receipts()

if not history_df.empty:
    # Calculate Insights
    total_spent = history_df['total'].sum()

    # Get the biggest single purchase
    biggest_row = history_df.loc[history_df['total'].idxmax()]
    biggest_vendor = biggest_row['vendor']
    biggest_amount = biggest_row['total']

    # Get the most frequent category
    top_cat = history_df['category'].value_counts().idxmax()

    # Display Metrics in 3 Columns
    m1, m2, m3 = st.columns(3)

    with m1:
        st.metric("Total Expenses", f"{total_spent:,.2f} {selected_currency}")

    with m2:
        st.metric("Biggest Spender", f"{biggest_vendor}", f"{biggest_amount:,.2f} {selected_currency}", delta_color="inverse")

    with m3:
        st.metric("Top Category", f"{top_cat}")

    st.divider()

    # --- BUDGET PROGRESS BAR ---
    st.write(f"**Monthly Budget Progress: {total_spent:,.2f} {selected_currency} / {monthly_budget:,.2f} {selected_currency}**")

    # Change bar color logic based on spending
    if total_spent > monthly_budget:
        st.error(f"⚠️ You are over budget by {total_spent - monthly_budget:,.2f} {selected_currency}!")
        st.progress(progress_percentage)  # This will be full/red-ish in some themes
    elif total_spent > (monthly_budget * 0.8):
        st.warning("Keep an eye out! You've used over 80% of your budget.")
        st.progress(progress_percentage)
    else:
        st.success("You are currently within your budget. Nice work!")
        st.progress(progress_percentage)

    # Charts Row
    col1, col2 = st.columns(2)
    with col1:
        fig_pie = px.pie(history_df, values='total', names='category', title="Spending by Category", hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        # Ensure date conversion is robust
        # 'errors=coerce' handles any messy strings by turning them into NaT (Not a Time)
        history_df['date_dt'] = pd.to_datetime(history_df['date'], dayfirst=True, errors='coerce')

        # Drop rows where date couldn't be parsed to avoid chart crashes
        df_sorted = history_df.dropna(subset=['date_dt']).sort_values('date_dt')

        if not df_sorted.empty:
            # Calculate the exact start and end dates from your data
            min_date = df_sorted['date_dt'].min()
            max_date = df_sorted['date_dt'].max()

            # Create the line chart
            fig_line = px.line(
                df_sorted,
                x='date_dt',
                y='total',
                title="Spending Timeline",
                markers=True,
                labels={'date_dt': 'Timeline', 'total': 'Amount'}
            )

            # FIX: Explicitly set the tick positions to data limits
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

# Pull the latest data
df = get_all_receipts()

if not df.empty:
    st.write("*You can edit cells directly in the table below and click 'Save Changes'.*")

    # Define the dropdown options (must match the sidebar list)
    cat_options = ["Food & Dining", "Travel", "Supplies", "Services", "Groceries", "Dining", "Transport",
                   "Miscellaneous"]

    # Interactive Data Editor with Dropdowns
    edited_df = st.data_editor(
        df,
        column_order=("id", "date", "vendor", "total", "category"),
        disabled=["id"],
        column_config={
            "category": st.column_config.SelectboxColumn(
                "Category",
                options=cat_options,
                required=True,
            )
        },
        key="receipt_editor",
        use_container_width=True
    )

    # Save Changes Button (Now updates both the Receipt and the database)
    if st.button("Save Table Changes"):
        for index, row in edited_df.iterrows():
            # Update the specific transaction
            update_receipt(row['id'], row['vendor'], row['total'], row['date'], row['category'])

            # Learning Loop: Update the map so future OCR guesses match this edit
            if row['vendor'] and row['category']:
                update_vendor_map(row['vendor'], row['category'])

        st.success("Database and Learning Model updated!")
        st.rerun()

    # Delete Section
    st.divider()
    st.subheader("Delete a Transaction")
    col_del1, col_del2 = st.columns([1, 3])

    with col_del1:
        id_to_delete = st.number_input("Enter ID to delete", min_value=1, step=1)
    with col_del2:
        st.write(" ")
        if st.button("Confirm Delete", type="primary"):
            delete_receipt(id_to_delete)
            st.warning(f"Record #{id_to_delete} deleted.")
            st.rerun()
else:
    st.info("No records to manage yet.")