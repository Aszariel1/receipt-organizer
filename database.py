import sqlite3
import pandas as pd

DB_NAME = "expenses.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS receipts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  vendor TEXT, total REAL, date TEXT, 
                  category TEXT, raw_text TEXT)''')
    conn.commit()
    conn.close()

def save_receipt(data):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO receipts (vendor, total, date, category, raw_text) VALUES (?, ?, ?, ?, ?)",
              (data['vendor'], data['total'], data['date'], data['category'], data['raw_text']))
    conn.commit()
    conn.close()

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