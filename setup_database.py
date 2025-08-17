import sqlite3
import os

# Define the path for the database
DB_FOLDER = 'db'
DB_NAME = 'docathon.db'
DB_PATH = os.path.join(DB_FOLDER, DB_NAME)
SCHEMA_PATH = 'schema.sql'

def setup_database():
    """Creates the database and its tables based on the schema file."""
    # Ensure the db folder exists
    os.makedirs(DB_FOLDER, exist_ok=True)
    
    print(f"Setting up database at: {DB_PATH}")
    
    try:
        # Connect to the database (this will create the file if it doesn't exist)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Read the schema file
        with open(SCHEMA_PATH, 'r') as f:
            schema_script = f.read()
            
        # Execute the schema script to create tables
        cursor.executescript(schema_script)
        conn.commit()
        
        print("Database tables created successfully.")
        
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")

if __name__ == '__main__':
    setup_database()