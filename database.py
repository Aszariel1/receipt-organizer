import sqlite3
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from sync_manager import push_to_cloud
DB_NAME = "expenses.db"


def init_db():
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS receipts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, vendor TEXT, total REAL, date TEXT, category TEXT, raw_text TEXT)''')

    # Create settings table with both columns immediately
    c.execute('''CREATE TABLE IF NOT EXISTS settings
                 (key TEXT PRIMARY KEY, value REAL, value_text TEXT)''')
    conn.commit()
    conn.close()


def sync_from_cloud(owner_name):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # Read the backup sheet
        df = conn.read(ttl=0)  # ttl=0 forces a fresh pull from Google

        # Filter for this specific user
        user_data = df[df['owner'] == owner_name]

        if not user_data.empty:
            import sqlite3
            db_conn = sqlite3.connect('expenses.db')
            # Inject the cloud data into your local SQLite
            # We drop 'owner' so it fits your existing SQLite table structure
            user_data.drop(columns=['owner']).to_sql('receipts', db_conn, if_exists='replace', index=False)
            db_conn.close()
            return True
    except Exception as e:
        print(f"Cloud sync failed: {e}")
    return False


def save_receipt(data, owner):
    import sqlite3
    # Save to your local computer first
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute("INSERT INTO receipts (vendor, total, date, category, raw_text) VALUES (?, ?, ?, ?, ?)",
              (data['vendor'], data['total'], data['date'], data['category'], data['raw_text']))
    conn.commit()
    conn.close()

    # TRIGGER THE CLOUD SYNC
    try:
        from sync_manager import push_to_cloud
        push_to_cloud(owner, data)
    except Exception as e:
        print(f"Cloud trigger failed: {e}")



def push_to_cloud(owner, vendor, total, date, category):
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl=0)

    new_entry = pd.DataFrame([{
        "owner": owner,
        "vendor": vendor,
        "total": total,
        "date": date,
        "category": category
    }])

    updated_df = pd.concat([df, new_entry], ignore_index=True)
    conn.update(data=updated_df)


def get_all_receipts():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM receipts ORDER BY id DESC", conn)
    conn.close()
    return df

def delete_receipt(receipt_id):
    """Removes a record from the DB by ID."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM receipts WHERE id = ?", (receipt_id,))
    conn.commit()
    conn.close()

def update_receipt(receipt_id, vendor, total, date, category):
    """Updates an existing record."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""UPDATE receipts 
                 SET vendor = ?, total = ?, date = ?, category = ? 
                 WHERE id = ?""",
              (vendor, total, date, category, receipt_id))
    conn.commit()
    conn.close()

def get_category_from_db(vendor_name):
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    # We use a case-insensitive search to be safe
    c.execute("SELECT category FROM vendor_map WHERE LOWER(vendor_name) = LOWER(?)", (vendor_name,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def create_vendor_map_table():
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS vendor_map
                 (vendor_name TEXT PRIMARY KEY, category TEXT)''')
    conn.commit()
    conn.close()

def update_vendor_map(vendor_name, category):
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    # "INSERT OR REPLACE" handles updating the category if the vendor already exists
    c.execute("INSERT OR REPLACE INTO vendor_map (vendor_name, category) VALUES (?, ?)",
              (vendor_name, category))
    conn.commit()
    conn.close()

def save_budget(amount):
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    # Create a simple settings table if it doesn't exist
    c.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value REAL)')
    c.execute('INSERT OR REPLACE INTO settings (key, value) VALUES ("budget", ?)', (amount,))
    conn.commit()
    conn.close()

def load_budget():
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value REAL)')
    c.execute('SELECT value FROM settings WHERE key = "budget"')
    result = c.fetchone()
    conn.close()
    return result[0] if result else 500.0  # Default to 500 if not set

def save_currency(currency_code):
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO settings (key, value_text) VALUES ("currency", ?)', (currency_code,))
    conn.commit()
    conn.close()

def load_currency():
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    # (Note: SQLite ignores the above if the column already exists in some versions,
    # but for safety, a try/except or manual DB check is better)
    c.execute('SELECT value_text FROM settings WHERE key = "currency"')
    result = c.fetchone()
    conn.close()
    return result[0] if result and result[0] else "USD"