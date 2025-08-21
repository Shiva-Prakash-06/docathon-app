import sqlite3
import os

DB_PATH = os.path.join('db', 'docathon.db')

def apply_migration():
    """Adds the 'team_members' table to the database."""
    print(f"Connecting to database at: {DB_PATH}")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        print("Creating 'team_members' table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                photo_filename TEXT
            )
        """)
        print("'team_members' table created or already exists.")

        conn.commit()
        print("\nMigration applied successfully!")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    apply_migration()