import sqlite3
import os

DB_PATH = os.path.join('db', 'docathon.db')

def apply_migration():
    """Adds the 'counts_as_ball' column to the score_log table for over tracking."""
    print(f"Connecting to database at: {DB_PATH}")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        print("Updating score_log table...")
        # Add counts_as_ball column if it doesn't exist
        cursor.execute("PRAGMA table_info(score_log)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'counts_as_ball' not in columns:
            # Add the column with a default value of 0 for existing entries
            cursor.execute("ALTER TABLE score_log ADD COLUMN counts_as_ball INTEGER NOT NULL DEFAULT 0")
            print("Added 'counts_as_ball' column to score_log table.")
        else:
            print("'counts_as_ball' column already exists.")

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