import sqlite3
import bcrypt
import os
from datetime import datetime

def init_db():
    """Initialize the database with required tables"""
    # Check if database file exists, if not create it
    db_exists = os.path.exists('attendance.db')
    
    # Connect to database
    conn = sqlite3.connect('attendance.db')
    cursor = conn.cursor()
    
    # Create Users table (admin/instructors)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL CHECK (role IN ('admin', 'instructor')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create Students table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        email TEXT UNIQUE,
        phone TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create Courses table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_code TEXT UNIQUE NOT NULL,
        course_name TEXT NOT NULL,
        instructor_id INTEGER NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (instructor_id) REFERENCES users (id)
    )
    ''')
    
    # Create Enrollments table (linking students to courses)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS enrollments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        course_id INTEGER NOT NULL,
        enrollment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students (id),
        FOREIGN KEY (course_id) REFERENCES courses (id),
        UNIQUE(student_id, course_id)
    )
    ''')
    
    # Create Attendance records table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        enrollment_id INTEGER NOT NULL,
        date DATE NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('present', 'absent', 'late', 'excused')),
        notes TEXT,
        recorded_by INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (enrollment_id) REFERENCES enrollments (id),
        FOREIGN KEY (recorded_by) REFERENCES users (id),
        UNIQUE(enrollment_id, date)
    )
    ''')
    
    # Add default admin user if database is being created for the first time
    if not db_exists:
        # Hash default password 'admin123'
        hashed_password = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        cursor.execute('''
        INSERT INTO users (username, password, full_name, role)
        VALUES (?, ?, ?, ?)
        ''', ('admin', hashed_password, 'System Administrator', 'admin'))
    
    conn.commit()
    conn.close()
    
    print("Database initialized successfully.")

def get_connection():
    """Get a connection to the database"""
    conn = sqlite3.connect('attendance.db')
    conn.row_factory = sqlite3.Row  # This enables column access by name
    return conn

if __name__ == "__main__":
    init_db() 