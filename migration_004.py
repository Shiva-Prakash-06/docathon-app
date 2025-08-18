import sqlite3
import os

DB_PATH = os.path.join('db', 'docathon.db')

def apply_migration():
    """Adds the 'stories' table to the database."""
    print(f"Connecting to database at: {DB_PATH}")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        print("Creating 'stories' table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                author TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("'stories' table created or already exists.")

        conn.commit()
        print("\nMigration applied successfully!")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")

if __name__ == '__main__':
    apply_migration()