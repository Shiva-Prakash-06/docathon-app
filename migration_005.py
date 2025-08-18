import sqlite3
import os

DB_PATH = os.path.join('db', 'docathon.db')

def apply_migration():
    """Adds the 'image_filename' column to the stories table."""
    print(f"Connecting to database at: {DB_PATH}")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        print("Updating 'stories' table...")
        cursor.execute("PRAGMA table_info(stories)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'image_filename' not in columns:
            cursor.execute("ALTER TABLE stories ADD COLUMN image_filename TEXT")
            print("Added 'image_filename' column to 'stories' table.")
        else:
            print("'image_filename' column already exists.")

        conn.commit()
        print("\nMigration applied successfully!")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    apply_migration()