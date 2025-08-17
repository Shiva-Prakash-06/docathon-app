import sqlite3
import os

DB_PATH = os.path.join('db', 'docathon.db')

def apply_migration():
    """
    Applies the migration to add tables for Rounds and Point Adjustments,
    and updates the matches table.
    """
    print(f"Connecting to database at: {DB_PATH}")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 1. Create the 'rounds' table
        print("Creating 'rounds' table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rounds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sport_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                round_type TEXT NOT NULL CHECK(round_type IN ('GROUP', 'KNOCKOUT', 'QUARTER_FINAL', 'SEMI_FINAL', 'FINAL')),
                FOREIGN KEY (sport_id) REFERENCES sports (id)
            )
        """)
        print("'rounds' table created or already exists.")

        # 2. Create the 'point_adjustments' table
        print("Creating 'point_adjustments' table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS point_adjustments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_id INTEGER NOT NULL,
                points INTEGER NOT NULL,
                reason TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (class_id) REFERENCES classes (id)
            )
        """)
        print("'point_adjustments' table created or already exists.")

        # 3. Update the 'matches' table to include a round_id
        print("Updating 'matches' table...")
        cursor.execute("PRAGMA table_info(matches)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'round_id' not in columns:
            cursor.execute("ALTER TABLE matches ADD COLUMN round_id INTEGER")
            print("Added 'round_id' column to 'matches' table.")
        else:
            print("'round_id' column already exists.")

        conn.commit()
        print("\nMigration applied successfully! Your database is now up to date.")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")

if __name__ == '__main__':
    apply_migration()