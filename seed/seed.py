import sqlite3
import os

# Go up one level from /seed to the project root to find the db path
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'db', 'docathon.db')

def clear_existing_data(cursor):
    """Clears existing non-essential data before seeding."""
    print("Clearing existing data from classes table...")
    # We must disable foreign keys to truncate tables with relationships
    cursor.execute("PRAGMA foreign_keys = OFF;")
    cursor.execute("DELETE FROM classes;")
    # It's a good idea to reset the autoincrement counter
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='classes';")
    print("Classes table cleared.")

def seed_data():
    """Inserts initial data for classes and sports into the database."""
    # Compiled list from all 4 images plus MCOM
    classes_to_add = [
        "1 BCOM A", "1 BCOM B", "1 BCOM C", "1 BCOM D", "1 BCOM F",
        "1 BCOM AFA", "1 BCOM A&T", "1 BCOM F&I A", "1 BCOM F&I B",
        "1 BCOM SF & 1 Bsc. A&A", "1 BCOM SF", "1 BSc. A&A",
        "3 BCOM A", "3 BCOM B", "3 BCOM C", "3 BCOM D", "3 BCOM F",
        "3 BCOM AFA", "3 BCOM F&I A", "3 BCOM F&I B", "3 BCOM A&T",
        "3 BCOM SF & 3 BSc. A&A",
        "5 BCOM A", "5 BCOM B", "5 BCOM C", "5 BCOM D", "5 BCOM F",
        "5 BCOM AFA", "5 BCOM F&I A", "5 BCOM F&I B", "5 BCOM A&T",
        "5 BCOM SF",
        "MCOM"
    ]
    
    # List of tuples: (Sport Name, Has Scores Boolean)
    sports_to_add = [
        ("Badminton", 1), ("Basketball (B)", 1), ("Basketball (G)", 1),
        ("Carrom", 0), ("Chess", 0), ("Football", 1), ("Table Tennis", 1),
        ("Cricket Boys", 1), ("Cricket Girls", 1), ("Throwball", 1), ("Volleyball", 1)
    ]

    print(f"Connecting to database at: {DB_PATH}")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Clear old class data first
        clear_existing_data(cursor)
        
        # Seed classes
        print("Seeding new classes...")
        for class_name in classes_to_add:
            try:
                cursor.execute("INSERT INTO classes (name) VALUES (?)", (class_name,))
            except sqlite3.IntegrityError:
                print(f"Class '{class_name}' already exists. Skipping.")
        print(f"{len(classes_to_add)} classes seeded.")

        # Re-enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON;")
        
        conn.commit()
        print("\nSeeding complete!")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")

if __name__ == '__main__':
    seed_data()