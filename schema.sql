-- Defines the structure for the entire database

-- Table for all participating classes
CREATE TABLE IF NOT EXISTS classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

-- Table for all sports in the event
CREATE TABLE IF NOT EXISTS sports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    -- 1 for sports with scores (Football), 0 for result-only (Chess)
    has_scores INTEGER NOT NULL CHECK(has_scores IN (0, 1))
);

-- Table for all matches
CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sport_id INTEGER NOT NULL,
    class1_id INTEGER NOT NULL,
    class2_id INTEGER NOT NULL,
    -- The ID of the winning class. NULL if match is not completed.
    winner_id INTEGER,
    -- Flexible text field for custom score formats (e.g., "2-1", "150/7", "21-18, 21-19")
    result_details TEXT,
    -- Status of the match
    status TEXT NOT NULL DEFAULT 'UPCOMING' CHECK(status IN ('UPCOMING', 'LIVE', 'COMPLETED')),
    -- Storing datetime as ISO 8601 string ("YYYY-MM-DD HH:MM:SS")
    match_time TEXT NOT NULL,
    notes TEXT,
    FOREIGN KEY (sport_id) REFERENCES sports (id),
    FOREIGN KEY (class1_id) REFERENCES classes (id),
    FOREIGN KEY (class2_id) REFERENCES classes (id),
    FOREIGN KEY (winner_id) REFERENCES classes (id)
);