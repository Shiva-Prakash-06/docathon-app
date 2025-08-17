import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'db', 'docathon.db')

def clear_and_seed(cursor):
    """Clears and re-seeds all necessary tables."""
    print("Disabling foreign keys...")
    cursor.execute("PRAGMA foreign_keys = OFF;")

    # --- Clear Tables ---
    tables_to_clear = ['classes', 'sports']
    for table in tables_to_clear:
        print(f"Clearing {table} table...")
        cursor.execute(f"DELETE FROM {table};")
        cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}';")

    # --- Seed Data ---
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
    
    sports_to_add = [
        ("Badminton", 1), ("Basketball (B)", 1), ("Basketball (G)", 1),
        ("Carrom", 0), ("Chess", 0), ("Football", 1), ("Table Tennis", 1),
        ("Cricket Boys", 1), ("Cricket Girls", 1), ("Throwball", 1), ("Volleyball", 1)
    ]

    # --- Insert Data ---
    print("\nSeeding new classes...")
    cursor.executemany("INSERT INTO classes (name) VALUES (?)", [(name,) for name in classes_to_add])
    print(f"{len(classes_to_add)} classes seeded.")

    print("\nSeeding new sports...")
    cursor.executemany("INSERT INTO sports (name, has_scores) VALUES (?, ?)", sports_to_add)
    print(f"{len(sports_to_add)} sports seeded.")

    print("\nRe-enabling foreign keys...")
    cursor.execute("PRAGMA foreign_keys = ON;")


def main():
    """Main function to run the seeder."""
    print(f"Connecting to database at: {DB_PATH}")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        clear_and_seed(cursor)
        conn.commit()
        print("\nSeeding complete!")
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")

if __name__ == '__main__':
    main()