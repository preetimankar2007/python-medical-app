import sqlite3
import hashlib
import os
import re
from datetime import datetime, timedelta
import jwt

# Secret key for JWT tokens
SECRET_KEY = os.urandom(32)

def init_db():
    """Initialize the database with all required tables"""
    conn = sqlite3.connect('app.db')
    c = conn.cursor()
    
    # Check if user_type column exists in users table
    c.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in c.fetchall()]
    
    # If users table doesn't exist or needs to be updated
    if 'user_type' not in columns:
        # Create temporary table with new schema
        c.execute('''
            CREATE TABLE IF NOT EXISTS users_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                user_type TEXT DEFAULT 'doctor',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')
        
        # Copy data from old table if it exists
        try:
            c.execute('''
                INSERT INTO users_new (id, username, password, email, created_at, last_login)
                SELECT id, username, password, email, created_at, last_login FROM users
            ''')
            # Drop old table
            c.execute('DROP TABLE users')
            # Rename new table to users
            c.execute('ALTER TABLE users_new RENAME TO users')
        except sqlite3.OperationalError:
            # If old table doesn't exist, just rename the new table
            c.execute('ALTER TABLE users_new RENAME TO users')
    else:
        # Create users table if it doesn't exist
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                user_type TEXT DEFAULT 'doctor',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')
    
    # Create medical_representatives table
    c.execute('''
        CREATE TABLE IF NOT EXISTS medical_representatives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            territory TEXT NOT NULL,
            company TEXT NOT NULL,
            specialization TEXT,
            target_doctors INTEGER DEFAULT 0,
            current_doctors INTEGER DEFAULT 0,
            monthly_visits INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create mr_doctor_assignments table
    c.execute('''
        CREATE TABLE IF NOT EXISTS mr_doctor_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mr_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            assignment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active',
            last_visit_date TIMESTAMP,
            notes TEXT,
            FOREIGN KEY (mr_id) REFERENCES medical_representatives (id),
            FOREIGN KEY (doctor_id) REFERENCES users (id)
        )
    ''')
    
    # Create mr_visits table
    c.execute('''
        CREATE TABLE IF NOT EXISTS mr_visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mr_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            visit_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            visit_purpose TEXT,
            discussion_points TEXT,
            feedback TEXT,
            next_visit_date TIMESTAMP,
            status TEXT DEFAULT 'completed',
            FOREIGN KEY (mr_id) REFERENCES medical_representatives (id),
            FOREIGN KEY (doctor_id) REFERENCES users (id)
        )
    ''')
    
    # Create discount_codes table
    c.execute('''
        CREATE TABLE IF NOT EXISTS discount_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            doctor_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expiry_date TIMESTAMP,
            times_used INTEGER DEFAULT 0,
            max_uses INTEGER DEFAULT 100,
            discount_percentage INTEGER DEFAULT 20,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (doctor_id) REFERENCES users (id)
        )
    ''')
    
    # Update any existing users without user_type to have 'doctor' as default
    c.execute('''
        UPDATE users 
        SET user_type = 'doctor' 
        WHERE user_type IS NULL
    ''')
    
    conn.commit()
    conn.close()

def hash_password(password):
    """Hash password using SHA-256 with salt"""
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000
    )
    return salt + key

def verify_password(stored_password, provided_password):
    """Verify the provided password against stored hash"""
    salt = stored_password[:32]
    stored_key = stored_password[32:]
    key = hashlib.pbkdf2_hmac(
        'sha256',
        provided_password.encode('utf-8'),
        salt,
        100000
    )
    return key == stored_key

def is_valid_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_valid_password(password):
    """
    Validate password strength:
    - At least 8 characters
    - Contains uppercase and lowercase letters
    - Contains numbers
    - Contains special characters
    """
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'[0-9]', password):
        return False
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False
    return True

def register_user(username, password, email):
    """Register a new user"""
    try:
        # Validate input
        if not username or not password or not email:
            return False, "All fields are required"
        
        if not is_valid_email(email):
            return False, "Invalid email format"
        
        if not is_valid_password(password):
            return False, "Password must be at least 8 characters and contain uppercase, lowercase, numbers, and special characters"
        
        # Hash password
        hashed_password = hash_password(password)
        
        # Store in database
        conn = sqlite3.connect('app.db')
        c = conn.cursor()
        c.execute('INSERT INTO users (username, password, email) VALUES (?, ?, ?)',
                 (username, hashed_password, email))
        conn.commit()
        conn.close()
        
        return True, "Registration successful"
    except sqlite3.IntegrityError:
        return False, "Username or email already exists"
    except Exception as e:
        return False, f"Registration failed: {str(e)}"

def login_user(username, password):
    """Login user and return JWT token if successful"""
    try:
        conn = sqlite3.connect('app.db')
        c = conn.cursor()
        c.execute('SELECT id, password, user_type FROM users WHERE username = ?', (username,))
        user = c.fetchone()
        
        if user and verify_password(user[1], password):
            # Update last login
            c.execute('UPDATE users SET last_login = ? WHERE id = ?',
                     (datetime.now(), user[0]))
            conn.commit()
            
            # Generate JWT token
            token = jwt.encode({
                'user_id': user[0],
                'username': username,
                'user_type': user[2],
                'exp': datetime.utcnow() + timedelta(hours=24)
            }, SECRET_KEY, algorithm='HS256')
            
            return True, token, user[0], user[2]  # Return user_id and user_type
        else:
            return False, "Invalid username or password", None, None
    except Exception as e:
        return False, f"Login failed: {str(e)}", None, None
    finally:
        conn.close()

def verify_token(token):
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return True, payload
    except jwt.ExpiredSignatureError:
        return False, "Token has expired"
    except jwt.InvalidTokenError:
        return False, "Invalid token"

def create_discount_code(doctor_id, code, expiry_days=30, max_uses=100, discount_percentage=20):
    """Create a new discount code for a doctor"""
    conn = sqlite3.connect('app.db')
    c = conn.cursor()
    
    try:
        expiry_date = datetime.now() + timedelta(days=expiry_days)
        c.execute('''
            INSERT INTO discount_codes 
            (code, doctor_id, expiry_date, max_uses, discount_percentage)
            VALUES (?, ?, ?, ?, ?)
        ''', (code, doctor_id, expiry_date, max_uses, discount_percentage))
        conn.commit()
        return True, "Discount code created successfully"
    except sqlite3.IntegrityError:
        return False, "Discount code already exists"
    finally:
        conn.close()

def validate_discount_code(code):
    """Validate a discount code and return discount percentage if valid"""
    conn = sqlite3.connect('app.db')
    c = conn.cursor()
    
    try:
        c.execute('''
            SELECT discount_percentage, times_used, max_uses, expiry_date, is_active
            FROM discount_codes
            WHERE code = ?
        ''', (code,))
        
        result = c.fetchone()
        
        if not result:
            return False, "Invalid discount code"
            
        discount_percentage, times_used, max_uses, expiry_date, is_active = result
        
        if not is_active:
            return False, "This discount code is no longer active"
            
        if times_used >= max_uses:
            return False, "This discount code has reached its maximum usage limit"
            
        expiry = datetime.strptime(expiry_date, '%Y-%m-%d %H:%M:%S.%f')
        if expiry < datetime.now():
            return False, "This discount code has expired"
            
        # Update usage count
        c.execute('''
            UPDATE discount_codes
            SET times_used = times_used + 1
            WHERE code = ?
        ''', (code,))
        
        conn.commit()
        return True, f"{discount_percentage}% discount applied successfully!"
        
    finally:
        conn.close()

def register_mr(username, password, email, full_name, phone, territory, company, specialization):
    """Register a new Medical Representative"""
    conn = None
    try:
        if not all([username, password, email, full_name, phone, territory, company]):
            return False, "All required fields must be filled"
        
        if not is_valid_email(email):
            return False, "Invalid email format"
        
        if not is_valid_password(password):
            return False, "Password must be at least 8 characters and contain uppercase, lowercase, numbers, and special characters"
        
        conn = sqlite3.connect('app.db')
        c = conn.cursor()
        
        # First create user account
        hashed_password = hash_password(password)
        c.execute('''
            INSERT INTO users (username, password, email, user_type)
            VALUES (?, ?, ?, 'mr')
        ''', (username, hashed_password, email))
        
        user_id = c.lastrowid
        
        # Then create MR profile
        c.execute('''
            INSERT INTO medical_representatives 
            (user_id, full_name, phone, territory, company, specialization)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, full_name, phone, territory, company, specialization))
        
        conn.commit()
        return True, "Medical Representative registered successfully"
    
    except sqlite3.IntegrityError:
        if conn:
            conn.rollback()
        return False, "Username or email already exists"
    except Exception as e:
        if conn:
            conn.rollback()
        return False, f"Registration failed: {str(e)}"
    finally:
        if conn:
            conn.close()

def get_mr_details(user_id):
    """Get Medical Representative details"""
    conn = sqlite3.connect('app.db')
    c = conn.cursor()
    try:
        c.execute('''
            SELECT mr.*, u.email, u.username
            FROM medical_representatives mr
            JOIN users u ON mr.user_id = u.id
            WHERE u.id = ?
        ''', (user_id,))
        return c.fetchone()
    finally:
        conn.close()

def update_mr_profile(user_id, full_name, phone, territory, company, specialization):
    """Update Medical Representative profile"""
    conn = sqlite3.connect('app.db')
    c = conn.cursor()
    try:
        c.execute('''
            UPDATE medical_representatives
            SET full_name = ?, phone = ?, territory = ?, 
                company = ?, specialization = ?, last_updated = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (full_name, phone, territory, company, specialization, user_id))
        conn.commit()
        return True, "Profile updated successfully"
    except Exception as e:
        return False, f"Update failed: {str(e)}"
    finally:
        conn.close()

def record_doctor_visit(mr_id, doctor_id, visit_purpose, discussion_points, feedback, next_visit_date):
    """Record a doctor visit by MR"""
    conn = sqlite3.connect('app.db')
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO mr_visits 
            (mr_id, doctor_id, visit_purpose, discussion_points, feedback, next_visit_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (mr_id, doctor_id, visit_purpose, discussion_points, feedback, next_visit_date))
        
        # Update last visit date in assignments
        c.execute('''
            UPDATE mr_doctor_assignments
            SET last_visit_date = CURRENT_TIMESTAMP
            WHERE mr_id = ? AND doctor_id = ?
        ''', (mr_id, doctor_id))
        
        conn.commit()
        return True, "Visit recorded successfully"
    except Exception as e:
        return False, f"Failed to record visit: {str(e)}"
    finally:
        conn.close()

def get_mr_statistics(mr_id):
    """Get MR performance statistics"""
    conn = sqlite3.connect('app.db')
    c = conn.cursor()
    try:
        # Get total assigned doctors
        c.execute('''
            SELECT COUNT(*) 
            FROM mr_doctor_assignments 
            WHERE mr_id = ? AND status = 'active'
        ''', (mr_id,))
        total_doctors = c.fetchone()[0]
        
        # Get total visits this month
        c.execute('''
            SELECT COUNT(*) 
            FROM mr_visits 
            WHERE mr_id = ? 
            AND strftime('%Y-%m', visit_date) = strftime('%Y-%m', 'now')
        ''', (mr_id,))
        monthly_visits = c.fetchone()[0]
        
        return {
            'total_doctors': total_doctors,
            'monthly_visits': monthly_visits
        }
    finally:
        conn.close() 