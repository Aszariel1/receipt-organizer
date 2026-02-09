import pandas as pd
from streamlit_gsheets import GSheetsConnection
import sqlite3
import streamlit as st
import requests
import gspread
from google.oauth2.service_account import Credentials

def pull_from_cloud(owner_name):
    clean_owner_name = str(owner_name).strip().lower()
    csv_url = "https://docs.google.com/spreadsheets/d/1jlQXj8mvRc8Q-RBmBCqQTkMXxqvIWfXChuOQtXOd1BQ/export?format=csv&gid=0"

    try:
        # Silent read
        cloud_df = pd.read_csv(csv_url)

        if cloud_df is not None and not cloud_df.empty:
            cloud_df.columns = cloud_df.columns.str.strip().str.lower()

            # Filter for user
            mask = cloud_df['owner'].astype(str).str.strip().str.lower() == clean_owner_name
            user_data = cloud_df[mask]

            if not user_data.empty:
                db_conn = sqlite3.connect('expenses.db')

                # Use the ID you already added
                needed_cols = ['id', 'vendor', 'total', 'date', 'category', 'raw_text']
                existing_cols = [col for col in needed_cols if col in user_data.columns]

                local_df = user_data[existing_cols]
                local_df.to_sql('receipts', db_conn, if_exists='replace', index=False)
                db_conn.close()
                return True
        return False
    except Exception:
        # Stay silent unless there is a major crash
        return False


def push_to_cloud(owner_name, data):
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

    try:
        creds_dict = st.secrets["connections"]["gsheets"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        sheet_id = "1jlQXj8mvRc8Q-RBmBCqQTkMXxqvIWfXChuOQtXOd1BQ"
        spreadsheet = client.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet("receipts")
        raw_total = str(data.get('total', '0')).replace('$', '').replace(',', '').strip()
        try:
            clean_total = float(raw_total)
        except:
            clean_total = 0.0
        new_id = len(worksheet.get_all_values())

        row_to_send = [
            new_id,
            str(owner_name).lower().strip(),
            str(data.get('vendor', 'Unknown')).strip(),
            clean_total,
            str(data.get('date', '')).strip(),
            str(data.get('category', 'Misc')).strip(),
            str(data.get('raw_text', ''))[:500]  # Limit text length to avoid overflow
        ]

        worksheet.append_row(row_to_send, value_input_option='USER_ENTERED')

        st.toast("✅ SUCCESS: Data is in the Cloud!")
        return True

    except Exception as e:
        st.error(f"❌ CLOUD ERROR: {e}")
        # This will show us if the error is "API Not Enabled" or "Permission Denied"
        if "API" in str(e):
            st.info("ACTION REQUIRED: Enable 'Google Sheets API' AND 'Google Drive API' in Google Cloud Console.")
        st.stop()
        return False


def delete_from_cloud(receipt_id):
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = st.secrets["connections"]["gsheets"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)

        spreadsheet = client.open_by_key("1jlQXj8mvRc8Q-RBmBCqQTkMXxqvIWfXChuOQtXOd1BQ")
        worksheet = spreadsheet.worksheet("receipts")

        # Find the row
        all_rows = worksheet.get_all_values()
        target_str = str(receipt_id).strip()

        row_idx = -1
        for i, row in enumerate(all_rows):
            # Column A is index 0
            if str(row[0]).strip() == target_str:
                row_idx = i + 1
                break

        if row_idx != -1:
            worksheet.delete_rows(row_idx)
            print(f"✅ Cloud: Deleted row {row_idx}")
            return True
        return False
    except Exception as e:
        print(f"❌ Cloud Error: {e}")
        return False