import sqlite3
from datetime import datetime, date, timedelta
from database import get_connection
from tabulate import tabulate

class ReportManager:
    def __init__(self, auth):
        self.auth = auth
    
    def _check_permissions(self):
        """Check if current user is authenticated"""
        if not self.auth.is_authenticated():
            return False, "Authentication required"
        return True, ""
    
    def course_attendance_summary(self, course_id, start_date=None, end_date=None):
        """Generate a summary report of attendance for a course"""
        ok, msg = self._check_permissions()
        if not ok:
            return False, msg, None
        
        # Check if user has access to this course
        if not self.auth.is_admin():
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('''
            SELECT * FROM courses
            WHERE id = ? AND instructor_id = ?
            ''', (course_id, self.auth.get_current_user()['id']))
            
            if not cursor.fetchone():
                conn.close()
                return False, "You do not have permission to access this course", None
            conn.close()
        
        # Set default date range if not provided (last 30 days)
        if end_date is None:
            end_date = date.today().isoformat()
        
        if start_date is None:
            start_date = (date.today() - timedelta(days=30)).isoformat()
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get course details
        cursor.execute('''
        SELECT c.*, u.full_name as instructor_name
        FROM courses c
        JOIN users u ON c.instructor_id = u.id
        WHERE c.id = ?
        ''', (course_id,))
        
        course = dict(cursor.fetchone() or {})
        
        if not course:
            conn.close()
            return False, f"Course with ID {course_id} not found", None
        
        # Get all students enrolled in the course
        cursor.execute('''
        SELECT e.id as enrollment_id, s.id as student_id, s.student_id as student_code, 
               s.full_name as student_name
        FROM enrollments e
        JOIN students s ON e.student_id = s.id
        WHERE e.course_id = ?
        ORDER BY s.full_name
        ''', (course_id,))
        
        students = [dict(student) for student in cursor.fetchall()]
        
        if not students:
            conn.close()
            return False, f"No students enrolled in {course['course_name']}", None
        
        # Get all attendance records in the date range
        cursor.execute('''
        SELECT a.enrollment_id, a.date, a.status
        FROM attendance a
        JOIN enrollments e ON a.enrollment_id = e.id
        WHERE e.course_id = ? AND a.date BETWEEN ? AND ?
        ORDER BY a.date
        ''', (course_id, start_date, end_date))
        
        all_records = [dict(record) for record in cursor.fetchall()]
        
        # Get unique dates in the range that have attendance records
        cursor.execute('''
        SELECT DISTINCT a.date
        FROM attendance a
        JOIN enrollments e ON a.enrollment_id = e.id
        WHERE e.course_id = ? AND a.date BETWEEN ? AND ?
        ORDER BY a.date
        ''', (course_id, start_date, end_date))
        
        dates = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        # Build student attendance summaries
        student_summaries = []
        
        for student in students:
            student_records = [r for r in all_records if r['enrollment_id'] == student['enrollment_id']]
            
            # Count different status types
            total = len(student_records)
            present = sum(1 for r in student_records if r['status'] == 'present')
            absent = sum(1 for r in student_records if r['status'] == 'absent')
            late = sum(1 for r in student_records if r['status'] == 'late')
            excused = sum(1 for r in student_records if r['status'] == 'excused')
            
            # Calculate attendance rate
            if total > 0:
                attendance_rate = round((present + late) / total * 100, 2)
            else:
                attendance_rate = 0
            
            student_summaries.append({
                'student_id': student['student_id'],
                'student_code': student['student_code'],
                'student_name': student['student_name'],
                'enrollment_id': student['enrollment_id'],
                'total_classes': total,
                'present': present,
                'absent': absent,
                'late': late,
                'excused': excused,
                'attendance_rate': attendance_rate
            })
        
        # Calculate overall course statistics
        total_possible_records = len(students) * len(dates)
        total_records = len(all_records)
        total_present = sum(1 for r in all_records if r['status'] == 'present')
        total_absent = sum(1 for r in all_records if r['status'] == 'absent')
        total_late = sum(1 for r in all_records if r['status'] == 'late')
        total_excused = sum(1 for r in all_records if r['status'] == 'excused')
        
        if total_records > 0:
            overall_attendance_rate = round((total_present + total_late) / total_records * 100, 2)
        else:
            overall_attendance_rate = 0
        
        if total_possible_records > 0:
            records_completion_rate = round(total_records / total_possible_records * 100, 2)
        else:
            records_completion_rate = 0
        
        course_summary = {
            'course_id': course['id'],
            'course_code': course['course_code'],
            'course_name': course['course_name'],
            'instructor_name': course['instructor_name'],
            'start_date': start_date,
            'end_date': end_date,
            'total_students': len(students),
            'total_dates': len(dates),
            'dates': dates,
            'total_possible_records': total_possible_records,
            'total_records': total_records,
            'total_present': total_present,
            'total_absent': total_absent,
            'total_late': total_late, 
            'total_excused': total_excused,
            'overall_attendance_rate': overall_attendance_rate,
            'records_completion_rate': records_completion_rate
        }
        
        report = {
            'course_summary': course_summary,
            'student_summaries': student_summaries
        }
        
        return True, f"Generated attendance report for {course['course_name']}", report
    
    def student_attendance_report(self, student_id):
        """Generate a report of a student's attendance across all courses"""
        ok, msg = self._check_permissions()
        if not ok:
            return False, msg, None
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get student details
        cursor.execute('SELECT * FROM students WHERE id = ?', (student_id,))
        student = cursor.fetchone()
        
        if not student:
            conn.close()
            return False, f"Student with ID {student_id} not found", None
        
        student = dict(student)
        
        # Get all enrollments for the student
        query = '''
        SELECT e.id as enrollment_id, c.id as course_id, c.course_code, c.course_name,
               u.full_name as instructor_name
        FROM enrollments e
        JOIN courses c ON e.course_id = c.id
        JOIN users u ON c.instructor_id = u.id
        WHERE e.student_id = ?
        '''
        
        # If instructor, only show courses taught by them
        if not self.auth.is_admin():
            query += " AND c.instructor_id = ?"
            cursor.execute(query, (student_id, self.auth.get_current_user()['id']))
        else:
            cursor.execute(query, (student_id,))
        
        enrollments = [dict(enrollment) for enrollment in cursor.fetchall()]
        
        if not enrollments:
            conn.close()
            if self.auth.is_admin():
                return False, f"Student {student['full_name']} is not enrolled in any courses", None
            else:
                return False, f"Student {student['full_name']} is not enrolled in any of your courses", None
        
        # Get attendance for each enrollment
        for enrollment in enrollments:
            cursor.execute('''
            SELECT status, COUNT(*) as count
            FROM attendance
            WHERE enrollment_id = ?
            GROUP BY status
            ''', (enrollment['enrollment_id'],))
            
            stats = {row['status']: row['count'] for row in cursor.fetchall()}
            
            # Get total records
            total = sum(stats.values())
            
            # Set defaults for missing statuses
            present = stats.get('present', 0)
            absent = stats.get('absent', 0)
            late = stats.get('late', 0)
            excused = stats.get('excused', 0)
            
            # Calculate attendance rate
            if total > 0:
                attendance_rate = round((present + late) / total * 100, 2)
            else:
                attendance_rate = 0
            
            # Add stats to enrollment
            enrollment.update({
                'total_classes': total,
                'present': present,
                'absent': absent,
                'late': late,
                'excused': excused,
                'attendance_rate': attendance_rate
            })
            
            # Get most recent attendance date
            cursor.execute('''
            SELECT MAX(date) as last_date
            FROM attendance
            WHERE enrollment_id = ?
            ''', (enrollment['enrollment_id'],))
            
            last_date = cursor.fetchone()[0]
            enrollment['last_attendance_date'] = last_date
        
        conn.close()
        
        # Calculate overall statistics
        total_classes = sum(e['total_classes'] for e in enrollments)
        total_present = sum(e['present'] for e in enrollments)
        total_absent = sum(e['absent'] for e in enrollments)
        total_late = sum(e['late'] for e in enrollments)
        total_excused = sum(e['excused'] for e in enrollments)
        
        if total_classes > 0:
            overall_attendance_rate = round((total_present + total_late) / total_classes * 100, 2)
        else:
            overall_attendance_rate = 0
        
        overall_stats = {
            'total_courses': len(enrollments),
            'total_classes': total_classes,
            'present': total_present,
            'absent': total_absent,
            'late': total_late,
            'excused': total_excused,
            'overall_attendance_rate': overall_attendance_rate
        }
        
        report = {
            'student': student,
            'overall_stats': overall_stats,
            'course_details': enrollments
        }
        
        return True, f"Generated attendance report for {student['full_name']}", report
    
    def generate_csv_report(self, report_data, report_type):
        """Generate a CSV string from report data"""
        if report_type == 'course':
            # Course report CSV format
            csv_lines = ['Student ID,Student Name,Total Classes,Present,Absent,Late,Excused,Attendance Rate']
            
            for student in report_data['student_summaries']:
                csv_lines.append(f"{student['student_code']},{student['student_name']},{student['total_classes']},"
                                f"{student['present']},{student['absent']},{student['late']},"
                                f"{student['excused']},{student['attendance_rate']}%")
            
            # Add summary line
            summary = report_data['course_summary']
            csv_lines.append('')
            csv_lines.append(f"Course: {summary['course_code']} - {summary['course_name']}")
            csv_lines.append(f"Date Range: {summary['start_date']} to {summary['end_date']}")
            csv_lines.append(f"Overall Attendance Rate: {summary['overall_attendance_rate']}%")
            
            return '\n'.join(csv_lines)
            
        elif report_type == 'student':
            # Student report CSV format
            student = report_data['student']
            csv_lines = [f"Student Report: {student['student_id']} - {student['full_name']}"]
            csv_lines.append('')
            csv_lines.append('Course Code,Course Name,Total Classes,Present,Absent,Late,Excused,Attendance Rate')
            
            for course in report_data['course_details']:
                csv_lines.append(f"{course['course_code']},{course['course_name']},{course['total_classes']},"
                                f"{course['present']},{course['absent']},{course['late']},"
                                f"{course['excused']},{course['attendance_rate']}%")
            
            # Add summary line
            stats = report_data['overall_stats']
            csv_lines.append('')
            csv_lines.append(f"Overall Attendance Rate: {stats['overall_attendance_rate']}%")
            
            return '\n'.join(csv_lines)
        
        return "Unsupported report type"
    
    def format_report_table(self, report_data, report_type):
        """Format report data as a text table using tabulate"""
        if report_type == 'course':
            # Course report table format
            headers = ['Student ID', 'Student Name', 'Total', 'Present', 'Absent', 'Late', 'Excused', 'Rate %']
            
            rows = []
            for student in report_data['student_summaries']:
                rows.append([
                    student['student_code'],
                    student['student_name'],
                    student['total_classes'],
                    student['present'],
                    student['absent'],
                    student['late'],
                    student['excused'],
                    f"{student['attendance_rate']}%"
                ])
            
            table = tabulate(rows, headers=headers, tablefmt='grid')
            
            # Add summary
            summary = report_data['course_summary']
            result = [
                f"Course: {summary['course_code']} - {summary['course_name']}",
                f"Instructor: {summary['instructor_name']}",
                f"Date Range: {summary['start_date']} to {summary['end_date']}",
                f"Students: {summary['total_students']}, Classes: {summary['total_dates']}",
                f"Overall Attendance Rate: {summary['overall_attendance_rate']}%",
                "",
                table
            ]
            
            return '\n'.join(result)
            
        elif report_type == 'student':
            # Student report table format
            headers = ['Course', 'Total', 'Present', 'Absent', 'Late', 'Excused', 'Rate %', 'Last Date']
            
            rows = []
            for course in report_data['course_details']:
                rows.append([
                    f"{course['course_code']} - {course['course_name']}",
                    course['total_classes'],
                    course['present'],
                    course['absent'],
                    course['late'],
                    course['excused'],
                    f"{course['attendance_rate']}%",
                    course['last_attendance_date'] or 'N/A'
                ])
            
            table = tabulate(rows, headers=headers, tablefmt='grid')
            
            # Add summary
            student = report_data['student']
            stats = report_data['overall_stats']
            result = [
                f"Student: {student['student_id']} - {student['full_name']}",
                f"Email: {student['email'] or 'N/A'}",
                f"Courses Enrolled: {stats['total_courses']}",
                f"Overall Attendance Rate: {stats['overall_attendance_rate']}%",
                "",
                table
            ]
            
            return '\n'.join(result)
        
        return "Unsupported report type" 