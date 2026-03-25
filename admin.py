import sqlite3

conn = sqlite3.connect("campus_connect.db")
cursor = conn.cursor()

try:
    # Insert into users table only
    cursor.execute("""
        INSERT INTO users (email, password, role)
        VALUES (?, ?, ?)
    """, (
        "admin@saintgits.org",
        "admin123",
        "admin"
    ))

    conn.commit()
    print("Admin created successfully ✅")

except Exception as e:
    print("Error:", e)

conn.close()
