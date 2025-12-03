import sqlite3
from datetime import datetime, date
from database import get_connection

class InstructorManager:
    def __init__(self, auth):
        self.auth = auth
    
    def _check_permissions(self):
        """Check if current user is admin or instructor"""
        if not self.auth.is_authenticated():
            return False, "Authentication required"
        if not (self.auth.is_admin() or self.auth.is_instructor()):
            return False, "Insufficient permissions"
        return True, ""
    
    def get_instructor_courses(self):
        """Get courses taught by the current instructor"""
        ok, msg = self._check_permissions()
        if not ok:
            return False, msg, []
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Admin can see all courses
        if self.auth.is_admin():
            cursor.execute('''
            SELECT c.*, u.full_name as instructor_name
            FROM courses c
            JOIN users u ON c.instructor_id = u.id
            ORDER BY c.course_code
            ''')
        else:
            # Instructor can only see their courses
            cursor.execute('''
            SELECT c.*, u.full_name as instructor_name
            FROM courses c
            JOIN users u ON c.instructor_id = u.id
            WHERE c.instructor_id = ?
            ORDER BY c.course_code
            ''', (self.auth.get_current_user()['id'],))
        
        courses = [dict(course) for course in cursor.fetchall()]
        conn.close()
        
        return True, f"Found {len(courses)} courses", courses
    
    def get_course_students(self, course_id):
        """Get students enrolled in a specific course"""
        ok, msg = self._check_permissions()
        if not ok:
            return False, msg, []
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if user has permission to access this course
        if not self.auth.is_admin():
            cursor.execute('''
            SELECT * FROM courses
            WHERE id = ? AND instructor_id = ?
            ''', (course_id, self.auth.get_current_user()['id']))
            
            if not cursor.fetchone():
                conn.close()
                return False, "You do not have permission to access this course", []
        
        # Get all enrolled students
        cursor.execute('''
        SELECT e.id as enrollment_id, s.id as student_id, s.student_id as student_code,
               s.full_name, s.email, s.phone
        FROM enrollments e
        JOIN students s ON e.student_id = s.id
        WHERE e.course_id = ?
        ORDER BY s.full_name
        ''', (course_id,))
        
        students = [dict(student) for student in cursor.fetchall()]
        conn.close()
        
        return True, f"Found {len(students)} students enrolled", students
    
    def take_attendance(self, enrollment_id, attendance_date, status, notes=None):
        """Record attendance for a student"""
        ok, msg = self._check_permissions()
        if not ok:
            return False, msg
        
        # Validate status
        valid_statuses = ['present', 'absent', 'late', 'excused']
        if status not in valid_statuses:
            return False, f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if enrollment exists and user has permission
        if not self.auth.is_admin():
            cursor.execute('''
            SELECT e.*, c.instructor_id
            FROM enrollments e
            JOIN courses c ON e.course_id = c.id
            WHERE e.id = ?
            ''', (enrollment_id,))
            
            enrollment = cursor.fetchone()
            
            if not enrollment:
                conn.close()
                return False, "Enrollment not found"
                
            if enrollment['instructor_id'] != self.auth.get_current_user()['id']:
                conn.close()
                return False, "You do not have permission to record attendance for this student"
        else:
            # Admin check if enrollment exists
            cursor.execute('SELECT * FROM enrollments WHERE id = ?', (enrollment_id,))
            if not cursor.fetchone():
                conn.close()
                return False, "Enrollment not found"
        
        # Parse date or use today
        if attendance_date is None:
            attendance_date = date.today().isoformat()
        
        try:
            # Try to insert new attendance record
            cursor.execute('''
            INSERT INTO attendance (enrollment_id, date, status, notes, recorded_by)
            VALUES (?, ?, ?, ?, ?)
            ''', (enrollment_id, attendance_date, status, notes, self.auth.get_current_user()['id']))
            conn.commit()
            
            # Get student and course info for confirmation message
            cursor.execute('''
            SELECT s.full_name, c.course_name 
            FROM enrollments e
            JOIN students s ON e.student_id = s.id
            JOIN courses c ON e.course_id = c.id
            WHERE e.id = ?
            ''', (enrollment_id,))
            
            info = cursor.fetchone()
            conn.close()
            
            return True, f"Recorded '{status}' for {info['full_name']} in {info['course_name']} on {attendance_date}"
            
        except sqlite3.IntegrityError:
            # Record already exists, update it
            cursor.execute('''
            UPDATE attendance
            SET status = ?, notes = ?, recorded_by = ?
            WHERE enrollment_id = ? AND date = ?
            ''', (status, notes, self.auth.get_current_user()['id'], enrollment_id, attendance_date))
            conn.commit()
            
            # Get student and course info for confirmation message
            cursor.execute('''
            SELECT s.full_name, c.course_name 
            FROM enrollments e
            JOIN students s ON e.student_id = s.id
            JOIN courses c ON e.course_id = c.id
            WHERE e.id = ?
            ''', (enrollment_id,))
            
            info = cursor.fetchone()
            conn.close()
            
            return True, f"Updated attendance to '{status}' for {info['full_name']} in {info['course_name']} on {attendance_date}"
    
    def take_bulk_attendance(self, course_id, attendance_date, data):
        """Record attendance for multiple students in a course
        
        Args:
            course_id: The course ID
            attendance_date: The date for attendance
            data: List of dictionaries with enrollment_id, status, and optional notes
        """
        ok, msg = self._check_permissions()
        if not ok:
            return False, msg
        
        # Parse date or use today
        if attendance_date is None:
            attendance_date = date.today().isoformat()
        
        # Check if user has permission to access this course
        conn = get_connection()
        cursor = conn.cursor()
        
        if not self.auth.is_admin():
            cursor.execute('''
            SELECT * FROM courses
            WHERE id = ? AND instructor_id = ?
            ''', (course_id, self.auth.get_current_user()['id']))
            
            if not cursor.fetchone():
                conn.close()
                return False, "You do not have permission to access this course"
        
        # Get the course name
        cursor.execute('SELECT course_name FROM courses WHERE id = ?', (course_id,))
        course = cursor.fetchone()
        
        if not course:
            conn.close()
            return False, f"Course with ID {course_id} not found"
        
        # Process each attendance record
        success_count = 0
        error_count = 0
        
        for item in data:
            enrollment_id = item.get('enrollment_id')
            status = item.get('status')
            notes = item.get('notes')
            
            # Basic validation
            if not enrollment_id or not status:
                error_count += 1
                continue
                
            # Validate status
            valid_statuses = ['present', 'absent', 'late', 'excused']
            if status not in valid_statuses:
                error_count += 1
                continue
            
            # Check if enrollment belongs to this course
            cursor.execute('''
            SELECT * FROM enrollments
            WHERE id = ? AND course_id = ?
            ''', (enrollment_id, course_id))
            
            if not cursor.fetchone():
                error_count += 1
                continue
            
            try:
                # Try to insert new attendance record
                cursor.execute('''
                INSERT INTO attendance (enrollment_id, date, status, notes, recorded_by)
                VALUES (?, ?, ?, ?, ?)
                ''', (enrollment_id, attendance_date, status, notes, self.auth.get_current_user()['id']))
                success_count += 1
                
            except sqlite3.IntegrityError:
                # Record already exists, update it
                cursor.execute('''
                UPDATE attendance
                SET status = ?, notes = ?, recorded_by = ?
                WHERE enrollment_id = ? AND date = ?
                ''', (status, notes, self.auth.get_current_user()['id'], enrollment_id, attendance_date))
                success_count += 1
        
        conn.commit()
        conn.close()
        
        return True, f"Recorded attendance for {course['course_name']} on {attendance_date}: {success_count} successful, {error_count} failed"
    
    def get_attendance_records(self, course_id, start_date=None, end_date=None):
        """Get attendance records for a course within a date range"""
        ok, msg = self._check_permissions()
        if not ok:
            return False, msg, []
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if user has permission to access this course
        if not self.auth.is_admin():
            cursor.execute('''
            SELECT * FROM courses
            WHERE id = ? AND instructor_id = ?
            ''', (course_id, self.auth.get_current_user()['id']))
            
            if not cursor.fetchone():
                conn.close()
                return False, "You do not have permission to access this course", []
        
        # Build query based on date range
        query = '''
        SELECT a.id, a.date, a.status, a.notes, 
               s.student_id as student_code, s.full_name as student_name,
               e.id as enrollment_id, u.full_name as recorded_by_name
        FROM attendance a
        JOIN enrollments e ON a.enrollment_id = e.id
        JOIN students s ON e.student_id = s.id
        JOIN users u ON a.recorded_by = u.id
        WHERE e.course_id = ?
        '''
        
        params = [course_id]
        
        if start_date:
            query += " AND a.date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND a.date <= ?"
            params.append(end_date)
        
        query += " ORDER BY a.date DESC, s.full_name"
        
        cursor.execute(query, params)
        records = [dict(record) for record in cursor.fetchall()]
        
        # Get course name
        cursor.execute('SELECT course_name FROM courses WHERE id = ?', (course_id,))
        course = cursor.fetchone()
        
        conn.close()
        
        return True, f"Found {len(records)} attendance records for {course['course_name']}", records
    
    def get_student_attendance(self, enrollment_id):
        """Get all attendance records for a specific student in a course"""
        ok, msg = self._check_permissions()
        if not ok:
            return False, msg, []
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if user has permission to access this enrollment
        if not self.auth.is_admin():
            cursor.execute('''
            SELECT e.*, c.instructor_id, c.course_name, s.full_name as student_name
            FROM enrollments e
            JOIN courses c ON e.course_id = c.id
            JOIN students s ON e.student_id = s.id
            WHERE e.id = ?
            ''', (enrollment_id,))
            
            enrollment = cursor.fetchone()
            
            if not enrollment:
                conn.close()
                return False, "Enrollment not found", []
                
            if enrollment['instructor_id'] != self.auth.get_current_user()['id']:
                conn.close()
                return False, "You do not have permission to view attendance for this student", []
        else:
            # Admin - get enrollment info
            cursor.execute('''
            SELECT e.*, c.course_name, s.full_name as student_name
            FROM enrollments e
            JOIN courses c ON e.course_id = c.id
            JOIN students s ON e.student_id = s.id
            WHERE e.id = ?
            ''', (enrollment_id,))
            
            enrollment = cursor.fetchone()
            
            if not enrollment:
                conn.close()
                return False, "Enrollment not found", []
        
        # Get all attendance records
        cursor.execute('''
        SELECT a.*, u.full_name as recorded_by_name
        FROM attendance a
        JOIN users u ON a.recorded_by = u.id
        WHERE a.enrollment_id = ?
        ORDER BY a.date DESC
        ''', (enrollment_id,))
        
        records = [dict(record) for record in cursor.fetchall()]
        conn.close()
        
        # Calculate statistics
        total = len(records)
        present = sum(1 for r in records if r['status'] == 'present')
        absent = sum(1 for r in records if r['status'] == 'absent')
        late = sum(1 for r in records if r['status'] == 'late')
        excused = sum(1 for r in records if r['status'] == 'excused')
        
        attendance_rate = (present + late) / total * 100 if total > 0 else 0
        
        stats = {
            'total': total,
            'present': present,
            'absent': absent,
            'late': late,
            'excused': excused,
            'attendance_rate': round(attendance_rate, 2)
        }
        
        return True, f"Attendance records for {enrollment['student_name']} in {enrollment['course_name']}", {
            'records': records,
            'stats': stats,
            'student_name': enrollment['student_name'],
            'course_name': enrollment['course_name']
        } 