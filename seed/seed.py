import sqlite3
import os

# Go up one level from /seed to the project root to find the db path
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'db', 'docathon.db')

def seed_data():
    """Inserts initial data for classes and sports into the database."""
    classes_to_add = [
        "1 BCOM A", "1 BCOM B", "1 BCOM C", "1 BCOM D", "1 BCOM F", "1 BCOM A&T", 
        "1 BCOM AFA", "1 BCOM SFH", "1 BCOM F&I A", "1 BCOM F&I B", "1 BSC A&A",
        "3 BCOM A", "3 BCOM B", "3 BCOM C", "3 BCOM D", "3 BCOM F", "3 BCOM A&T", 
        "3 BCOM AFA", "3 BCOM SFH", "3 BCOM F&I A", "3 BCOM F&I B", "3 BSC A&A",
        "5 BCOM A", "5 BCOM B", "5 BCOM C", "5 BCOM D", "5 BCOM F", "5 BCOM A&T", 
        "5 BCOM AFA", "5 BCOM SFH", "5 BCOM F&I A", "5 BCOM F&I B"
    ]
    
    # List of tuples: (Sport Name, Has Scores Boolean)
    sports_to_add = [
        ("Badminton", 1),
        ("Basketball (B)", 1),
        ("Basketball (G)", 1),
        ("Carrom", 0),  # Result only
        ("Chess", 0),   # Result only
        ("Football", 1),
        ("Table Tennis", 1),
        ("Cricket Boys", 1),
        ("Cricket Girls", 1),
        ("Throwball", 1),
        ("Volleyball", 1)
    ]

    print(f"Connecting to database at: {DB_PATH}")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Seed classes
        print("Seeding classes...")
        for class_name in classes_to_add:
            try:
                cursor.execute("INSERT INTO classes (name) VALUES (?)", (class_name,))
            except sqlite3.IntegrityError:
                print(f"Class '{class_name}' already exists. Skipping.")
        print(f"{len(classes_to_add)} classes processed.")

        # Seed sports
        print("\nSeeding sports...")
        for sport_name, has_scores in sports_to_add:
            try:
                cursor.execute("INSERT INTO sports (name, has_scores) VALUES (?, ?)", (sport_name, has_scores))
            except sqlite3.IntegrityError:
                print(f"Sport '{sport_name}' already exists. Skipping.")
        print(f"{len(sports_to_add)} sports processed.")
        
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