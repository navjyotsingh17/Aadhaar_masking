import sqlite3

# Connect to the SQLite database
conn = sqlite3.connect('masking_audit.db')
cursor = conn.cursor()

# Create the audit details table
cursor.execute('''
CREATE TABLE IF NOT EXISTS audit_details (
    id INTEGER PRIMARY KEY,
    image_name TEXT,
    path TEXT,
    masking_status TEXT,
    aadhar_number TEXT,
    occurrence INTEGER,
    accuracy REAL,
    time_taken REAL
)
''')

# Create the user authentication table
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE,
    password TEXT
)
''')

conn.commit()
conn.close()
