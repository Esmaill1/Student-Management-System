# Software Requirements Specification (SRS)
## Student Attendance System

### 1. Introduction

#### 1.1 Purpose
This document specifies the software requirements for a Student Attendance System that allows instructors to mark and track student attendance, and generate attendance reports. The system is designed to be simple, functional, and operate with an offline SQLite database.

#### 1.2 Scope
The Student Attendance System will include user authentication, student management, course management, attendance tracking, and reporting functionality. The system will be implemented as a command-line interface application.

#### 1.3 Definitions
- **Admin**: A user with full system access and management privileges
- **Instructor**: A user with permissions to manage attendance for assigned courses
- **Student**: An individual whose attendance is being tracked
- **Course**: A class or subject being taught
- **Enrollment**: A record linking a student to a course
- **Attendance Record**: A record of a student's presence status for a specific date

### 2. Overall Description

#### 2.1 Product Perspective
The Student Attendance System is a standalone application that operates offline with a local database. It is designed to be a simple, effective tool for educational institutions to track student attendance.

#### 2.2 Product Functions
- User authentication and authorization
- Student management
- Course management
- Enrollment management
- Attendance tracking
- Report generation

#### 2.3 User Classes and Characteristics
1. **Administrators**
   - Full access to all system functions
   - Responsible for setting up and maintaining the system
   - Manage users, students, courses, and enrollments

2. **Instructors**
   - Access limited to assigned courses
   - Record and view attendance for assigned courses
   - Generate reports for assigned courses and their students

#### 2.4 Operating Environment
- Python 3.6 or higher
- SQLite3 database
- Any operating system that supports Python (Windows, macOS, Linux)

#### 2.5 Design and Implementation Constraints
- Command-line interface
- Offline operation
- SQLite database for data storage
- No external API dependencies

#### 2.6 Assumptions and Dependencies
- Users have basic knowledge of command-line applications
- The system will be run on a computer with Python installed
- The SQLite database file will be accessible and writeable

### 3. Specific Requirements

#### 3.1 External Interface Requirements

##### 3.1.1 User Interfaces
- Command-line interface with menu-driven navigation
- Clear prompts and feedback messages
- Consistent format for displaying data

##### 3.1.2 Hardware Interfaces
- Standard keyboard input
- Standard display output

##### 3.1.3 Software Interfaces
- SQLite database
- Python standard library
- Third-party libraries: bcrypt, tabulate

#### 3.2 Functional Requirements

##### 3.2.1 Authentication
- **FR-1.1**: The system shall allow users to login with a username and password
- **FR-1.2**: The system shall support two user roles: admin and instructor
- **FR-1.3**: The system shall hash passwords for secure storage
- **FR-1.4**: The system shall provide a logout function
- **FR-1.5**: The system shall restrict access based on user role

##### 3.2.2 Student Management
- **FR-2.1**: The system shall allow admins to add new students
- **FR-2.2**: The system shall allow admins to edit existing student information
- **FR-2.3**: The system shall allow admins to delete students (if not enrolled in any courses)
- **FR-2.4**: The system shall allow viewing the list of all students
- **FR-2.5**: The system shall enforce unique student IDs

##### 3.2.3 Course Management
- **FR-3.1**: The system shall allow admins to add new courses
- **FR-3.2**: The system shall allow admins to edit course information
- **FR-3.3**: The system shall allow admins to delete courses (if no students are enrolled)
- **FR-3.4**: The system shall allow viewing the list of all courses
- **FR-3.5**: The system shall enforce unique course codes
- **FR-3.6**: The system shall require each course to have an assigned instructor

##### 3.2.4 Enrollment Management
- **FR-4.1**: The system shall allow admins to enroll students in courses
- **FR-4.2**: The system shall allow admins to remove students from courses
- **FR-4.3**: The system shall prevent duplicate enrollments
- **FR-4.4**: The system shall allow viewing enrollments by course
- **FR-4.5**: The system shall allow viewing enrollments by student

##### 3.2.5 Attendance Tracking
- **FR-5.1**: The system shall allow instructors to record attendance for their courses
- **FR-5.2**: The system shall allow bulk attendance entry for all students in a course
- **FR-5.3**: The system shall support multiple attendance statuses (present, absent, late, excused)
- **FR-5.4**: The system shall record the date and time of attendance entry
- **FR-5.5**: The system shall record which user entered the attendance data
- **FR-5.6**: The system shall allow optional notes for attendance records
- **FR-5.7**: The system shall allow viewing past attendance records

##### 3.2.6 Reporting
- **FR-6.1**: The system shall generate attendance summaries by course
- **FR-6.2**: The system shall generate attendance reports by student
- **FR-6.3**: The system shall calculate attendance rates and statistics
- **FR-6.4**: The system shall allow filtering reports by date range
- **FR-6.5**: The system shall allow exporting reports as CSV files

##### 3.2.7 User Management
- **FR-7.1**: The system shall allow admins to add new users
- **FR-7.2**: The system shall allow viewing the list of all users
- **FR-7.3**: The system shall allow users to change their passwords

#### 3.3 Non-Functional Requirements

##### 3.3.1 Performance
- **NFR-1.1**: The system shall respond to user input within 2 seconds
- **NFR-1.2**: The system shall support databases with up to 1000 students
- **NFR-1.3**: The system shall support databases with up to 100 courses
- **NFR-1.4**: The system shall support databases with up to 5000 attendance records

##### 3.3.2 Security
- **NFR-2.1**: The system shall hash all passwords using bcrypt
- **NFR-2.2**: The system shall enforce role-based access control
- **NFR-2.3**: The system shall validate all user inputs
- **NFR-2.4**: The system shall prevent SQL injection attacks

##### 3.3.3 Usability
- **NFR-3.1**: The system shall provide clear menu navigation
- **NFR-3.2**: The system shall provide meaningful error messages
- **NFR-3.3**: The system shall provide confirmation for critical actions
- **NFR-3.4**: The system shall display data in a readable, formatted manner

##### 3.3.4 Reliability
- **NFR-4.1**: The system shall validate data before writing to the database
- **NFR-4.2**: The system shall handle unexpected inputs gracefully
- **NFR-4.3**: The system shall prevent data loss due to user errors

##### 3.3.5 Maintainability
- **NFR-5.1**: The system shall use a modular design
- **NFR-5.2**: The system shall include comments and documentation
- **NFR-5.3**: The system shall follow consistent naming conventions
- **NFR-5.4**: The system shall separate business logic from user interface code

### 4. Supporting Materials

#### 4.1 Data Models
- Entity-Relationship Diagram (described in README.md)
- Database Schema (implemented in database.py)

#### 4.2 Project Schedule
- Work Breakdown Structure (described in README.md)
- Gantt Chart (provided in gantt_chart.txt) 