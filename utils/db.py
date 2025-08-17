import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'db', 'docathon.db')

def get_db_connection():
    """Establishes a connection to the database."""
    conn = sqlite3.connect(DB_PATH)
    # This allows you to access columns by name (like a dictionary)
    conn.row_factory = sqlite3.Row
    return conn