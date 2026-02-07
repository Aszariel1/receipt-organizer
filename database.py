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