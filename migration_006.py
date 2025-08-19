import sqlite3
import os

DB_PATH = os.path.join('db', 'docathon.db')

def apply_migration():
    """Adds the 'scorecard_url' column to the matches table."""
    print(f"Connecting to database at: {DB_PATH}")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        print("Updating 'matches' table...")
        cursor.execute("PRAGMA table_info(matches)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'scorecard_url' not in columns:
            cursor.execute("ALTER TABLE matches ADD COLUMN scorecard_url TEXT")
            print("Added 'scorecard_url' column to 'matches' table.")
        else:
            print("'scorecard_url' column already exists.")

        conn.commit()
        print("\nMigration applied successfully!")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    apply_migration()