import os
import sys
from datetime import datetime, date, timedelta
import getpass

from database import init_db, get_connection
from auth import Auth
from admin import AdminManager
from instructor import InstructorManager
from reports import ReportManager

class AttendanceSystem:
    def __init__(self):
        self.auth = Auth()
        self.admin = AdminManager(self.auth)
        self.instructor = InstructorManager(self.auth)
        self.reports = ReportManager(self.auth)
        
        # Initialize database if it doesn't exist
        init_db()
    
    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self, title):
        """Print a header for menus"""
        self.clear_screen()
        print("=" * 60)
        print(f"{title.center(60)}")
        print("=" * 60)
        print()
    
    def login_menu(self):
        """Display login menu and process authentication"""
        while True:
            self.print_header("Student Attendance System - Login")
            
            print("1. Login")
            print("2. Exit")
            print()
            
            choice = input("Enter your choice (1-2): ")
            
            if choice == '1':
                username = input("Username: ")
                password = getpass.getpass("Password: ")
                
                if self.auth.login(username, password):
                    print("\nLogin successful!")
                    input("Press Enter to continue...")
                    self.main_menu()
                else:
                    print("\nInvalid username or password!")
                    input("Press Enter to continue...")
            
            elif choice == '2':
                sys.exit(0)
    
    def main_menu(self):
        """Display main menu based on user role"""
        if not self.auth.is_authenticated():
            self.login_menu()
            return
        
        user = self.auth.get_current_user()
        
        while True:
            self.print_header(f"Main Menu - Welcome {user['full_name']}")
            
            if self.auth.is_admin():
                print("1. Manage Students")
                print("2. Manage Courses")
                print("3. Manage Enrollments")
                print("4. User Management")
                print("5. Take Attendance")
                print("6. Reports")
                print("7. Change Password")
                print("8. Logout")
                print()
                
                choice = input("Enter your choice (1-8): ")
                
                if choice == '1':
                    self.student_menu()
                elif choice == '2':
                    self.course_menu()
                elif choice == '3':
                    self.enrollment_menu()
                elif choice == '4':
                    self.user_menu()
                elif choice == '5':
                    self.attendance_menu()
                elif choice == '6':
                    self.report_menu()
                elif choice == '7':
                    self.change_password()
                elif choice == '8':
                    self.auth.logout()
                    self.login_menu()
                    return
            
            elif self.auth.is_instructor():
                print("1. View My Courses")
                print("2. Take Attendance")
                print("3. View Attendance Records")
                print("4. Reports")
                print("5. Change Password")
                print("6. Logout")
                print()
                
                choice = input("Enter your choice (1-6): ")
                
                if choice == '1':
                    self.view_instructor_courses()
                elif choice == '2':
                    self.attendance_menu()
                elif choice == '3':
                    self.view_attendance_records()
                elif choice == '4':
                    self.report_menu()
                elif choice == '5':
                    self.change_password()
                elif choice == '6':
                    self.auth.logout()
                    self.login_menu()
                    return
            
            else:
                print("Invalid role. Please contact administrator.")
                input("Press Enter to continue...")
                self.auth.logout()
                self.login_menu()
                return
    
    def change_password(self):
        """Change current user's password"""
        self.print_header("Change Password")
        
        old_password = getpass.getpass("Current Password: ")
        new_password = getpass.getpass("New Password: ")
        confirm_password = getpass.getpass("Confirm New Password: ")
        
        if new_password != confirm_password:
            print("\nNew passwords do not match!")
            input("Press Enter to continue...")
            return
        
        success, message = self.auth.change_password(old_password, new_password)
        print(f"\n{message}")
        input("Press Enter to continue...")
    
    # Admin functions
    def student_menu(self):
        """Student management menu"""
        while True:
            self.print_header("Student Management")
            
            print("1. Add New Student")
            print("2. Edit Student")
            print("3. Delete Student")
            print("4. List All Students")
            print("5. Back to Main Menu")
            print()
            
            choice = input("Enter your choice (1-5): ")
            
            if choice == '1':
                self.add_student()
            elif choice == '2':
                self.edit_student()
            elif choice == '3':
                self.delete_student()
            elif choice == '4':
                self.list_students()
            elif choice == '5':
                return
    
    def add_student(self):
        """Add a new student"""
        self.print_header("Add New Student")
        
        student_id = input("Student ID: ")
        full_name = input("Full Name: ")
        email = input("Email (optional): ") or None
        phone = input("Phone (optional): ") or None
        
        success, message = self.admin.add_student(student_id, full_name, email, phone)
        print(f"\n{message}")
        input("Press Enter to continue...")
    
    def edit_student(self):
        """Edit an existing student"""
        self.print_header("Edit Student")
        
        success, message, students = self.admin.list_students()
        
        if not success:
            print(f"\n{message}")
            input("Press Enter to continue...")
            return
        
        print("\nAvailable Students:")
        for i, student in enumerate(students, 1):
            print(f"{i}. {student['student_id']} - {student['full_name']}")
        
        try:
            index = int(input("\nEnter student number to edit (0 to cancel): "))
            if index == 0:
                return
            
            student = students[index-1]
            
            print(f"\nEditing Student: {student['student_id']} - {student['full_name']}")
            print("Leave blank to keep current value")
            
            student_id = input(f"Student ID [{student['student_id']}]: ") or None
            full_name = input(f"Full Name [{student['full_name']}]: ") or None
            email = input(f"Email [{student['email'] or 'None'}]: ") or None
            phone = input(f"Phone [{student['phone'] or 'None'}]: ") or None
            
            success, message = self.admin.edit_student(student['id'], student_id, full_name, email, phone)
            print(f"\n{message}")
            
        except (ValueError, IndexError):
            print("\nInvalid selection!")
        
        input("Press Enter to continue...")
    
    def delete_student(self):
        """Delete a student"""
        self.print_header("Delete Student")
        
        success, message, students = self.admin.list_students()
        
        if not success:
            print(f"\n{message}")
            input("Press Enter to continue...")
            return
        
        print("\nAvailable Students:")
        for i, student in enumerate(students, 1):
            print(f"{i}. {student['student_id']} - {student['full_name']}")
        
        try:
            index = int(input("\nEnter student number to delete (0 to cancel): "))
            if index == 0:
                return
            
            student = students[index-1]
            
            confirm = input(f"\nAre you sure you want to delete {student['full_name']}? (y/n): ")
            
            if confirm.lower() == 'y':
                success, message = self.admin.delete_student(student['id'])
                print(f"\n{message}")
            
        except (ValueError, IndexError):
            print("\nInvalid selection!")
        
        input("Press Enter to continue...")
    
    def list_students(self):
        """List all students"""
        self.print_header("Student List")
        
        success, message, students = self.admin.list_students()
        
        if not success:
            print(f"\n{message}")
            input("Press Enter to continue...")
            return
        
        print(f"\n{message}")
        print("\nID\tStudent ID\tName\t\t\tEmail")
        print("-" * 70)
        
        for student in students:
            # Pad the name field for better alignment
            name = student['full_name']
            if len(name) < 16:
                name = name + ' ' * (16 - len(name))
            
            print(f"{student['id']}\t{student['student_id']}\t\t{name}\t{student['email'] or ''}")
        
        input("\nPress Enter to continue...")
    
    def course_menu(self):
        """Course management menu"""
        while True:
            self.print_header("Course Management")
            
            print("1. Add New Course")
            print("2. Edit Course")
            print("3. Delete Course")
            print("4. List All Courses")
            print("5. Back to Main Menu")
            print()
            
            choice = input("Enter your choice (1-5): ")
            
            if choice == '1':
                self.add_course()
            elif choice == '2':
                self.edit_course()
            elif choice == '3':
                self.delete_course()
            elif choice == '4':
                self.list_courses()
            elif choice == '5':
                return
    
    def get_instructors(self):
        """Get all instructors from the database"""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, username, full_name
        FROM users
        WHERE role = 'instructor'
        ORDER BY full_name
        ''')
        
        instructors = [dict(instructor) for instructor in cursor.fetchall()]
        conn.close()
        
        return instructors
    
    def add_course(self):
        """Add a new course"""
        self.print_header("Add New Course")
        
        # Get list of instructors
        instructors = self.get_instructors()
        
        if not instructors:
            print("\nNo instructors available. Please add an instructor first.")
            input("Press Enter to continue...")
            return
        
        print("\nAvailable Instructors:")
        for i, instructor in enumerate(instructors, 1):
            print(f"{i}. {instructor['full_name']} ({instructor['username']})")
        
        try:
            index = int(input("\nSelect instructor (0 to cancel): "))
            if index == 0:
                return
            
            instructor = instructors[index-1]
            
            course_code = input("\nCourse Code: ")
            course_name = input("Course Name: ")
            description = input("Description (optional): ") or None
            
            success, message = self.admin.add_course(course_code, course_name, instructor['id'], description)
            print(f"\n{message}")
            
        except (ValueError, IndexError):
            print("\nInvalid selection!")
        
        input("Press Enter to continue...")
    
    def edit_course(self):
        """Edit an existing course"""
        self.print_header("Edit Course")
        
        success, message, courses = self.admin.list_courses()
        
        if not success:
            print(f"\n{message}")
            input("Press Enter to continue...")
            return
        
        print("\nAvailable Courses:")
        for i, course in enumerate(courses, 1):
            print(f"{i}. {course['course_code']} - {course['course_name']} (Instructor: {course['instructor_name']})")
        
        try:
            index = int(input("\nEnter course number to edit (0 to cancel): "))
            if index == 0:
                return
            
            course = courses[index-1]
            
            print(f"\nEditing Course: {course['course_code']} - {course['course_name']}")
            print("Leave blank to keep current value")
            
            course_code = input(f"Course Code [{course['course_code']}]: ") or None
            course_name = input(f"Course Name [{course['course_name']}]: ") or None
            description = input(f"Description [{course['description'] or 'None'}]: ") or None
            
            # Change instructor option
            change_instructor = input("\nDo you want to change the instructor? (y/n): ")
            
            instructor_id = None
            if change_instructor.lower() == 'y':
                instructors = self.get_instructors()
                
                print("\nAvailable Instructors:")
                for i, instructor in enumerate(instructors, 1):
                    print(f"{i}. {instructor['full_name']} ({instructor['username']})")
                
                try:
                    idx = int(input("\nSelect new instructor (0 to cancel): "))
                    if idx == 0:
                        return
                    
                    instructor = instructors[idx-1]
                    instructor_id = instructor['id']
                    
                except (ValueError, IndexError):
                    print("\nInvalid selection, keeping current instructor!")
            
            success, message = self.admin.edit_course(course['id'], course_code, course_name, instructor_id, description)
            print(f"\n{message}")
            
        except (ValueError, IndexError):
            print("\nInvalid selection!")
        
        input("Press Enter to continue...")
    
    def delete_course(self):
        """Delete a course"""
        self.print_header("Delete Course")
        
        success, message, courses = self.admin.list_courses()
        
        if not success:
            print(f"\n{message}")
            input("Press Enter to continue...")
            return
        
        print("\nAvailable Courses:")
        for i, course in enumerate(courses, 1):
            print(f"{i}. {course['course_code']} - {course['course_name']} (Instructor: {course['instructor_name']})")
        
        try:
            index = int(input("\nEnter course number to delete (0 to cancel): "))
            if index == 0:
                return
            
            course = courses[index-1]
            
            confirm = input(f"\nAre you sure you want to delete {course['course_name']}? (y/n): ")
            
            if confirm.lower() == 'y':
                success, message = self.admin.delete_course(course['id'])
                print(f"\n{message}")
            
        except (ValueError, IndexError):
            print("\nInvalid selection!")
        
        input("Press Enter to continue...")
    
    def list_courses(self):
        """List all courses"""
        self.print_header("Course List")
        
        success, message, courses = self.admin.list_courses()
        
        if not success:
            print(f"\n{message}")
            input("Press Enter to continue...")
            return
        
        print(f"\n{message}")
        print("\nID\tCode\tName\t\t\tInstructor")
        print("-" * 70)
        
        for course in courses:
            # Pad the name field for better alignment
            name = course['course_name']
            if len(name) < 16:
                name = name + ' ' * (16 - len(name))
            
            print(f"{course['id']}\t{course['course_code']}\t{name}\t{course['instructor_name']}")
        
        input("\nPress Enter to continue...")
    
    def enrollment_menu(self):
        """Enrollment management menu"""
        while True:
            self.print_header("Enrollment Management")
            
            print("1. Enroll Student in Course")
            print("2. Remove Student from Course")
            print("3. List Enrollments by Course")
            print("4. List Enrollments by Student")
            print("5. Back to Main Menu")
            print()
            
            choice = input("Enter your choice (1-5): ")
            
            if choice == '1':
                self.enroll_student()
            elif choice == '2':
                self.unenroll_student()
            elif choice == '3':
                self.list_enrollments_by_course()
            elif choice == '4':
                self.list_enrollments_by_student()
            elif choice == '5':
                return
    
    def enroll_student(self):
        """Enroll a student in a course"""
        self.print_header("Enroll Student in Course")
        
        # Get list of students
        success, message, students = self.admin.list_students()
        
        if not success or not students:
            print(f"\n{message}")
            input("Press Enter to continue...")
            return
        
        print("\nAvailable Students:")
        for i, student in enumerate(students, 1):
            print(f"{i}. {student['student_id']} - {student['full_name']}")
        
        try:
            student_index = int(input("\nSelect student (0 to cancel): "))
            if student_index == 0:
                return
            
            student = students[student_index-1]
            
            # Get list of courses
            success, message, courses = self.admin.list_courses()
            
            if not success or not courses:
                print(f"\n{message}")
                input("Press Enter to continue...")
                return
            
            print("\nAvailable Courses:")
            for i, course in enumerate(courses, 1):
                print(f"{i}. {course['course_code']} - {course['course_name']} (Instructor: {course['instructor_name']})")
            
            course_index = int(input("\nSelect course (0 to cancel): "))
            if course_index == 0:
                return
            
            course = courses[course_index-1]
            
            success, message = self.admin.enroll_student(student['id'], course['id'])
            print(f"\n{message}")
            
        except (ValueError, IndexError):
            print("\nInvalid selection!")
        
        input("Press Enter to continue...")
    
    def unenroll_student(self):
        """Remove a student from a course"""
        self.print_header("Remove Student from Course")
        
        # First, select a course
        success, message, courses = self.admin.list_courses()
        
        if not success or not courses:
            print(f"\n{message}")
            input("Press Enter to continue...")
            return
        
        print("\nSelect Course:")
        for i, course in enumerate(courses, 1):
            print(f"{i}. {course['course_code']} - {course['course_name']}")
        
        try:
            course_index = int(input("\nSelect course (0 to cancel): "))
            if course_index == 0:
                return
            
            course = courses[course_index-1]
            
            # Get enrollments for this course
            success, message, enrollments = self.admin.list_enrollments(course_id=course['id'])
            
            if not success or not enrollments:
                print(f"\nNo students enrolled in {course['course_name']}")
                input("Press Enter to continue...")
                return
            
            print(f"\nStudents enrolled in {course['course_name']}:")
            for i, enrollment in enumerate(enrollments, 1):
                print(f"{i}. {enrollment['student_code']} - {enrollment['student_name']}")
            
            student_index = int(input("\nSelect student to remove (0 to cancel): "))
            if student_index == 0:
                return
            
            enrollment = enrollments[student_index-1]
            
            confirm = input(f"\nAre you sure you want to remove {enrollment['student_name']} from {course['course_name']}? (y/n): ")
            
            if confirm.lower() == 'y':
                success, message = self.admin.unenroll_student(enrollment['id'])
                print(f"\n{message}")
            
        except (ValueError, IndexError):
            print("\nInvalid selection!")
        
        input("Press Enter to continue...")
    
    def list_enrollments_by_course(self):
        """List enrollments grouped by course"""
        self.print_header("Enrollments by Course")
        
        # Get list of courses
        success, message, courses = self.admin.list_courses()
        
        if not success or not courses:
            print(f"\n{message}")
            input("Press Enter to continue...")
            return
        
        print("\nSelect Course:")
        for i, course in enumerate(courses, 1):
            print(f"{i}. {course['course_code']} - {course['course_name']}")
        
        try:
            course_index = int(input("\nSelect course (0 to cancel): "))
            if course_index == 0:
                return
            
            course = courses[course_index-1]
            
            # Get enrollments for this course
            success, message, enrollments = self.admin.list_enrollments(course_id=course['id'])
            
            self.print_header(f"Students in {course['course_code']} - {course['course_name']}")
            
            if not success or not enrollments:
                print(f"\nNo students enrolled in this course")
                input("Press Enter to continue...")
                return
            
            print(f"\n{message}")
            print("\nID\tStudent ID\tStudent Name\t\tEnrolled On")
            print("-" * 70)
            
            for enrollment in enrollments:
                # Pad the name field for better alignment
                name = enrollment['student_name']
                if len(name) < 16:
                    name = name + ' ' * (16 - len(name))
                
                print(f"{enrollment['id']}\t{enrollment['student_code']}\t\t{name}\t{enrollment['enrollment_date'][:10]}")
            
        except (ValueError, IndexError):
            print("\nInvalid selection!")
        
        input("\nPress Enter to continue...")
    
    def list_enrollments_by_student(self):
        """List enrollments grouped by student"""
        self.print_header("Enrollments by Student")
        
        # Get list of students
        success, message, students = self.admin.list_students()
        
        if not success or not students:
            print(f"\n{message}")
            input("Press Enter to continue...")
            return
        
        print("\nSelect Student:")
        for i, student in enumerate(students, 1):
            print(f"{i}. {student['student_id']} - {student['full_name']}")
        
        try:
            student_index = int(input("\nSelect student (0 to cancel): "))
            if student_index == 0:
                return
            
            student = students[student_index-1]
            
            # Get enrollments for this student
            success, message, enrollments = self.admin.list_enrollments(student_id=student['id'])
            
            self.print_header(f"Courses for {student['full_name']}")
            
            if not success or not enrollments:
                print(f"\nThis student is not enrolled in any courses")
                input("Press Enter to continue...")
                return
            
            print(f"\n{message}")
            print("\nID\tCourse Code\tCourse Name\t\tEnrolled On")
            print("-" * 70)
            
            for enrollment in enrollments:
                # Pad the name field for better alignment
                name = enrollment['course_name']
                if len(name) < 16:
                    name = name + ' ' * (16 - len(name))
                
                print(f"{enrollment['id']}\t{enrollment['course_code']}\t\t{name}\t{enrollment['enrollment_date'][:10]}")
            
        except (ValueError, IndexError):
            print("\nInvalid selection!")
        
        input("\nPress Enter to continue...")
    
    def user_menu(self):
        """User management menu"""
        while True:
            self.print_header("User Management")
            
            print("1. Add New User")
            print("2. List Users")
            print("3. Back to Main Menu")
            print()
            
            choice = input("Enter your choice (1-3): ")
            
            if choice == '1':
                self.add_user()
            elif choice == '2':
                self.list_users()
            elif choice == '3':
                return
    
    def add_user(self):
        """Add a new user (admin or instructor)"""
        self.print_header("Add New User")
        
        username = input("Username: ")
        full_name = input("Full Name: ")
        
        print("\nSelect Role:")
        print("1. Administrator")
        print("2. Instructor")
        
        role_choice = input("\nEnter choice (1-2): ")
        
        if role_choice == '1':
            role = 'admin'
        elif role_choice == '2':
            role = 'instructor'
        else:
            print("\nInvalid role selection!")
            input("Press Enter to continue...")
            return
        
        password = getpass.getpass("\nPassword: ")
        confirm_password = getpass.getpass("Confirm Password: ")
        
        if password != confirm_password:
            print("\nPasswords do not match!")
            input("Press Enter to continue...")
            return
        
        success, message = self.auth.register_user(username, password, full_name, role)
        print(f"\n{message}")
        input("Press Enter to continue...")
    
    def list_users(self):
        """List all users"""
        self.print_header("User List")
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, username, full_name, role, created_at
        FROM users
        ORDER BY role, username
        ''')
        
        users = [dict(user) for user in cursor.fetchall()]
        conn.close()
        
        if not users:
            print("\nNo users found")
            input("Press Enter to continue...")
            return
        
        print(f"\nFound {len(users)} users")
        print("\nID\tUsername\tName\t\t\tRole\t\tCreated On")
        print("-" * 90)
        
        for user in users:
            # Pad the name field for better alignment
            name = user['full_name']
            if len(name) < 16:
                name = name + ' ' * (16 - len(name))
            
            role = user['role'].capitalize()
            if len(role) < 8:
                role = role + ' ' * (8 - len(role))
            
            print(f"{user['id']}\t{user['username']}\t\t{name}\t{role}\t{user['created_at'][:10]}")
        
        input("\nPress Enter to continue...")
    
    def attendance_menu(self):
        """Attendance management menu"""
        while True:
            self.print_header("Attendance Management")
            
            print("1. Take Attendance by Course")
            print("2. View Attendance Records")
            print("3. Back to Main Menu")
            print()
            
            choice = input("Enter your choice (1-3): ")
            
            if choice == '1':
                self.take_attendance_by_course()
            elif choice == '2':
                self.view_attendance_records()
            elif choice == '3':
                return
    
    def take_attendance_by_course(self):
        """Take attendance for a course"""
        self.print_header("Take Attendance")
        
        # Get instructor's courses
        success, message, courses = self.instructor.get_instructor_courses()
        
        if not success or not courses:
            print(f"\n{message}")
            input("Press Enter to continue...")
            return
        
        print("\nSelect Course:")
        for i, course in enumerate(courses, 1):
            print(f"{i}. {course['course_code']} - {course['course_name']}")
        
        try:
            course_index = int(input("\nSelect course (0 to cancel): "))
            if course_index == 0:
                return
            
            course = courses[course_index-1]
            
            # Get students for this course
            success, message, students = self.instructor.get_course_students(course['id'])
            
            if not success or not students:
                print(f"\nNo students enrolled in {course['course_name']}")
                input("Press Enter to continue...")
                return
            
            # Get attendance date
            today = date.today().isoformat()
            attendance_date = input(f"\nAttendance Date (YYYY-MM-DD) [default: {today}]: ") or today
            
            self.print_header(f"Taking Attendance: {course['course_code']} - {course['course_name']} ({attendance_date})")
            
            print("\nMark attendance for each student:")
            print("p = Present, a = Absent, l = Late, e = Excused\n")
            
            attendance_data = []
            
            for student in students:
                while True:
                    status_input = input(f"{student['student_code']} - {student['full_name']}: ").lower()
                    
                    if status_input == 'p':
                        status = 'present'
                        break
                    elif status_input == 'a':
                        status = 'absent'
                        break
                    elif status_input == 'l':
                        status = 'late'
                        break
                    elif status_input == 'e':
                        status = 'excused'
                        break
                    else:
                        print("Invalid input. Use p, a, l, or e.")
                
                notes = input("Notes (optional): ") or None
                
                attendance_data.append({
                    'enrollment_id': student['enrollment_id'],
                    'status': status,
                    'notes': notes
                })
                print()
            
            # Confirm submission
            confirm = input("\nSubmit attendance records? (y/n): ")
            
            if confirm.lower() == 'y':
                success, message = self.instructor.take_bulk_attendance(course['id'], attendance_date, attendance_data)
                print(f"\n{message}")
            
        except (ValueError, IndexError):
            print("\nInvalid selection!")
        
        input("Press Enter to continue...")
    
    def view_attendance_records(self):
        """View attendance records for a course"""
        self.print_header("View Attendance Records")
        
        # Get instructor's courses
        success, message, courses = self.instructor.get_instructor_courses()
        
        if not success or not courses:
            print(f"\n{message}")
            input("Press Enter to continue...")
            return
        
        print("\nSelect Course:")
        for i, course in enumerate(courses, 1):
            print(f"{i}. {course['course_code']} - {course['course_name']}")
        
        try:
            course_index = int(input("\nSelect course (0 to cancel): "))
            if course_index == 0:
                return
            
            course = courses[course_index-1]
            
            # Get date range
            today = date.today().isoformat()
            start_date = input("\nStart Date (YYYY-MM-DD) [optional]: ") or None
            end_date = input("End Date (YYYY-MM-DD) [default: today]: ") or today
            
            # Get attendance records
            success, message, records = self.instructor.get_attendance_records(course['id'], start_date, end_date)
            
            self.print_header(f"Attendance Records: {course['course_code']} - {course['course_name']}")
            
            if not success or not records:
                print(f"\nNo attendance records found for the selected period")
                input("Press Enter to continue...")
                return
            
            print(f"\n{message}")
            
            # Group records by date
            dates = {}
            for record in records:
                if record['date'] not in dates:
                    dates[record['date']] = []
                dates[record['date']].append(record)
            
            # Display records by date
            for date_str in sorted(dates.keys(), reverse=True):
                print(f"\nDate: {date_str}")
                print("Student ID\tStudent Name\t\tStatus\t\tNotes")
                print("-" * 80)
                
                for record in sorted(dates[date_str], key=lambda r: r['student_name']):
                    # Pad the name field for better alignment
                    name = record['student_name']
                    if len(name) < 16:
                        name = name + ' ' * (16 - len(name))
                    
                    status = record['status'].capitalize()
                    if len(status) < 8:
                        status = status + ' ' * (8 - len(status))
                    
                    print(f"{record['student_code']}\t{name}\t{status}\t{record['notes'] or ''}")
                
                input("\nPress Enter to see next date or continue...")
            
        except (ValueError, IndexError):
            print("\nInvalid selection!")
        
        input("Press Enter to continue...")
    
    def view_instructor_courses(self):
        """View courses taught by the instructor"""
        self.print_header("My Courses")
        
        success, message, courses = self.instructor.get_instructor_courses()
        
        if not success or not courses:
            print(f"\n{message}")
            input("Press Enter to continue...")
            return
        
        print(f"\n{message}")
        print("\nID\tCode\tName\t\t\tDescription")
        print("-" * 70)
        
        for course in courses:
            # Pad the name field for better alignment
            name = course['course_name']
            if len(name) < 16:
                name = name + ' ' * (16 - len(name))
            
            desc = course['description'] or ''
            if len(desc) > 30:
                desc = desc[:27] + '...'
            
            print(f"{course['id']}\t{course['course_code']}\t{name}\t{desc}")
        
        # Option to view students in a course
        view_students = input("\nView students in a course? (y/n): ")
        
        if view_students.lower() == 'y':
            try:
                course_index = int(input("\nEnter course number (0 to cancel): "))
                if course_index == 0:
                    return
                
                course = courses[course_index-1]
                
                success, message, students = self.instructor.get_course_students(course['id'])
                
                self.print_header(f"Students in {course['course_code']} - {course['course_name']}")
                
                if not success or not students:
                    print(f"\nNo students enrolled in this course")
                    input("Press Enter to continue...")
                    return
                
                print(f"\n{message}")
                print("\nID\tStudent ID\tName\t\t\tEmail")
                print("-" * 70)
                
                for student in students:
                    # Pad the name field for better alignment
                    name = student['full_name']
                    if len(name) < 16:
                        name = name + ' ' * (16 - len(name))
                    
                    print(f"{student['student_id']}\t{student['student_code']}\t\t{name}\t{student['email'] or ''}")
                
            except (ValueError, IndexError):
                print("\nInvalid selection!")
        
        input("\nPress Enter to continue...")
    
    def report_menu(self):
        """Report generation menu"""
        while True:
            self.print_header("Attendance Reports")
            
            print("1. Course Attendance Summary")
            print("2. Student Attendance Report")
            print("3. Back to Main Menu")
            print()
            
            choice = input("Enter your choice (1-3): ")
            
            if choice == '1':
                self.course_report()
            elif choice == '2':
                self.student_report()
            elif choice == '3':
                return
    
    def course_report(self):
        """Generate course attendance report"""
        self.print_header("Course Attendance Report")
        
        # Get list of courses
        success, message, courses = self.instructor.get_instructor_courses()
        
        if not success or not courses:
            print(f"\n{message}")
            input("Press Enter to continue...")
            return
        
        print("\nSelect Course:")
        for i, course in enumerate(courses, 1):
            print(f"{i}. {course['course_code']} - {course['course_name']}")
        
        try:
            course_index = int(input("\nSelect course (0 to cancel): "))
            if course_index == 0:
                return
            
            course = courses[course_index-1]
            
            # Get date range
            today = date.today().isoformat()
            thirty_days_ago = (date.today() - timedelta(days=30)).isoformat()
            
            start_date = input(f"\nStart Date (YYYY-MM-DD) [default: {thirty_days_ago}]: ") or thirty_days_ago
            end_date = input(f"End Date (YYYY-MM-DD) [default: {today}]: ") or today
            
            # Generate report
            success, message, report_data = self.reports.course_attendance_summary(course['id'], start_date, end_date)
            
            if not success or not report_data:
                print(f"\n{message}")
                input("Press Enter to continue...")
                return
            
            # Display formatted report
            formatted_report = self.reports.format_report_table(report_data, 'course')
            
            self.print_header(f"Course Report: {course['course_code']} - {course['course_name']}")
            print(formatted_report)
            
            # Option to export as CSV
            export_csv = input("\nExport as CSV? (y/n): ")
            if export_csv.lower() == 'y':
                csv_data = self.reports.generate_csv_report(report_data, 'course')
                filename = f"course_report_{course['course_code']}_{start_date}_to_{end_date}.csv"
                
                with open(filename, 'w') as f:
                    f.write(csv_data)
                
                print(f"\nReport exported to {filename}")
            
        except (ValueError, IndexError):
            print("\nInvalid selection!")
        
        input("Press Enter to continue...")
    
    def student_report(self):
        """Generate student attendance report"""
        self.print_header("Student Attendance Report")
        
        # Get list of students
        conn = get_connection()
        cursor = conn.cursor()
        
        query = "SELECT id, student_id, full_name FROM students"
        
        # If instructor, limit to students in their courses
        if not self.auth.is_admin():
            query = '''
            SELECT DISTINCT s.id, s.student_id, s.full_name
            FROM students s
            JOIN enrollments e ON s.id = e.student_id
            JOIN courses c ON e.course_id = c.id
            WHERE c.instructor_id = ?
            ORDER BY s.full_name
            '''
            cursor.execute(query, (self.auth.get_current_user()['id'],))
        else:
            cursor.execute(query)
        
        students = [dict(student) for student in cursor.fetchall()]
        conn.close()
        
        if not students:
            print("\nNo students found")
            input("Press Enter to continue...")
            return
        
        print("\nSelect Student:")
        for i, student in enumerate(students, 1):
            print(f"{i}. {student['student_id']} - {student['full_name']}")
        
        try:
            student_index = int(input("\nSelect student (0 to cancel): "))
            if student_index == 0:
                return
            
            student = students[student_index-1]
            
            # Generate report
            success, message, report_data = self.reports.student_attendance_report(student['id'])
            
            if not success or not report_data:
                print(f"\n{message}")
                input("Press Enter to continue...")
                return
            
            # Display formatted report
            formatted_report = self.reports.format_report_table(report_data, 'student')
            
            self.print_header(f"Student Report: {student['student_id']} - {student['full_name']}")
            print(formatted_report)
            
            # Option to export as CSV
            export_csv = input("\nExport as CSV? (y/n): ")
            if export_csv.lower() == 'y':
                csv_data = self.reports.generate_csv_report(report_data, 'student')
                filename = f"student_report_{student['student_id']}.csv"
                
                with open(filename, 'w') as f:
                    f.write(csv_data)
                
                print(f"\nReport exported to {filename}")
            
        except (ValueError, IndexError):
            print("\nInvalid selection!")
        
        input("Press Enter to continue...")

if __name__ == "__main__":
    system = AttendanceSystem()
    system.login_menu() 