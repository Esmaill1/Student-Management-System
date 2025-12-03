import bcrypt
import sqlite3
from database import get_connection

class Auth:
    def __init__(self):
        self.current_user = None
    
    def login(self, username, password):
        """Authenticate a user by username and password"""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            # Create user object without password
            self.current_user = {
                'id': user['id'],
                'username': user['username'],
                'full_name': user['full_name'],
                'role': user['role']
            }
            return True
        return False
    
    def logout(self):
        """Log out the current user"""
        self.current_user = None
    
    def is_authenticated(self):
        """Check if a user is authenticated"""
        return self.current_user is not None
    
    def is_admin(self):
        """Check if the current user is an admin"""
        return self.is_authenticated() and self.current_user['role'] == 'admin'
    
    def is_instructor(self):
        """Check if the current user is an instructor"""
        return self.is_authenticated() and self.current_user['role'] == 'instructor'
    
    def get_current_user(self):
        """Get the current user"""
        return self.current_user
    
    def register_user(self, username, password, full_name, role):
        """Register a new user (admin only function)"""
        if not self.is_admin():
            return False, "Only administrators can register new users"
        
        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            INSERT INTO users (username, password, full_name, role)
            VALUES (?, ?, ?, ?)
            ''', (username, hashed_password, full_name, role))
            conn.commit()
            return True, f"User {username} successfully created"
        except sqlite3.IntegrityError:
            return False, f"Username {username} already exists"
        finally:
            conn.close()
    
    def delete_user(self, user_id):
        """Delete a user (admin only function)"""
        if not self.is_admin():
            return False, "Only administrators can delete users"
            
        # Don't allow deleting yourself
        if self.current_user['id'] == user_id:
            return False, "You cannot delete your own account"
        
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Check if user exists
            cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            user = cursor.fetchone()
            
            if not user:
                conn.close()
                return False, f"User with ID {user_id} not found"
                
            # Check if user is an instructor with courses
            if user['role'] == 'instructor':
                cursor.execute('SELECT COUNT(*) FROM courses WHERE instructor_id = ?', (user_id,))
                course_count = cursor.fetchone()[0]
                
                if course_count > 0:
                    conn.close()
                    return False, "Cannot delete instructor with assigned courses"
            
            # Delete the user
            cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
            conn.commit()
            return True, "User deleted successfully"
        except Exception as e:
            return False, f"Error deleting user: {str(e)}"
        finally:
            conn.close()
    
    def change_password(self, old_password, new_password):
        """Change the password for the current user"""
        if not self.is_authenticated():
            return False, "You must be logged in to change your password"
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Verify old password
        cursor.execute('SELECT password FROM users WHERE id = ?', (self.current_user['id'],))
        user = cursor.fetchone()
        
        if not bcrypt.checkpw(old_password.encode('utf-8'), user['password'].encode('utf-8')):
            conn.close()
            return False, "Current password is incorrect"
        
        # Update with new password
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute('UPDATE users SET password = ? WHERE id = ?', 
                      (hashed_password, self.current_user['id']))
        conn.commit()
        conn.close()
        
        return True, "Password successfully updated" 