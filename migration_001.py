import sqlite3
import os

DB_PATH = os.path.join('db', 'docathon.db')

def apply_migration():
    """Applies the non-destructive migration for the live scoring feature."""
    print(f"Connecting to database at: {DB_PATH}")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        print("Creating score_log table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS score_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER NOT NULL,
                team_id INTEGER NOT NULL,
                points_scored INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (match_id) REFERENCES matches (id),
                FOREIGN KEY (team_id) REFERENCES classes (id)
            )
        """)

        print("Updating matches table...")
        # Add live_match_state column if it doesn't exist
        cursor.execute("PRAGMA table_info(matches)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'live_match_state' not in columns:
            cursor.execute("ALTER TABLE matches ADD COLUMN live_match_state TEXT")
            print("Added 'live_match_state' column to matches table.")
        else:
            print("'live_match_state' column already exists.")

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