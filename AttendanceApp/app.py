from datetime import datetime, timedelta
from functools import cache
from flask import Flask, make_response, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from datetime import datetime, timedelta
import calendar

app = Flask(__name__, static_url_path='/static')
app.config['SECRET_KEY'] = 'chimichangas'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'password'
app.config['MYSQL_DB'] = 'sparsha'

app.config["CACHE_TYPE"] = "null"

mysql = MySQL(app)

# Create tables
with app.app_context():
    cur = mysql.connection.cursor()

    # Create the Students table
    cur.execute('''CREATE TABLE IF NOT EXISTS students (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    firstname VARCHAR(100) NOT NULL,
                    lastname VARCHAR(100) NOT NULL,
                    email VARCHAR(80) UNIQUE NOT NULL,
                    age INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    bio TEXT)''')

    # Create the Attendance table
    # Create the Attendance table
    cur.execute('''CREATE TABLE IF NOT EXISTS attendance (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    student_id INT NOT NULL UNIQUE,
                    student_name VARCHAR(255) NOT NULL,
                    attendance_status VARCHAR(10) NOT NULL,
                    days_missed INT NOT NULL,
                    attendance_time TIME NOT NULL,
                    date_taken DATE NOT NULL,
                    
                    project VARCHAR(50) NOT NULL,
                    FOREIGN KEY (student_id) REFERENCES students(id))''')


    # Create the ProjectHead table
    cur.execute('''CREATE TABLE IF NOT EXISTS project_head (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password VARCHAR(50) NOT NULL)''')

    # Create the Projects table
    cur.execute('''CREATE TABLE IF NOT EXISTS projects (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(50) NOT NULL,
                    description VARCHAR(255),
                    teacher_id INT NOT NULL,
                    FOREIGN KEY (teacher_id) REFERENCES project_head(id))''')

    mysql.connection.commit()
    cur.close()


@app.route('/')
def start_page():
    if 'teacher_email' in session:
        # If the user is logged in, redirect them to another page
        return redirect(url_for('projects'))

    # Clear the session to log out the user
    session.pop('teacher_email', None)

    # Set caching directives to prevent back button usage
    response = make_response(render_template('start_page.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'

    return response


@app.route('/display/<int:project_id>')
def display(project_id):
    if 'teacher_email' in session:
        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT * FROM attendance WHERE project_id = %s", (project_id,))
        attendance_data = cur.fetchall()
        cur.close()
        return render_template('display.html', attendance_data=attendance_data, project_id=project_id)


@app.route('/add_attendance/<int:project_id>', methods=['GET', 'POST'])
def add_attendance(project_id):
    try:
        if request.method == 'POST':
            current_timestamp=datetime.now()
            cur = mysql.connection.cursor()
            volunteer_id = request.form['volunteer_id']
            volunteer_name = request.form['volunteer_name']
            attendance_status = request.form['attendance_status']

            # Check if a record exists for the given volunteer_id and project_id
            cur.execute(
                "SELECT * FROM attendance WHERE volunteer_id = %s AND project_id = %s", (volunteer_id, project_id))
            existing_record = cur.fetchone()

            if existing_record:
                # Update the existing record
                
                days_missed = existing_record[3] + \
                    (attendance_status == 'Absent')

                cur.execute("UPDATE attendance SET  attendance_status=%s, days_missed=%s, attendance_time=%s, date_taken=%s WHERE volunteer_id=%s AND project_id=%s",
                            ( attendance_status, days_missed, current_timestamp.time(), current_timestamp.date(), project_id, volunteer_id))

                # Insert a new record
                days_present = (attendance_status == 'Present')
                days_missed = (attendance_status == 'Absent')

                cur.execute("INSERT INTO attendance (volunteer_id, volunteer_name, attendance_status,  days_missed, attendance_time, date_taken, project_id) VALUES (%s, %s, %s,  %s, %s, %s, %s)",
                            (volunteer_id, volunteer_name, attendance_status,  days_missed, current_timestamp.time(), current_timestamp.date(), project_id))

            mysql.connection.commit()
            cur.close()

            return redirect(url_for('display', project_id=project_id))
    except mysql.connection.IntegrityError as e:
        # Handle the specific IntegrityError (duplicate key error)
        error_message = "ID already exists."

        # Render the template with the error message
        return render_template('add_attendance.html', project_id=project_id, error_message=error_message)

    current_date = datetime.now().date()
    _, last_day_of_month = calendar.monthrange(
        current_date.year, current_date.month)
    dates = [current_date + timedelta(days=i)
             for i in range(1, last_day_of_month + 1)]

    return render_template('add_attendance.html', project_id=project_id)


@app.route('/teacher_register', methods=['GET', 'POST'])
def teacher_register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Check if the username is already taken
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM project_head WHERE email = %s", (email,))
        existing_teacher = cur.fetchone()

        if existing_teacher is None:
            cur.execute(
                "INSERT INTO project_head (email, password) VALUES (%s, %s)", (email, password))
            mysql.connection.commit()
            cur.close()

            session['teacher_email'] = email
            return redirect(url_for('teacher_login'))
        else:
            flash("Email has already been registered, please login.", "error")

    return render_template('teacher_register.html')


@app.route('/teacher_login', methods=['GET', 'POST'])
def teacher_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT * FROM project_head WHERE email = %s AND password = %s", (email, password))
        teacher = cur.fetchone()
        cur.close()

        if teacher:
            session['teacher_email'] = email
            # Redirect to projects (project selection) page
            response = redirect(url_for('projects'))
            response.headers['Cache-Control'] = 'private, no-cache, no-store, must-revalidate'
            response.headers['Expires'] = '-1'
            response.headers['Pragma'] = 'no-cache'
            return response
        else:
            flash(
                "Incorrect details entered. Please try again or register a new account.", "error")

    return render_template('teacher_login.html')


@app.route('/logout')
def logout():
    # Clear the session to log out the user
    del session['teacher_email']
    session.pop('teacher_email',None)
    # Set caching directives to prevent back button usage
    response = redirect(url_for('start_page'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'

    flash('You have been successfully logged out.', 'success')

    return response


@app.route('/add_project', methods=['GET', 'POST'])
def add_project():
    if request.method == 'POST':
        project_name = request.form['project_name']
        project_description = request.form['project_description']

        teacher_email = session.get('teacher_email')
        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM project_head WHERE email = %s",
                    (teacher_email,))
        teacher_id = cur.fetchone()[0]
        cur.execute("INSERT INTO projects (name, description, teacher_id) VALUES (%s, %s, %s)",
                    (project_name, project_description, teacher_id))
        mysql.connection.commit()
        cur.close()
        
        return redirect(url_for('projects'))

    return render_template('add_project.html')


@app.route('/projects')
def projects():
    if 'teacher_email' in session:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM projects")
        projects_data = cur.fetchall()
        cur.close()
        #print(projects_data)
        return render_template('projects.html', projects_data=projects_data)


    return redirect(url_for('start_page'))


@app.route('/profile')
def profile():
    teacher_email = session.get('teacher_email')
    if teacher_email:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM project_head WHERE email = %s",
                    (teacher_email,))
        teacher = cur.fetchone()
        cur.close()

        return render_template('profile.html', teacher=teacher)
    else:
        return redirect(url_for('start_page'))


if __name__ == '__main__':
    
    app.run(debug=True)
