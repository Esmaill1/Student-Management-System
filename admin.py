import sqlite3
from database import get_connection

class AdminManager:
    def __init__(self, auth):
        self.auth = auth
    
    def _check_admin(self):
        """Check if current user is admin"""
        if not self.auth.is_admin():
            return False, "Administrative privileges required"
        return True, ""
    
    # Student Management
    def add_student(self, student_id, full_name, email=None, phone=None):
        """Add a new student to the system"""
        is_admin, msg = self._check_admin()
        if not is_admin:
            return False, msg
        
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            INSERT INTO students (student_id, full_name, email, phone)
            VALUES (?, ?, ?, ?)
            ''', (student_id, full_name, email, phone))
            conn.commit()
            return True, f"Student {student_id} - {full_name} added successfully"
        except sqlite3.IntegrityError:
            return False, f"Student ID {student_id} or email already exists"
        finally:
            conn.close()
    
    def edit_student(self, id, student_id=None, full_name=None, email=None, phone=None):
        """Edit an existing student"""
        is_admin, msg = self._check_admin()
        if not is_admin:
            return False, msg
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Fetch current student data
        cursor.execute('SELECT * FROM students WHERE id = ?', (id,))
        student = cursor.fetchone()
        
        if not student:
            conn.close()
            return False, f"Student with ID {id} not found"
        
        # Update with new values or keep existing ones
        student_id = student_id if student_id is not None else student['student_id']
        full_name = full_name if full_name is not None else student['full_name']
        email = email if email is not None else student['email']
        phone = phone if phone is not None else student['phone']
        
        try:
            cursor.execute('''
            UPDATE students
            SET student_id = ?, full_name = ?, email = ?, phone = ?
            WHERE id = ?
            ''', (student_id, full_name, email, phone, id))
            conn.commit()
            return True, f"Student {student_id} updated successfully"
        except sqlite3.IntegrityError:
            return False, f"Student ID {student_id} or email already exists"
        finally:
            conn.close()
    
    def delete_student(self, id):
        """Delete a student"""
        is_admin, msg = self._check_admin()
        if not is_admin:
            return False, msg
        
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # First check if student has enrollments
            cursor.execute('SELECT COUNT(*) FROM enrollments WHERE student_id = ?', (id,))
            enrollment_count = cursor.fetchone()[0]
            
            if enrollment_count > 0:
                conn.close()
                return False, "Cannot delete student with existing enrollments"
            
            cursor.execute('DELETE FROM students WHERE id = ?', (id,))
            
            if cursor.rowcount == 0:
                conn.close()
                return False, f"Student with ID {id} not found"
            
            conn.commit()
            return True, "Student deleted successfully"
        finally:
            conn.close()
    
    def delete_student_with_records(self, id):
        """Delete a student with all associated records (enrollments and attendance)"""
        is_admin, msg = self._check_admin()
        if not is_admin:
            return False, msg
        
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Check if student exists
            cursor.execute('SELECT * FROM students WHERE id = ?', (id,))
            student = cursor.fetchone()
            
            if not student:
                conn.close()
                return False, f"Student with ID {id} not found"
            
            # Get all enrollment IDs for this student
            cursor.execute('SELECT id FROM enrollments WHERE student_id = ?', (id,))
            enrollment_ids = [row[0] for row in cursor.fetchall()]
            
            # Delete associated attendance records
            if enrollment_ids:
                placeholders = ','.join(['?'] * len(enrollment_ids))
                cursor.execute(f'DELETE FROM attendance WHERE enrollment_id IN ({placeholders})', enrollment_ids)
                attendance_count = cursor.rowcount
            else:
                attendance_count = 0
            
            # Delete enrollments
            cursor.execute('DELETE FROM enrollments WHERE student_id = ?', (id,))
            enrollment_count = cursor.rowcount
            
            # Finally delete the student
            cursor.execute('DELETE FROM students WHERE id = ?', (id,))
            
            conn.commit()
            return True, f"Student deleted successfully along with {enrollment_count} enrollments and {attendance_count} attendance records"
        except Exception as e:
            conn.rollback()
            return False, f"Error deleting student: {str(e)}"
        finally:
            conn.close()
    
    def list_students(self):
        """List all students"""
        is_admin, msg = self._check_admin()
        if not is_admin:
            return False, msg, []
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM students ORDER BY full_name')
        students = [dict(student) for student in cursor.fetchall()]
        conn.close()
        
        return True, f"Found {len(students)} students", students
    
    # Course Management
    def add_course(self, course_code, course_name, instructor_id, description=None):
        """Add a new course"""
        is_admin, msg = self._check_admin()
        if not is_admin:
            return False, msg
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Verify instructor exists
        cursor.execute('SELECT * FROM users WHERE id = ? AND role = "instructor"', (instructor_id,))
        instructor = cursor.fetchone()
        
        if not instructor:
            conn.close()
            return False, f"Instructor with ID {instructor_id} not found"
        
        try:
            cursor.execute('''
            INSERT INTO courses (course_code, course_name, instructor_id, description)
            VALUES (?, ?, ?, ?)
            ''', (course_code, course_name, instructor_id, description))
            conn.commit()
            return True, f"Course {course_code} - {course_name} added successfully"
        except sqlite3.IntegrityError:
            return False, f"Course code {course_code} already exists"
        finally:
            conn.close()
    
    def edit_course(self, id, course_code=None, course_name=None, instructor_id=None, description=None):
        """Edit an existing course"""
        is_admin, msg = self._check_admin()
        if not is_admin:
            return False, msg
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Fetch current course data
        cursor.execute('SELECT * FROM courses WHERE id = ?', (id,))
        course = cursor.fetchone()
        
        if not course:
            conn.close()
            return False, f"Course with ID {id} not found"
        
        # Update with new values or keep existing ones
        course_code = course_code if course_code is not None else course['course_code']
        course_name = course_name if course_name is not None else course['course_name']
        instructor_id = instructor_id if instructor_id is not None else course['instructor_id']
        description = description if description is not None else course['description']
        
        # Verify instructor exists if changing
        if instructor_id != course['instructor_id']:
            cursor.execute('SELECT * FROM users WHERE id = ? AND role = "instructor"', (instructor_id,))
            instructor = cursor.fetchone()
            
            if not instructor:
                conn.close()
                return False, f"Instructor with ID {instructor_id} not found"
        
        try:
            cursor.execute('''
            UPDATE courses
            SET course_code = ?, course_name = ?, instructor_id = ?, description = ?
            WHERE id = ?
            ''', (course_code, course_name, instructor_id, description, id))
            conn.commit()
            return True, f"Course {course_code} updated successfully"
        except sqlite3.IntegrityError:
            return False, f"Course code {course_code} already exists"
        finally:
            conn.close()
    
    def delete_course(self, id):
        """Delete a course"""
        is_admin, msg = self._check_admin()
        if not is_admin:
            return False, msg
        
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # First check if course has enrollments
            cursor.execute('SELECT COUNT(*) FROM enrollments WHERE course_id = ?', (id,))
            enrollment_count = cursor.fetchone()[0]
            
            if enrollment_count > 0:
                conn.close()
                return False, "Cannot delete course with existing enrollments"
            
            cursor.execute('DELETE FROM courses WHERE id = ?', (id,))
            
            if cursor.rowcount == 0:
                conn.close()
                return False, f"Course with ID {id} not found"
            
            conn.commit()
            return True, "Course deleted successfully"
        finally:
            conn.close()
    
    def list_courses(self):
        """List all courses with instructor information"""
        is_admin, msg = self._check_admin()
        if not is_admin and not self.auth.is_instructor():
            return False, "You do not have permission to view courses", []
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Join with users table to get instructor name
        cursor.execute('''
        SELECT c.*, u.full_name as instructor_name
        FROM courses c
        JOIN users u ON c.instructor_id = u.id
        ORDER BY c.course_code
        ''')
        
        courses = [dict(course) for course in cursor.fetchall()]
        conn.close()
        
        return True, f"Found {len(courses)} courses", courses
    
    # Enrollment Management
    def enroll_student(self, student_id, course_id):
        """Enroll a student in a course"""
        is_admin, msg = self._check_admin()
        if not is_admin:
            return False, msg
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Verify student exists
        cursor.execute('SELECT * FROM students WHERE id = ?', (student_id,))
        student = cursor.fetchone()
        
        if not student:
            conn.close()
            return False, f"Student with ID {student_id} not found"
        
        # Verify course exists
        cursor.execute('SELECT * FROM courses WHERE id = ?', (course_id,))
        course = cursor.fetchone()
        
        if not course:
            conn.close()
            return False, f"Course with ID {course_id} not found"
        
        try:
            cursor.execute('''
            INSERT INTO enrollments (student_id, course_id)
            VALUES (?, ?)
            ''', (student_id, course_id))
            conn.commit()
            return True, f"Student {student['full_name']} enrolled in {course['course_name']}"
        except sqlite3.IntegrityError:
            return False, "Student is already enrolled in this course"
        finally:
            conn.close()
    
    def unenroll_student(self, enrollment_id):
        """Remove student from a course"""
        is_admin, msg = self._check_admin()
        if not is_admin:
            return False, msg
        
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Check if there are attendance records
            cursor.execute('SELECT COUNT(*) FROM attendance WHERE enrollment_id = ?', (enrollment_id,))
            attendance_count = cursor.fetchone()[0]
            
            if attendance_count > 0:
                conn.close()
                return False, "Cannot unenroll student with existing attendance records"
            
            # Get enrollment details for confirmation message
            cursor.execute('''
            SELECT s.full_name, c.course_name 
            FROM enrollments e
            JOIN students s ON e.student_id = s.id
            JOIN courses c ON e.course_id = c.id
            WHERE e.id = ?
            ''', (enrollment_id,))
            
            enrollment = cursor.fetchone()
            
            if not enrollment:
                conn.close()
                return False, f"Enrollment with ID {enrollment_id} not found"
            
            cursor.execute('DELETE FROM enrollments WHERE id = ?', (enrollment_id,))
            conn.commit()
            
            return True, f"Student {enrollment['full_name']} unenrolled from {enrollment['course_name']}"
        finally:
            conn.close()
    
    def list_enrollments(self, course_id=None, student_id=None):
        """List enrollments with optional filtering"""
        is_admin, msg = self._check_admin()
        if not is_admin and not self.auth.is_instructor():
            return False, "You do not have permission to view enrollments", []
        
        conn = get_connection()
        cursor = conn.cursor()
        
        query = '''
        SELECT e.id, e.enrollment_date, s.id as student_id, s.student_id as student_code, 
               s.full_name as student_name, c.id as course_id, c.course_code, c.course_name
        FROM enrollments e
        JOIN students s ON e.student_id = s.id
        JOIN courses c ON e.course_id = c.id
        '''
        
        params = []
        
        # Add filters if provided
        if course_id is not None:
            query += " WHERE e.course_id = ?"
            params.append(course_id)
            
            if student_id is not None:
                query += " AND e.student_id = ?"
                params.append(student_id)
        elif student_id is not None:
            query += " WHERE e.student_id = ?"
            params.append(student_id)
        
        # If user is instructor, only show their courses
        if not is_admin and self.auth.is_instructor():
            if "WHERE" in query:
                query += " AND c.instructor_id = ?"
            else:
                query += " WHERE c.instructor_id = ?"
            params.append(self.auth.get_current_user()['id'])
        
        query += " ORDER BY c.course_name, s.full_name"
        
        cursor.execute(query, params)
        enrollments = [dict(enrollment) for enrollment in cursor.fetchall()]
        conn.close()
        
        return True, f"Found {len(enrollments)} enrollments", enrollments 