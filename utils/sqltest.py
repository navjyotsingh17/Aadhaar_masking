import sqlite3
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import random


def alter_table():
    # Check if the new columns already exist, if not, add them
    conn = sqlite3.connect('masking_audit.db')
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(audit_details)")
    existing_columns = [column[1] for column in cursor.fetchall()]
    
    new_columns = {
       "unmasked_image_path":"TEXT NOT NULL"

    }
    
    for column, column_type in new_columns.items():
        if column not in existing_columns:
            cursor.execute(f"ALTER TABLE audit_details ADD COLUMN {column} {column_type}")
    
    conn.commit()
    conn.close()

def create_table():
    conn = sqlite3.connect('masking_audit.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS audit_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        image_name TEXT NOT NULL,
        path TEXT NOT NULL,
        masking_status TEXT NOT NULL,
        aadhar_number TEXT,
        occurrence INTEGER,
        accuracy REAL,
        time_taken REAL,
        create_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        unmasked_image_path TEXT NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        last_logged_in TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()

def update_create_date_for_1000_rows_where_not_null():
    conn = sqlite3.connect('masking_audit.db')
    cursor = conn.cursor()
    
    # Specific datetime value
    sample_date = '2023-07-12 12:00:00'
    
    # Update the create_date column for the first 1000 rows where create_date is not null
    cursor.execute('''
    UPDATE audit_details
    SET create_date = ?
    WHERE ROWID IN (
        SELECT ROWID FROM audit_details 
        WHERE create_date IS NULL 
        LIMIT 1000
    )
    ''', (sample_date,))
    
    conn.commit()
    conn.close()


def log_audit_details(image_name, path, masking_status, aadhar_number, occurrence, accuracy, time_taken):
    conn = sqlite3.connect('masking_audit.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO audit_details (image_name, path, masking_status, aadhar_number, occurrence, accuracy, time_taken)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (image_name, path, masking_status, aadhar_number, occurrence, accuracy, time_taken))
    
    conn.commit()
    conn.close()

def drop_table(table_name):
    conn = sqlite3.connect('masking_audit.db')
    cursor = conn.cursor()
    
    cursor.execute(f'DROP TABLE IF EXISTS {table_name}')
    
    conn.commit()
    conn.close()

# Function to drop audit_details table
def drop_audit_details_table():
    drop_table('audit_details')

# Function to drop users table
def drop_users_table():
    drop_table('users')


# Add a user
def add_user(username, password):
    hashed_password = generate_password_hash(password)
    conn = sqlite3.connect('masking_audit.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
    conn.commit()
    conn.close()  

def delete():
    conn = sqlite3.connect('masking_audit.db')
    cursor = conn.cursor()
    cursor.execute('delete from users')
    conn.commit()
    conn.close()  

def deleterecord():
    
    conn = sqlite3.connect('masking_audit.db')
    cursor = conn.cursor()
    cursor.execute('delete from audit_details')
    conn.commit()
    conn.close()      

def get_all_audit_records():
    conn = sqlite3.connect('masking_audit.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM audit_details')
    rows = cursor.fetchall()
    
    conn.close()
    return rows

def get_all_users():
    conn = sqlite3.connect('masking_audit.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users')
    rows = cursor.fetchall()
    
    conn.close()
    return rows


def insert_dummy_audit_data(num_entries=150):
    try:
        # Connect to SQLite database
        conn = sqlite3.connect('masking_audit.db')
        cursor = conn.cursor()

        # Dummy data for insertion
        dummy_data = []
        for _ in range(num_entries):
            image_name = f'image{_ + 1}.jpg'
            path = f'/path/to/image{_ + 1}.jpg'
            masking_status = random.choice(['masked', 'unmasked'])
            aadhar_number = str(random.randint(100000000000, 999999999999)) if random.random() < 0.5 else None
            occurrence = random.randint(1, 4)
            accuracy = round(random.uniform(70.0, 100.0), 2)
            time_taken = round(random.uniform(1.0, 5.0), 2)
            create_date = datetime.now() - timedelta(days=random.randint(0, 1000))  # Random date within the last 1000 days

            dummy_data.append((image_name, path, masking_status, aadhar_number, occurrence, accuracy, time_taken, create_date))

        # Insert dummy data into audit_details table
        for data in dummy_data:
            image_name, path, masking_status, aadhar_number, occurrence, accuracy, time_taken, create_date = data
            cursor.execute('''
                INSERT INTO audit_details (image_name, path, masking_status, aadhar_number, occurrence, accuracy, time_taken, create_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (image_name, path, masking_status, aadhar_number, occurrence, accuracy, time_taken, create_date))

        # Commit changes
        conn.commit()
        print(f"{num_entries} dummy data entries inserted successfully.")
    
    except sqlite3.Error as e:
        print(f"Error inserting dummy data: {e}")
    
    finally:
        # Close connection
        if conn:
            conn.close()

# Example usage: Insert 150 dummy entries



# Create table
#create_table()
# alter_table()
# update_create_date_for_1000_rows_where_not_null()
#log_audit_details('example_image.jpg', '/path/to/example_image.jpg', 'masked', '123456789012', 1, 95.5, 2.3)
#add_user("admin","passw0rd")
# drop_audit_details_table()
#drop_users_table()
#create_table()
#insert_dummy_audit_data(num_entries=150)
#get_all_audit_records()
# deleterecord();

deleterecord()
# add_user("navjyot","admin")
# print(get_all_users())
# Get all audit records
# userRecords=get_all_users()
# for record in userRecords:
#     print(record)

# records = get_all_audit_records()
# for record in records:
#     print(record)



