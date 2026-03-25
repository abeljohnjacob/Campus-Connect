import sqlite3

def create_tables():
    conn = sqlite3.connect("campus_connect.db")
    cursor = conn.cursor()

    # 🔥 VERY IMPORTANT: enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON")

    # ---------------- USERS TABLE ----------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    )
    """)

    # ---------------- STUDENTS TABLE ----------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        student_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        name TEXT,
        contact TEXT,
        register_no TEXT,
        programme TEXT,
        semester TEXT,
        FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
    )
    """)

    # ---------------- FACULTIES TABLE ----------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS faculties (
        faculty_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        name TEXT,
        contact TEXT,
        register_no TEXT,
        department TEXT,
        designation TEXT,
        photo TEXT,
        isHOD TEXT,
        FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
    )
    """)

    # ---------------- VENUES TABLE ----------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS venues (
        venue_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        department TEXT NOT NULL,
        block TEXT NOT NULL,
        photo TEXT,
        purpose TEXT NOT NULL
    )
    """)
    
    #---------------- BOOKINGS TABLE -----------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
        faculty_id INTEGER NOT NULL,
        venue_id INTEGER NOT NULL,
        booking_type TEXT NOT NULL,
        date TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        purpose TEXT,
        target_batch TEXT,
        status TEXT DEFAULT 'requested',

        FOREIGN KEY (faculty_id)
            REFERENCES faculties(faculty_id)
            ON DELETE CASCADE,

        FOREIGN KEY (venue_id)
            REFERENCES venues(venue_id)
            ON DELETE CASCADE
    )
    """)
    
    
    # ---------------- CHATS TABLE ----------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chats (
        message_id INTEGER PRIMARY KEY AUTOINCREMENT,
        faculty_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        sender_role TEXT NOT NULL,
        message TEXT NOT NULL,
        sent_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (faculty_id)
            REFERENCES faculties(faculty_id)
            ON DELETE CASCADE,

        FOREIGN KEY (student_id)
            REFERENCES students(student_id)
            ON DELETE CASCADE
    )
    """)
    
    
    # ---------------- EVENTS TABLE ----------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_title TEXT NOT NULL,
        description TEXT NOT NULL,
        department TEXT NOT NULL,
        organizer TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()