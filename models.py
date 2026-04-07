import sqlite3
import os
from werkzeug.security import generate_password_hash

def get_db_connection():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'teacher', 'student')),
            security_pin TEXT NOT NULL
        )
    ''')
    
    # Exams table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            teacher_id INTEGER NOT NULL,
            duration INTEGER NOT NULL, -- duration in minutes
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (teacher_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    
    # Questions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_id INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct_option TEXT NOT NULL CHECK(correct_option IN ('A', 'B', 'C', 'D')),
            FOREIGN KEY (exam_id) REFERENCES exams (id) ON DELETE CASCADE
        )
    ''')
    
    # Results table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            exam_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            total INTEGER NOT NULL,
            date_taken TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (exam_id) REFERENCES exams (id) ON DELETE CASCADE
        )
    ''')
    
    # Dummy data
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        # Create dummy users for testing
        hashed_pw = generate_password_hash("password123")
        cursor.execute("INSERT INTO users (name, email, password, role, security_pin) VALUES (?, ?, ?, ?, ?)",
                       ("Admin User", "admin@exam.com", hashed_pw, "admin", "1234"))
        cursor.execute("INSERT INTO users (name, email, password, role, security_pin) VALUES (?, ?, ?, ?, ?)",
                       ("Teacher User", "teacher@exam.com", hashed_pw, "teacher", "1234"))
        cursor.execute("INSERT INTO users (name, email, password, role, security_pin) VALUES (?, ?, ?, ?, ?)",
                       ("Student User", "student@exam.com", hashed_pw, "student", "1234"))

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database SQLite schema initialized successfully.")
