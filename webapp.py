from flask import Flask, render_template, redirect, url_for, flash, request, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField, BooleanField, TextAreaField, DateField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Optional
import os
from datetime import datetime, date, timedelta
import sqlite3

from database import init_db, get_connection
from auth import Auth
from admin import AdminManager
from instructor import InstructorManager
from reports import ReportManager

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Create Auth instance for our app
auth_system = Auth()
admin_manager = AdminManager(auth_system)
instructor_manager = InstructorManager(auth_system)
report_manager = ReportManager(auth_system)

# Initialize database
init_db()

# --- User class for Flask-Login ---
class User(UserMixin):
    def __init__(self, user_data):
        self.id = user_data['id']
        self.username = user_data['username']
        self.full_name = user_data['full_name']
        self.role = user_data['role']

# --- Forms ---
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    full_name = StringField('Full Name', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Role', choices=[('admin', 'Administrator'), ('instructor', 'Instructor')])
    submit = SubmitField('Add User')

class StudentForm(FlaskForm):
    student_id = StringField('Student ID', validators=[DataRequired()])
    full_name = StringField('Full Name', validators=[DataRequired()])
    email = StringField('Email', validators=[Optional(), Email()])
    phone = StringField('Phone', validators=[Optional()])
    submit = SubmitField('Submit')

class CourseForm(FlaskForm):
    course_code = StringField('Course Code', validators=[DataRequired()])
    course_name = StringField('Course Name', validators=[DataRequired()])
    instructor_id = SelectField('Instructor', coerce=int, validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])
    submit = SubmitField('Submit')

class PasswordChangeForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Change Password')

# --- User Loader ---
@login_manager.user_loader
def load_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    
    if user_data:
        return User(user_data)
    
    return None

# --- Context Processors ---
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

# --- Routes ---
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        
        if auth_system.login(username, password):
            user_data = auth_system.get_current_user()
            user = User(user_data)
            login_user(user, remember=form.remember.data)
            
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    
    return render_template('login.html', form=form, title='Login')

@app.route('/logout')
@login_required
def logout():
    auth_system.logout()
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get some stats for the dashboard
    cursor.execute('SELECT COUNT(*) FROM students')
    student_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM courses')
    course_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM enrollments')
    enrollment_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM attendance')
    attendance_count = cursor.fetchone()[0]
    
    # Get latest courses
    if current_user.role == 'admin':
        cursor.execute('''
        SELECT c.*, u.full_name as instructor_name 
        FROM courses c JOIN users u ON c.instructor_id = u.id
        ORDER BY c.created_at DESC LIMIT 5
        ''')
    else:
        cursor.execute('''
        SELECT c.*, u.full_name as instructor_name 
        FROM courses c JOIN users u ON c.instructor_id = u.id
        WHERE c.instructor_id = ?
        ORDER BY c.created_at DESC LIMIT 5
        ''', (current_user.id,))
    
    latest_courses = [dict(course) for course in cursor.fetchall()]
    
    # Get latest attendance records
    if current_user.role == 'admin':
        cursor.execute('''
        SELECT a.date, a.status, s.full_name as student_name, c.course_name
        FROM attendance a
        JOIN enrollments e ON a.enrollment_id = e.id
        JOIN students s ON e.student_id = s.id
        JOIN courses c ON e.course_id = c.id
        ORDER BY a.created_at DESC LIMIT 10
        ''')
    else:
        cursor.execute('''
        SELECT a.date, a.status, s.full_name as student_name, c.course_name
        FROM attendance a
        JOIN enrollments e ON a.enrollment_id = e.id
        JOIN students s ON e.student_id = s.id
        JOIN courses c ON e.course_id = c.id
        WHERE c.instructor_id = ?
        ORDER BY a.created_at DESC LIMIT 10
        ''', (current_user.id,))
    
    latest_attendance = [dict(record) for record in cursor.fetchall()]
    
    conn.close()
    
    return render_template('dashboard.html', 
                           title='Dashboard',
                           student_count=student_count,
                           course_count=course_count,
                           enrollment_count=enrollment_count,
                           attendance_count=attendance_count,
                           latest_courses=latest_courses,
                           latest_attendance=latest_attendance)

# --- Student Routes ---
@app.route('/students')
@login_required
def students():
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    success, message, students_list = admin_manager.list_students()
    
    return render_template('students.html', 
                          title='Student Management',
                          students=students_list)

@app.route('/students/add', methods=['GET', 'POST'])
@login_required
def add_student():
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    form = StudentForm()
    
    if form.validate_on_submit():
        success, message = admin_manager.add_student(
            form.student_id.data,
            form.full_name.data,
            form.email.data,
            form.phone.data
        )
        
        if success:
            flash(message, 'success')
            return redirect(url_for('students'))
        else:
            flash(message, 'danger')
    
    return render_template('student_form.html', 
                          title='Add Student',
                          form=form,
                          action='Add')

@app.route('/students/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_student(id):
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get current student data
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM students WHERE id = ?', (id,))
    student = cursor.fetchone()
    conn.close()
    
    if not student:
        flash('Student not found.', 'danger')
        return redirect(url_for('students'))
    
    form = StudentForm()
    
    if request.method == 'GET':
        form.student_id.data = student['student_id']
        form.full_name.data = student['full_name']
        form.email.data = student['email']
        form.phone.data = student['phone']
    
    if form.validate_on_submit():
        success, message = admin_manager.edit_student(
            id,
            form.student_id.data,
            form.full_name.data,
            form.email.data,
            form.phone.data
        )
        
        if success:
            flash(message, 'success')
            return redirect(url_for('students'))
        else:
            flash(message, 'danger')
    
    return render_template('student_form.html', 
                          title='Edit Student',
                          form=form,
                          action='Update')

@app.route('/students/delete/<int:id>', methods=['POST'])
@login_required
def delete_student(id):
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    success, message = admin_manager.delete_student(id)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('students'))

@app.route('/students/delete_with_records/<int:id>', methods=['POST'])
@login_required
def delete_student_with_records(id):
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    success, message = admin_manager.delete_student_with_records(id)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('students'))

# --- Course Routes ---
@app.route('/courses')
@login_required
def courses():
    success, message, courses_list = admin_manager.list_courses()
    
    return render_template('courses.html', 
                          title='Course Management',
                          courses=courses_list)

@app.route('/courses/add', methods=['GET', 'POST'])
@login_required
def add_course():
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    form = CourseForm()
    
    # Populate instructor choices
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, full_name FROM users WHERE role = "instructor" ORDER BY full_name')
    instructors = cursor.fetchall()
    conn.close()
    
    form.instructor_id.choices = [(i['id'], i['full_name']) for i in instructors]
    
    if form.validate_on_submit():
        success, message = admin_manager.add_course(
            form.course_code.data,
            form.course_name.data,
            form.instructor_id.data,
            form.description.data
        )
        
        if success:
            flash(message, 'success')
            return redirect(url_for('courses'))
        else:
            flash(message, 'danger')
    
    return render_template('course_form.html', 
                          title='Add Course',
                          form=form,
                          action='Add')

@app.route('/courses/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_course(id):
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get current course data
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM courses WHERE id = ?', (id,))
    course = cursor.fetchone()
    
    if not course:
        conn.close()
        flash('Course not found.', 'danger')
        return redirect(url_for('courses'))
    
    # Populate instructor choices
    cursor.execute('SELECT id, full_name FROM users WHERE role = "instructor" ORDER BY full_name')
    instructors = cursor.fetchall()
    conn.close()
    
    form = CourseForm()
    form.instructor_id.choices = [(i['id'], i['full_name']) for i in instructors]
    
    if request.method == 'GET':
        form.course_code.data = course['course_code']
        form.course_name.data = course['course_name']
        form.instructor_id.data = course['instructor_id']
        form.description.data = course['description']
    
    if form.validate_on_submit():
        success, message = admin_manager.edit_course(
            id,
            form.course_code.data,
            form.course_name.data,
            form.instructor_id.data,
            form.description.data
        )
        
        if success:
            flash(message, 'success')
            return redirect(url_for('courses'))
        else:
            flash(message, 'danger')
    
    return render_template('course_form.html', 
                          title='Edit Course',
                          form=form,
                          action='Update')

@app.route('/courses/delete/<int:id>', methods=['POST'])
@login_required
def delete_course(id):
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    success, message = admin_manager.delete_course(id)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('courses'))

# --- Enrollment Routes ---
@app.route('/enrollments')
@login_required
def enrollments():
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    success, message, enrollments_list = admin_manager.list_enrollments()
    
    return render_template('enrollments.html', 
                          title='Enrollment Management',
                          enrollments=enrollments_list)

@app.route('/enrollments/add', methods=['GET', 'POST'])
@login_required
def add_enrollment():
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get students
    success, message, students = admin_manager.list_students()
    
    # Get courses
    success, message, courses = admin_manager.list_courses()
    
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        course_id = request.form.get('course_id')
        
        if student_id and course_id:
            success, message = admin_manager.enroll_student(student_id, course_id)
            
            if success:
                flash(message, 'success')
                return redirect(url_for('enrollments'))
            else:
                flash(message, 'danger')
    
    return render_template('enrollment_form.html', 
                          title='Add Enrollment',
                          students=students,
                          courses=courses)

@app.route('/enrollments/delete/<int:id>', methods=['POST'])
@login_required
def delete_enrollment(id):
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    success, message = admin_manager.unenroll_student(id)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('enrollments'))

# --- Attendance Routes ---
@app.route('/attendance')
@login_required
def attendance():
    success, message, courses = instructor_manager.get_instructor_courses()
    
    return render_template('attendance.html', 
                          title='Attendance Management',
                          courses=courses)

@app.route('/attendance/take/<int:course_id>', methods=['GET', 'POST'])
@login_required
def take_attendance(course_id):
    # Get course details
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT c.*, u.full_name as instructor_name
    FROM courses c
    JOIN users u ON c.instructor_id = u.id
    WHERE c.id = ?
    ''', (course_id,))
    course = cursor.fetchone()
    conn.close()
    
    if not course:
        flash('Course not found.', 'danger')
        return redirect(url_for('attendance'))
    
    # Check if user has permission
    if current_user.role != 'admin' and course['instructor_id'] != current_user.id:
        flash('You do not have permission to take attendance for this course.', 'danger')
        return redirect(url_for('attendance'))
    
    # Get students for this course
    success, message, students = instructor_manager.get_course_students(course_id)
    
    if not students:
        flash('No students enrolled in this course.', 'danger')
        return redirect(url_for('attendance'))
    
    attendance_date = request.form.get('attendance_date', date.today().isoformat())
    
    if request.method == 'POST' and 'submit' in request.form:
        attendance_data = []
        
        for student in students:
            enrollment_id = student['enrollment_id']
            status = request.form.get(f'status_{enrollment_id}')
            notes = request.form.get(f'notes_{enrollment_id}', '')
            
            if status:
                attendance_data.append({
                    'enrollment_id': enrollment_id,
                    'status': status,
                    'notes': notes
                })
        
        if attendance_data:
            success, message = instructor_manager.take_bulk_attendance(course_id, attendance_date, attendance_data)
            
            if success:
                flash(message, 'success')
                return redirect(url_for('attendance'))
            else:
                flash(message, 'danger')
    
    return render_template('take_attendance.html', 
                          title=f'Take Attendance - {course["course_name"]}',
                          course=course,
                          students=students,
                          attendance_date=attendance_date)

@app.route('/attendance/view/<int:course_id>')
@login_required
def view_attendance(course_id):
    # Get course details
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT c.*, u.full_name as instructor_name
    FROM courses c
    JOIN users u ON c.instructor_id = u.id
    WHERE c.id = ?
    ''', (course_id,))
    course = cursor.fetchone()
    conn.close()
    
    if not course:
        flash('Course not found.', 'danger')
        return redirect(url_for('attendance'))
    
    # Check if user has permission
    if current_user.role != 'admin' and course['instructor_id'] != current_user.id:
        flash('You do not have permission to view attendance for this course.', 'danger')
        return redirect(url_for('attendance'))
    
    # Get attendance records
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date', date.today().isoformat())
    
    success, message, records = instructor_manager.get_attendance_records(course_id, start_date, end_date)
    
    # Group records by date
    dates = {}
    for record in records:
        if record['date'] not in dates:
            dates[record['date']] = []
        dates[record['date']].append(record)
    
    return render_template('view_attendance.html', 
                          title=f'Attendance Records - {course["course_name"]}',
                          course=course,
                          dates=dates,
                          start_date=start_date,
                          end_date=end_date)

# --- Report Routes ---
@app.route('/reports')
@login_required
def reports():
    return render_template('reports.html', title='Reports')

@app.route('/reports/course', methods=['GET', 'POST'])
@login_required
def course_report():
    success, message, courses = instructor_manager.get_instructor_courses()
    
    if request.method == 'POST':
        course_id = request.form.get('course_id')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date', date.today().isoformat())
        
        if course_id:
            success, message, report_data = report_manager.course_attendance_summary(course_id, start_date, end_date)
            
            if success:
                return render_template('course_report.html', 
                                      title='Course Attendance Report',
                                      report=report_data,
                                      export_url=url_for('export_course_report', 
                                                       course_id=course_id,
                                                       start_date=start_date,
                                                       end_date=end_date))
            else:
                flash(message, 'danger')
    
    thirty_days_ago = (date.today() - timedelta(days=30)).isoformat()
    
    return render_template('course_report_form.html', 
                          title='Course Attendance Report',
                          courses=courses,
                          default_start_date=thirty_days_ago,
                          default_end_date=date.today().isoformat())

@app.route('/reports/student', methods=['GET', 'POST'])
@login_required
def student_report():
    # Get list of students based on role
    conn = get_connection()
    cursor = conn.cursor()
    
    if current_user.role == 'admin':
        cursor.execute('SELECT id, student_id, full_name FROM students ORDER BY full_name')
    else:
        cursor.execute('''
        SELECT DISTINCT s.id, s.student_id, s.full_name
        FROM students s
        JOIN enrollments e ON s.id = e.student_id
        JOIN courses c ON e.course_id = c.id
        WHERE c.instructor_id = ?
        ORDER BY s.full_name
        ''', (current_user.id,))
    
    students = [dict(student) for student in cursor.fetchall()]
    conn.close()
    
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        
        if student_id:
            success, message, report_data = report_manager.student_attendance_report(student_id)
            
            if success:
                return render_template('student_report.html', 
                                      title='Student Attendance Report',
                                      report=report_data,
                                      export_url=url_for('export_student_report', student_id=student_id))
            else:
                flash(message, 'danger')
    
    return render_template('student_report_form.html', 
                          title='Student Attendance Report',
                          students=students)

@app.route('/reports/export/course/<int:course_id>')
@login_required
def export_course_report(course_id):
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date', date.today().isoformat())
    
    success, message, report_data = report_manager.course_attendance_summary(course_id, start_date, end_date)
    
    if success:
        csv_data = report_manager.generate_csv_report(report_data, 'course')
        response = app.response_class(
            csv_data,
            mimetype='text/csv',
            headers={"Content-Disposition": f"attachment;filename=course_report_{report_data['course_summary']['course_code']}.csv"}
        )
        return response
    else:
        flash(message, 'danger')
        return redirect(url_for('reports'))

@app.route('/reports/export/student/<int:student_id>')
@login_required
def export_student_report(student_id):
    success, message, report_data = report_manager.student_attendance_report(student_id)
    
    if success:
        csv_data = report_manager.generate_csv_report(report_data, 'student')
        response = app.response_class(
            csv_data,
            mimetype='text/csv',
            headers={"Content-Disposition": f"attachment;filename=student_report_{report_data['student']['student_id']}.csv"}
        )
        return response
    else:
        flash(message, 'danger')
        return redirect(url_for('reports'))

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', title='Profile')

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = PasswordChangeForm()
    
    if form.validate_on_submit():
        old_password = form.current_password.data
        new_password = form.new_password.data
        
        success, message = auth_system.change_password(old_password, new_password)
        
        if success:
            flash(message, 'success')
            return redirect(url_for('profile'))
        else:
            flash(message, 'danger')
    
    return render_template('change_password.html', title='Change Password', form=form)

# --- User Management Routes ---
@app.route('/users')
@login_required
def users():
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, full_name, role, created_at FROM users ORDER BY role, username')
    users_list = [dict(user) for user in cursor.fetchall()]
    conn.close()
    
    return render_template('users.html', title='User Management', users=users_list)

@app.route('/users/add', methods=['GET', 'POST'])
@login_required
def add_user():
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    form = UserForm()
    
    if form.validate_on_submit():
        success, message = auth_system.register_user(
            form.username.data,
            form.password.data,
            form.full_name.data,
            form.role.data
        )
        
        if success:
            flash(message, 'success')
            return redirect(url_for('users'))
        else:
            flash(message, 'danger')
    
    return render_template('user_form.html', title='Add User', form=form)

@app.route('/users/delete/<int:id>', methods=['POST'])
@login_required
def delete_user(id):
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    success, message = auth_system.delete_user(id)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('users'))

if __name__ == '__main__':
    app.run(debug=True) 