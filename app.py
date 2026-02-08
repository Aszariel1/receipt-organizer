import streamlit as st
import pandas as pd
import plotly.express as px
from processor import extract_receipt_data
from database import (init_db, save_receipt, get_all_receipts, delete_receipt, update_receipt, create_vendor_map_table,
                      update_vendor_map, save_budget, load_budget, load_currency, save_currency)
from sync_manager import pull_from_cloud

if 'saved_to_cloud' not in st.session_state:
    st.session_state.saved_to_cloud = False

# Initialize Database

init_db()
create_vendor_map_table()

# --- SIDEBAR: LOGIN ---

st.sidebar.header("Login")
user_name = st.sidebar.text_input("Username").strip().lower()

if user_name:
    # Check if we need to switch users
    if "current_user" not in st.session_state or st.session_state.current_user != user_name:
        with st.spinner(f"Switching to {user_name}..."):
            # Clear local SQLite
            import sqlite3

            conn = sqlite3.connect('expenses.db')
            conn.execute("DELETE FROM receipts")
            conn.commit()
            conn.close()

            # Pull data (Silent version)
            pull_from_cloud(user_name)

            # Update state and refresh
            st.session_state.current_user = user_name
            st.rerun()

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
    if "last_uploaded_file" not in st.session_state or st.session_state.last_uploaded_file != uploaded_file.name:
        st.session_state.saved_to_cloud = False
        st.session_state.last_uploaded_file = uploaded_file.name

    with st.spinner("Analyzing Receipt..."):
        result = extract_receipt_data(uploaded_file)

        st.sidebar.subheader("Verify Data")
        vendor = st.sidebar.text_input("Vendor", value=result['vendor'])
        total = st.sidebar.number_input("Total", value=result['total'])
        date = st.sidebar.text_input("Date", value=result['date'])

        # Define the list of options available in the UI
        options = ["Food & Dining", "Travel", "Supplies", "Services", "Groceries", "Transport",
                   "Miscellaneous"]

        # Safety Check: If the guessed category isn't in the list, default to "Miscellaneous"
        guessed_category = result.get('category', "Miscellaneous")
        if guessed_category in options:
            default_idx = options.index(guessed_category)
        else:
            default_idx = options.index("Miscellaneous")

        # Use the safe index in the selectbox
        category = st.sidebar.selectbox("Category", options, index=default_idx)

        if st.sidebar.button("✅ Save Expense"):
            if st.session_state.get('saved_to_cloud') == False:
                final_data = {
                    "vendor": vendor,
                    "total": total,
                    "date": date,
                    "category": category,
                    "raw_text": result['raw_text']
                }
                save_receipt(final_data, user_name)
                st.session_state.saved_to_cloud = True

                st.sidebar.success("Saved locally and synced!")
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
    if not history_df['category'].dropna().empty:
        top_cat = history_df['category'].value_counts().idxmax()
    else:
        top_cat = "None"  # Fallback if no categories exist yet

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
    st.dataframe(
        history_df[['vendor', 'total', 'date', 'category']],
        use_container_width=True,
        column_config={
            "total": st.column_config.NumberColumn(
                f"Total ({selected_currency})",  # Puts denomination in the header
                format=f"%.2f {selected_currency}"  # Shows: 3442.77 USD
            )
        }
    )
else:
    st.info("No receipts found. Upload an image in the sidebar to get started!")

st.divider()
# Initialize the toggle state if it doesn't exist
if "show_manage" not in st.session_state:
    st.session_state.show_manage = False

# Dedicated Manage Button
if st.button("Manage Transactions"):
    st.session_state.show_manage = not st.session_state.show_manage

# Hidden Management Section
if st.session_state.show_manage:
    st.subheader("Edit or Delete Transactions")

    # Refresh data from database
    manage_df = get_all_receipts()

    if not manage_df.empty:
        # Create a user-friendly "Display ID" that is always 1, 2, 3...
        # This replaces the "ugly" database IDs in the user's view
        manage_df.insert(0, '#', range(1, len(manage_df) + 1))

        st.write("*Edit rows below and click 'Save All Edits', or use the dropdown to delete.*")

        # Define category options for the dropdown in the table
        cat_options = ["Food & Dining", "Travel", "Supplies", "Services", "Groceries", "Transport", "Miscellaneous"]

        # The Data Editor (Hiding the real database 'id' entirely)
        edited_df = st.data_editor(
            manage_df,
            column_order=("#", "vendor", "total", "date", "category"),
            disabled=["#"],
            hide_index=True,
            column_config={
                "category": st.column_config.SelectboxColumn("Category", options=cat_options, required=True),
                "total": st.column_config.NumberColumn(
                    f"Total ({selected_currency})",
                    format=f"%.2f {selected_currency}"  # Shows: 3442.77 RON, etc.
                )
            },
            key="manage_editor_v2",
            use_container_width=True
        )

        # Action Buttons Row
        col_save, col_del = st.columns(2)

        with col_save:
            if st.button("Save All Edits"):
                for _, row in edited_df.iterrows():
                    # We still use the hidden 'id' column for the database update
                    update_receipt(row['id'], row['vendor'], row['total'], row['date'], row['category'])
                    if row['vendor'] and row['category']:
                        update_vendor_map(row['vendor'], row['category'])
                st.success("Changes saved successfully!")
                st.rerun()

        with col_del:
            # Clean Deletion using the Display ID (#)
            to_delete_display = st.selectbox("Select Row # to Delete", options=manage_df['#'])
            if st.button("Delete Selected Row", type="primary"):
                # Map the Display ID back to the REAL hidden database ID
                real_id = manage_df.loc[manage_df['#'] == to_delete_display, 'id'].values[0]
                delete_receipt(real_id)
                st.warning(f"Row #{to_delete_display} removed from database.")
                st.rerun()
    else:
        st.info("No records to manage yet.")