from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify
import sqlite3
import os
from datetime import datetime
from database import create_tables

app = Flask(__name__)
app.secret_key = "campus_connect_secret"

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

create_tables()


# ---------------- DB CONNECTION HELPER ----------------
def get_connection():
    conn = sqlite3.connect("campus_connect.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")  # 🔥 ensure cascade always works
    return conn


# ---------------- HOME ----------------
@app.route('/')
def home():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM students")
    total_students = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM faculties")
    total_faculties = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM venues")
    total_venues = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "index.html",
        total_students=total_students,
        total_faculties=total_faculties,
        total_venues=total_venues
    )


# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        contact = request.form['contact']
        programme = request.form['programme']
        semester = request.form['semester']
        register_no = request.form['register_no']
        password = request.form['password']

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO users (email, password, role)
            VALUES (?, ?, ?)
        """, (email, password, "student"))

        user_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO students
            (user_id, name, contact, register_no, programme, semester)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, full_name, contact, register_no, programme, semester))

        conn.commit()
        conn.close()

        flash("Registration successful", "success")
        return redirect(url_for('login'))

    return render_template("register.html")


# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM users WHERE email=? AND password=?
        """, (email, password))

        user = cursor.fetchone()
        conn.close()

        if user:
            session['user_id'] = user['user_id']
            session['role'] = user['role']

            if user['role'] == 'student':
                return redirect('/student_dashboard')
            elif user['role'] == 'faculty':
                return redirect('/faculty_dashboard')
            elif user['role'] == 'admin':
                return redirect('/admin_dashboard')

        flash("Invalid email or password", "danger")

    return render_template("login.html")


# ---------------- ADMIN DASHBOARD ----------------
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' in session and session['role'] == 'admin':
        return render_template("dash_admin.html")
    return redirect('/login')


# ---------------- Manage Students ----------------
@app.route('/admin/manage_students')
def admin_manage_students():
    if 'user_id' in session and session['role'] == 'admin':
        return render_template("admin_manage_students.html")
    return redirect('/login')


# ---------------- View Students ----------------
@app.route('/admin/view_students')
def admin_view_students():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT s.*, u.email
        FROM students s
        JOIN users u ON s.user_id = u.user_id
        ORDER BY s.programme, s.name
    """)

    students = cursor.fetchall()
    conn.close()

    categorized = {
        "MCA": [],
        "MBA": [],
        "B-Tech CS Engineering": [],
        "B-Tech Mechanical Engineering": [],
        "B-Tech E&E Engineering": []
    }

    for student in students:
        prog = student['programme']
        if prog in categorized:
            categorized[prog].append(student)

    return render_template(
        "admin_view_students.html",
        categorized=categorized
    )

    
# ---------------- Edit Student ----------------
@app.route('/admin/edit_student/<int:id>', methods=['GET', 'POST'])
def admin_edit_student(id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        full_name = request.form['full_name']
        contact = request.form['contact']
        register_no = request.form['register_no']
        programme = request.form['programme']
        semester = request.form['semester']

        cursor.execute("""
            UPDATE students
            SET name=?, contact=?, register_no=?,
                programme=?, semester=?
            WHERE student_id=?
        """, (
            full_name, contact, register_no,
            programme, semester, id
        ))

        conn.commit()
        conn.close()

        return redirect(url_for('admin_view_students'))

    cursor.execute("""
        SELECT s.*, u.email, u.password
        FROM students s
        JOIN users u ON s.user_id = u.user_id
        WHERE s.student_id=?
    """, (id,))

    student = cursor.fetchone()
    conn.close()

    return render_template("admin_edit_student.html", student=student)


# ---------------- Delete Student ----------------
@app.route('/admin/delete_student/<int:id>')
def delete_student(id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM users
        WHERE user_id = (
            SELECT user_id FROM students WHERE student_id=?
        )
    """, (id,))

    conn.commit()
    conn.close()

    return redirect(url_for('admin_view_students'))


# ---------------- Manage Faculties ----------------
@app.route('/admin/manage_faculties')
def admin_manage_faculties():
    if 'user_id' in session and session['role'] == 'admin':
        return render_template("admin_manage_faculties.html")
    return redirect('/login')


# ---------------- Add Faculty ----------------
@app.route('/admin/add_faculty', methods=['GET', 'POST'])
def admin_add_faculty():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect('/login')

    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        contact = request.form['contact']
        register_no = request.form['register_no']
        department = request.form['department']
        designation = request.form['designation']
        isHOD = request.form.get('is_hod', 'No')
        password = request.form['password']

        photo = request.files['photo']
        photo_filename = None

        if photo and photo.filename:
            photo_filename = photo.filename
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_filename))

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO users (email, password, role)
            VALUES (?, ?, ?)
        """, (email, password, "faculty"))

        user_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO faculties
            (user_id, name, contact, register_no, department, designation, photo, isHOD)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, full_name, contact, register_no,
              department, designation, photo_filename, isHOD))

        conn.commit()
        conn.close()

        return redirect(url_for('admin_manage_faculties'))

    return render_template("admin_add_faculty.html")


# ---------------- View Faculties ----------------
@app.route('/admin/view_faculties')
def admin_view_faculties():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT f.*, u.email
        FROM faculties f
        JOIN users u ON f.user_id = u.user_id
        ORDER BY f.department, f.name
    """)

    faculties = cursor.fetchall()
    conn.close()

    categorized = {
        "MCA": [],
        "MBA": [],
        "B-Tech CS Engineering": [],
        "B-Tech Mechanical Engineering": [],
        "B-Tech E&E Engineering": []
    }

    for faculty in faculties:
        dept = faculty['department']
        if dept in categorized:
            categorized[dept].append(faculty)

    return render_template(
        "admin_view_faculties.html",
        categorized=categorized
    )


# ---------------- Edit Faculty ----------------
@app.route('/admin/edit_faculty/<int:id>', methods=['GET', 'POST'])
def admin_edit_faculty(id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        full_name = request.form['full_name']
        contact = request.form['contact']
        register_no = request.form['register_no']
        department = request.form['department']
        designation = request.form['designation']
        isHOD = request.form.get('is_hod', 'No')

        photo = request.files.get('photo')

        if photo and photo.filename:
            photo_filename = photo.filename
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_filename))

            cursor.execute("""
                UPDATE faculties
                SET photo=?
                WHERE faculty_id=?
            """, (photo_filename, id))

        cursor.execute("""
            UPDATE faculties
            SET name=?, contact=?, register_no=?,
                department=?, designation=?, isHOD=?
            WHERE faculty_id=?
        """, (
            full_name, contact, register_no,
            department, designation, isHOD, id
        ))

        conn.commit()
        conn.close()

        return redirect(url_for('admin_view_faculties'))

    cursor.execute("""
        SELECT f.*, u.email, u.password
        FROM faculties f
        JOIN users u ON f.user_id = u.user_id
        WHERE f.faculty_id=?
    """, (id,))

    faculty = cursor.fetchone()
    conn.close()

    return render_template("admin_edit_faculty.html", faculty=faculty)


# ---------------- Delete Faculty (cascade safe) ----------------
@app.route('/admin/delete_faculty/<int:id>')
def delete_faculty(id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM users
        WHERE user_id = (SELECT user_id FROM faculties WHERE faculty_id=?)
    """, (id,))

    conn.commit()
    conn.close()

    return redirect(url_for('admin_view_faculties'))


# ---------------- Manage Venues ----------------
@app.route('/admin/manage_venues')
def admin_manage_venues():
    if 'user_id' in session and session['role'] == 'admin':
        return render_template("admin_manage_venues.html")
    return redirect('/login')


# ---------------- Add Venue ----------------
@app.route('/admin/add_venue', methods=['GET', 'POST'])
def admin_add_venue():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect('/login')

    if request.method == 'POST':
        name = request.form['name']
        venue_type = request.form['type']
        department = request.form['department']
        block = request.form['block']
        purpose = request.form['purpose']

        photo = request.files.get('photo')
        photo_filename = None

        if photo and photo.filename:
            photo_filename = photo.filename
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_filename))

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO venues
            (name, type, department, block, photo, purpose)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, venue_type, department, block, photo_filename, purpose))

        conn.commit()
        conn.close()

        return redirect(url_for('admin_manage_venues'))

    return render_template("admin_add_venue.html")


# ---------------- View Venues ----------------
@app.route('/admin/view_venues')
def admin_view_venues():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM venues
        ORDER BY department, name
    """)

    venues = cursor.fetchall()
    conn.close()

    categorized = {
        "Independent": [],
        "MCA": [],
        "MBA": [],
        "B-Tech CS Engineering": [],
        "B-Tech Mechanical Engineering": [],
        "B-Tech E&E Engineering": []
    }

    for v in venues:
        dept = v['department']
        if dept in categorized:
            categorized[dept].append(v)

    return render_template(
        "admin_view_venues.html",
        categorized=categorized
    )


# ---------------- Edit Venue ----------------
@app.route("/admin/edit_venue/<int:venue_id>", methods=["GET", "POST"])
def admin_edit_venue(venue_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM venues WHERE venue_id = ?", (venue_id,))
    venue = cursor.fetchone()

    if request.method == "POST":
        name = request.form["name"]
        vtype = request.form["type"]
        department = request.form["department"]
        block = request.form["block"]
        purpose = request.form["purpose"]

        photo_file = request.files.get("photo")

        if photo_file and photo_file.filename:
            photo_filename = photo_file.filename
            photo_file.save(os.path.join(app.config["UPLOAD_FOLDER"], photo_filename))
        else:
            photo_filename = venue["photo"]

        cursor.execute("""
            UPDATE venues
            SET name = ?, type = ?, department = ?, block = ?, purpose = ?, photo = ?
            WHERE venue_id = ?
        """, (name, vtype, department, block, purpose, photo_filename, venue_id))

        conn.commit()
        conn.close()

        return redirect(url_for("admin_view_venues"))

    conn.close()
    return render_template("admin_edit_venue.html", venue=venue)


# ---------------- Delete Venue ----------------
@app.route("/admin/delete_venue/<int:id>")
def delete_venue(id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect('/login')
    
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM venues WHERE venue_id = ?", (id,))
    
    conn.commit()
    conn.close()

    return redirect(url_for("admin_view_venues"))


# ---------------- Manage Bookings ----------------
@app.route('/admin/manage_bookings')
def admin_manage_bookings():
    if 'user_id' in session and session['role'] == 'admin':
        return render_template("admin_manage_bookings.html")
    return redirect('/login')


# ---------------- Admin Session Requests ----------------
@app.route('/admin/session_requests')
def admin_session_requests():

    if 'user_id' not in session or session['role'] != 'admin':
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT b.booking_id,
               f.name AS faculty_name,
               v.name AS venue_name,
               b.date,
               b.start_time,
               b.end_time,
               b.purpose,
               b.target_batch,
               b.status
        FROM bookings b
        JOIN faculties f ON b.faculty_id = f.faculty_id
        JOIN venues v ON b.venue_id = v.venue_id
        WHERE b.booking_type='session'
        ORDER BY b.booking_id DESC
    """)

    requests = cursor.fetchall()

    formatted_requests = []

    for r in requests:
        formatted_date = datetime.strptime(r['date'], "%Y-%m-%d").strftime("%d-%b-%Y")
        formatted_start = datetime.strptime(r['start_time'], "%H:%M").strftime("%I:%M %p")
        formatted_end = datetime.strptime(r['end_time'], "%H:%M").strftime("%I:%M %p")

        r = dict(r)
        r['date'] = formatted_date
        r['start_time'] = formatted_start
        r['end_time'] = formatted_end

        formatted_requests.append(r)

    conn.close()

    return render_template("admin_session_requests.html", requests=formatted_requests)


# ---------------- Admin Event Requests ----------------
@app.route('/admin/event_requests')
def admin_event_requests():

    if 'user_id' not in session or session['role'] != 'admin':
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT b.booking_id,
               f.name AS faculty_name,
               v.name AS venue_name,
               b.date,
               b.start_time,
               b.end_time,
               b.purpose,
               b.target_batch,
               b.status
        FROM bookings b
        JOIN faculties f ON b.faculty_id = f.faculty_id
        JOIN venues v ON b.venue_id = v.venue_id
        WHERE b.booking_type='event'
        ORDER BY b.booking_id DESC
    """)

    requests = cursor.fetchall()

    formatted_requests = []

    for r in requests:
        formatted_date = datetime.strptime(r['date'], "%Y-%m-%d").strftime("%d-%b-%Y")
        formatted_start = datetime.strptime(r['start_time'], "%H:%M").strftime("%I:%M %p")
        formatted_end = datetime.strptime(r['end_time'], "%H:%M").strftime("%I:%M %p")

        r = dict(r)
        r['date'] = formatted_date
        r['start_time'] = formatted_start
        r['end_time'] = formatted_end

        formatted_requests.append(r)

    conn.close()

    return render_template("admin_event_requests.html", requests=formatted_requests)


# ---------------- Approve Booking ----------------
@app.route('/admin/approve_booking/<int:booking_id>')
def approve_booking(booking_id):

    if 'user_id' not in session or session['role'] != 'admin':
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE bookings
        SET status='approved'
        WHERE booking_id=?
    """, (booking_id,))

    conn.commit()
    conn.close()

    return redirect(request.referrer)


# ---------------- Reject Booking ----------------
@app.route('/admin/reject_booking/<int:booking_id>')
def reject_booking(booking_id):

    if 'user_id' not in session or session['role'] != 'admin':
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE bookings
        SET status='rejected'
        WHERE booking_id=?
    """, (booking_id,))

    conn.commit()
    conn.close()

    return redirect(request.referrer)


# ---------------- Manage Events ----------------
@app.route('/admin/manage_events')
def admin_manage_events():
    if 'user_id' in session and session['role'] == 'admin':
        return render_template("admin_manage_events.html")
    return redirect('/login')


# ---------------- Add Event ----------------
@app.route('/admin/add_event', methods=['GET','POST'])
def admin_add_event():

    if 'user_id' not in session or session['role'] != 'admin':
        return redirect('/login')

    if request.method == 'POST':

        event_title = request.form['event_title']
        organizer = request.form['organizer']
        description = request.form['description']
        start_date = request.form['start_date']
        end_date = request.form['end_date']

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO events
            (event_title, organizer, description, start_date, end_date)
            VALUES (?, ?, ?, ?, ?)
        """, (event_title, organizer, description, start_date, end_date))

        conn.commit()
        conn.close()

        return redirect('/admin/manage_events')

    return render_template("admin_add_event.html")


# ---------------- View Events ----------------
@app.route('/admin/view_events')
def admin_view_events():

    if 'user_id' not in session or session['role'] != 'admin':
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM events
        ORDER BY start_date DESC
    """)

    events = cursor.fetchall()

    formatted_events = []

    for e in events:

        e = dict(e)

        formatted_start = datetime.strptime(e['start_date'], "%Y-%m-%d").strftime("%d-%b-%Y")
        formatted_end = datetime.strptime(e['end_date'], "%Y-%m-%d").strftime("%d-%b-%Y")

        e['start_date'] = formatted_start
        e['end_date'] = formatted_end

        formatted_events.append(e)

    conn.close()

    return render_template("admin_view_events.html", events=formatted_events)


# ---------------- Edit Event ----------------
@app.route('/admin_edit_event/<int:id>', methods=['GET', 'POST'])
def admin_edit_event(id):
    
    conn = get_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        title = request.form['event_title']
        organizer = request.form['organizer']
        desc = request.form['description']
        start = request.form['start_date']
        end = request.form['end_date']

        cursor.execute("""
            UPDATE events
            SET event_title=?, organizer=?, description=?, start_date=?, end_date=?
            WHERE event_id=?
        """, (title, organizer, desc, start, end, id))

        conn.commit()
        conn.close()
        return redirect(url_for('admin_view_events'))

    cursor.execute("SELECT * FROM events WHERE event_id=?", (id,))
    event = cursor.fetchone()
    conn.close()

    return render_template('admin_edit_event.html', event=event)


# ---------------- Delete Event ----------------
@app.route('/delete_event/<int:id>')
def delete_event(id):
    
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM events WHERE event_id = ?", (id,))
    conn.commit()
    conn.close()

    return redirect(url_for('admin_view_events'))


# ---------------- FACULTY DASHBOARD ----------------
@app.route('/faculty_dashboard')
def faculty_dashboard():
    if 'user_id' not in session or session['role'] != 'faculty':
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT faculty_id, name, department, photo
        FROM faculties
        WHERE user_id = ?
    """, (session['user_id'],))
    faculty = cursor.fetchone()

    if not faculty:
        conn.close()
        return redirect('/login')

    faculty_id = faculty['faculty_id']
    faculty_name = faculty['name']
    department = faculty['department']
    faculty_photo = faculty['photo']

    cursor.execute("""
        SELECT COUNT(*)
        FROM students
        WHERE programme = ?
    """, (department,))
    total_students = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM bookings
        WHERE faculty_id = ?
    """, (faculty_id,))
    total_bookings = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM venues
        WHERE department = ?
        OR department = 'Independent'
    """, (department,))
    total_venues = cursor.fetchone()[0]

    cursor.execute("""
        SELECT b.*, v.name AS venue_name
        FROM bookings b
        JOIN venues v ON b.venue_id = v.venue_id
        WHERE b.faculty_id = ?
        ORDER BY b.booking_id DESC
        LIMIT 4
    """, (faculty_id,))
    recent_bookings = cursor.fetchall()
    
    formatted_bookings = []

    for b in recent_bookings:
        booking = dict(b)

        booking['date'] = datetime.strptime(booking['date'], "%Y-%m-%d").strftime("%d-%b-%Y")
        booking['start_time'] = datetime.strptime(booking['start_time'], "%H:%M").strftime("%I:%M %p")
        booking['end_time'] = datetime.strptime(booking['end_time'], "%H:%M").strftime("%I:%M %p")

        formatted_bookings.append(booking)

    conn.close()

    return render_template(
        "dash_faculty.html",
        faculty_name=faculty_name,
        faculty_photo=faculty_photo,
        total_students=total_students,
        total_bookings=total_bookings,
        total_venues=total_venues,
        recent_bookings=formatted_bookings
    )


# ---------------- View Students ----------------
@app.route('/faculty/view_students')
def faculty_view_students():

    if 'user_id' not in session or session['role'] != 'faculty':
        return redirect('/login')

    search = request.args.get('search', '').strip()
    semester_filter = request.args.get('semester', 'Show All')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT department
        FROM faculties
        WHERE user_id = ?
    """, (session['user_id'],))

    faculty = cursor.fetchone()

    if not faculty:
        conn.close()
        return redirect('/faculty_dashboard')

    faculty_dept = faculty['department']

    query = """
        SELECT s.*, u.email
        FROM students s
        JOIN users u ON s.user_id = u.user_id
        WHERE s.programme = ?
    """
    params = [faculty_dept]

    if search:
        query += " AND s.name LIKE ?"
        params.append(f"%{search}%")

    if semester_filter != "Show All":
        query += " AND s.semester = ?"
        params.append(semester_filter)

    query += " ORDER BY s.name"

    cursor.execute(query, params)
    students = cursor.fetchall()

    conn.close()

    if faculty_dept in ["MCA", "MBA"]:
        semester_options = ["Show All", "S1", "S2", "S3", "S4"]
    else:
        semester_options = ["Show All", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]

    return render_template(
        "faculty_view_students.html",
        students=students,
        semester_options=semester_options,
        selected_semester=semester_filter,
        search=search,
        faculty_dept=faculty_dept
    )
    

# ---------------- Book Session ----------------
@app.route('/faculty/book_session')
def faculty_book_session():

    if 'user_id' not in session or session['role'] != 'faculty':
        return redirect(url_for('login'))

    conn = get_connection()
    cursor = conn.cursor()

    faculty_user_id = session['user_id']

    cursor.execute("""
        SELECT faculty_id, department
        FROM faculties
        WHERE user_id = ?
    """, (faculty_user_id,))
    
    faculty = cursor.fetchone()

    if not faculty:
        flash("Faculty record not found", "danger")
        return redirect(url_for('login'))

    faculty_id = faculty['faculty_id']
    faculty_dept = faculty['department']

    cursor.execute("""
        SELECT *
        FROM venues
        WHERE LOWER(TRIM(purpose)) IN ('hybrid', 'session only')
        AND department = ?
        ORDER BY name
    """, (faculty_dept,))

    venues = cursor.fetchall()

    cursor.execute("""
        SELECT venue_id, status
        FROM bookings
        WHERE status IN ('requested','approved')
    """)

    active = cursor.fetchall()

    booked_map = {}
    for a in active:
        booked_map[a['venue_id']] = a['status']

    conn.close()

    session['department'] = faculty_dept
    
    return render_template(
        "faculty_book_session.html",
        venues=venues,
        booked_map=booked_map,
        department=session.get('department')
    )
    

# ---------------- Book Session - Request ----------------
@app.route('/faculty/session_request/<int:venue_id>', methods=['POST'])
def faculty_session_request(venue_id):
    if 'user_id' not in session or session['role'] != 'faculty':
        return jsonify({'status': 'error', 'message': 'Unauthorized access'})

    date = request.form['date']
    start_time = request.form['start_time']
    end_time = request.form['end_time']
    purpose = request.form['purpose']
    target_batch = request.form['target_batch']

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT faculty_id, name
        FROM faculties
        WHERE user_id = ?
    """, (session['user_id'],))
    faculty = cursor.fetchone()
    faculty_id = faculty['faculty_id']
    faculty_name = faculty['name']

    cursor.execute("SELECT name FROM venues WHERE venue_id = ?", (venue_id,))
    venue_name = cursor.fetchone()['name']

    cursor.execute("""
        SELECT b.start_time, b.end_time, b.status, b.target_batch, b.purpose, f.name AS faculty_name
        FROM bookings b
        JOIN faculties f ON b.faculty_id = f.faculty_id
        WHERE b.venue_id = ?
          AND b.date = ?
          AND b.status IN ('requested','approved')
          AND (? < b.end_time AND ? > b.start_time)
    """, (venue_id, date, start_time, end_time))
    conflict = cursor.fetchone()
            
    if conflict:

        formatted_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d-%b-%Y")
        start_time = datetime.strptime(conflict['start_time'], "%H:%M").strftime("%I:%M %p")
        end_time = datetime.strptime(conflict['end_time'], "%H:%M").strftime("%I:%M %p")

        if conflict['status'] == 'requested':
            message = f"{venue_name} is already requested by {conflict['faculty_name']} on {formatted_date} from {start_time} - {end_time} for {conflict['target_batch']} ({conflict['purpose']})."
        else:
            message = f"{venue_name} is already booked by {conflict['faculty_name']} on {formatted_date} from {start_time} - {end_time} for {conflict['target_batch']} ({conflict['purpose']})."
            
        conn.close()
        return jsonify({'status': 'conflict', 'message': message})

    cursor.execute("""
        INSERT INTO bookings
        (faculty_id, venue_id, booking_type, date, start_time, end_time, purpose, target_batch, status)
        VALUES (?, ?, 'session', ?, ?, ?, ?, ?, 'requested')
    """, (faculty_id, venue_id, date, start_time, end_time, purpose, target_batch))

    conn.commit()
    conn.close()

    return jsonify({'status': 'success', 'message': 'Booking request has been forwarded to Admin'})


# ---------------- Book Event ----------------
@app.route('/faculty/book_event')
def faculty_book_event():

    if 'user_id' not in session or session['role'] != 'faculty':
        return redirect(url_for('login'))

    conn = get_connection()
    cursor = conn.cursor()

    faculty_user_id = session['user_id']

    cursor.execute("""
        SELECT faculty_id, department
        FROM faculties
        WHERE user_id = ?
    """, (faculty_user_id,))
    
    faculty = cursor.fetchone()

    if not faculty:
        flash("Faculty record not found", "danger")
        return redirect(url_for('login'))

    faculty_id = faculty['faculty_id']
    faculty_dept = faculty['department']

    cursor.execute("""
        SELECT *
        FROM venues
        WHERE 
            (LOWER(TRIM(purpose)) = 'hybrid' AND department = ?)
            OR
            (LOWER(TRIM(purpose)) = 'event only' AND LOWER(TRIM(department)) = 'independent')
        ORDER BY name
    """, (faculty_dept,))

    venues = cursor.fetchall()

    cursor.execute("""
        SELECT venue_id, status
        FROM bookings
        WHERE status IN ('requested','approved')
    """)

    active = cursor.fetchall()

    booked_map = {}
    for a in active:
        booked_map[a['venue_id']] = a['status']

    conn.close()

    return render_template(
        "faculty_book_event.html",
        venues=venues,
        booked_map=booked_map,
        department=faculty_dept
    )
    

# ---------------- Book Event - Request ----------------
@app.route('/faculty/event_request/<int:venue_id>', methods=['POST'])
def faculty_event_request(venue_id):

    if 'user_id' not in session or session['role'] != 'faculty':
        return jsonify({'status': 'error', 'message': 'Unauthorized access'})

    date = request.form['date']
    start_time = request.form['start_time']
    end_time = request.form['end_time']
    purpose = request.form['purpose']
    target_batch = request.form['target_batch']

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT faculty_id, name
        FROM faculties
        WHERE user_id = ?
    """, (session['user_id'],))

    faculty = cursor.fetchone()
    faculty_id = faculty['faculty_id']
    faculty_name = faculty['name']

    cursor.execute("""
        SELECT name
        FROM venues
        WHERE venue_id = ?
    """, (venue_id,))

    venue_name = cursor.fetchone()['name']

    cursor.execute("""
        SELECT b.start_time, b.end_time, b.status, b.target_batch, b.purpose, f.name AS faculty_name
        FROM bookings b
        JOIN faculties f ON b.faculty_id = f.faculty_id
        WHERE b.venue_id = ?
        AND b.date = ?
        AND b.status IN ('requested','approved')
        AND (? < b.end_time AND ? > b.start_time)
    """, (venue_id, date, start_time, end_time))

    conflict = cursor.fetchone()

    if conflict:

        formatted_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d-%b-%Y")
        start_time = datetime.strptime(conflict['start_time'], "%H:%M").strftime("%I:%M %p")
        end_time = datetime.strptime(conflict['end_time'], "%H:%M").strftime("%I:%M %p")

        if conflict['status'] == 'requested':
            message = f"{venue_name} is already requested by {conflict['faculty_name']} on {formatted_date} from {start_time} - {end_time} for {conflict['target_batch']} ({conflict['purpose']})."
        else:
            message = f"{venue_name} is already booked by {conflict['faculty_name']} on {formatted_date} from {start_time} - {end_time} for {conflict['target_batch']} ({conflict['purpose']})."

        conn.close()
        return jsonify({'status': 'conflict', 'message': message})

    cursor.execute("""
        INSERT INTO bookings
        (faculty_id, venue_id, booking_type, date, start_time, end_time, purpose, target_batch, status)
        VALUES (?, ?, 'event', ?, ?, ?, ?, ?, 'requested')
    """, (
        faculty_id,
        venue_id,
        date,
        start_time,
        end_time,
        purpose,
        target_batch
    ))

    conn.commit()
    conn.close()

    return jsonify({
        'status': 'success',
        'message': 'Booking request has been forwarded to Admin'
    })


# ---------------- View Bookings ----------------
@app.route('/faculty/view_bookings')
def faculty_view_bookings():

    if 'user_id' not in session or session['role'] != 'faculty':
        return redirect(url_for('login'))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT faculty_id
        FROM faculties
        WHERE user_id = ?
    """, (session['user_id'],))

    faculty = cursor.fetchone()

    if not faculty:
        conn.close()
        return redirect(url_for('faculty_dashboard'))

    faculty_id = faculty['faculty_id']

    cursor.execute("""
        SELECT 
            b.booking_id,
            b.booking_type,
            b.date,
            b.start_time,
            b.end_time,
            b.status,
            v.name AS venue_name,
            v.block
        FROM bookings b
        JOIN venues v ON b.venue_id = v.venue_id
        WHERE b.faculty_id = ?
        ORDER BY b.booking_id DESC
    """, (faculty_id,))

    bookings = cursor.fetchall()

    formatted_bookings = []

    for b in bookings:
        booking = dict(b)

        booking['date'] = datetime.strptime(booking['date'], "%Y-%m-%d").strftime("%d-%b-%Y")
        booking['start_time'] = datetime.strptime(booking['start_time'], "%H:%M").strftime("%I:%M %p")
        booking['end_time'] = datetime.strptime(booking['end_time'], "%H:%M").strftime("%I:%M %p")

        formatted_bookings.append(booking)

    conn.close()

    return render_template(
        "faculty_view_bookings.html",
        bookings=formatted_bookings
    )
    
    
# ---------------- View Events ----------------
@app.route('/faculty/view_events')
def faculty_view_events():

    if 'user_id' not in session or session['role'] != 'faculty':
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM events
        ORDER BY start_date DESC
    """)

    events = cursor.fetchall()
    conn.close()

    today = datetime.now().date()

    live_events = []
    upcoming_events = []
    past_events = []

    for e in events:

        e = dict(e)

        start = datetime.strptime(e['start_date'], "%Y-%m-%d").date()
        end = datetime.strptime(e['end_date'], "%Y-%m-%d").date()

        e['start_date'] = start.strftime("%d-%b-%Y")
        e['end_date'] = end.strftime("%d-%b-%Y")

        if start <= today <= end:
            live_events.append(e)

        elif today < start:
            upcoming_events.append(e)

        else:
            past_events.append(e)

    return render_template(
        "faculty_view_events.html",
        live_events=live_events,
        upcoming_events=upcoming_events,
        past_events=past_events
    )
    
    
# ---------------- Faculty Chatspace ----------------
@app.route('/faculty/chatspace')
def faculty_chatspace():
    if 'user_id' not in session or session['role'] != 'faculty':
        return redirect('/login')

    search = request.args.get('search', '').strip()
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT faculty_id FROM faculties WHERE user_id = ?", (session['user_id'],))
    faculty = cursor.fetchone()
    faculty_id = faculty['faculty_id']

    if search:
        cursor.execute("""
            SELECT s.student_id, s.name, s.semester, s.register_no,
            SUM(CASE WHEN c.is_read = 0 AND c.sender_role='student' THEN 1 ELSE 0 END) AS unread_count
            FROM chats c
            JOIN students s ON c.student_id = s.student_id
            WHERE c.faculty_id = ?
            AND (s.name LIKE ? OR s.register_no LIKE ? OR s.semester LIKE ?)
            GROUP BY s.student_id
            ORDER BY MAX(c.sent_time) DESC
        """, (faculty_id, f"%{search}%", f"%{search}%", f"%{search}%"))
    else:
        cursor.execute("""
            SELECT s.student_id, s.name, s.semester, s.register_no,
                SUM(CASE WHEN c.is_read = 0 AND c.sender_role='student' THEN 1 ELSE 0 END) AS unread_count
            FROM chats c
            JOIN students s ON s.student_id = c.student_id
            WHERE c.faculty_id = ?
            GROUP BY s.student_id
            ORDER BY MAX(c.sent_time) DESC
        """, (faculty_id,))

    chats = cursor.fetchall()
    conn.close()

    return render_template("faculty_chatspace.html", chats=chats, search=search)
    

# ---------------- Faculty Chatpage ----------------
@app.route('/faculty/chatpage/<int:student_id>', methods=['GET','POST'])
def faculty_chatpage(student_id):
    if 'user_id' not in session or session['role'] != 'faculty':
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT faculty_id FROM faculties WHERE user_id = ?", (session['user_id'],))
    faculty_id = cursor.fetchone()['faculty_id']

    if request.method == 'POST':
        message = request.form['message']
        cursor.execute("""
            INSERT INTO chats (faculty_id, student_id, sender_role, message, is_read)
            VALUES (?, ?, 'faculty', ?, 0)
        """, (faculty_id, student_id, message))
        conn.commit()

    cursor.execute("""
        UPDATE chats
        SET is_read = 1
        WHERE faculty_id = ? AND student_id = ? AND sender_role = 'student' AND is_read = 0
    """, (faculty_id, student_id))
    conn.commit()

    cursor.execute("SELECT name FROM students WHERE student_id = ?", (student_id,))
    student = cursor.fetchone()

    cursor.execute("""
        SELECT *
        FROM chats
        WHERE faculty_id = ? AND student_id = ?
        ORDER BY sent_time
    """, (faculty_id, student_id))
    messages = cursor.fetchall()
    conn.close()

    return render_template(
        "faculty_chatpage.html",
        messages=messages,
        student=student,
        student_id=student_id
    )


# ---------------- STUDENT DASHBOARD ----------------
@app.route('/student_dashboard')
def student_dashboard():

    if 'user_id' not in session or session['role'] != 'student':
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT s.name, s.programme, s.semester
        FROM students s
        WHERE s.user_id = ?
    """, (session['user_id'],))

    student = cursor.fetchone()
    student_dept = student['programme']

    cursor.execute("""
        SELECT COUNT(*)
        FROM faculties
        WHERE department = ?
    """, (student_dept,))
    total_faculties = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM bookings b
        JOIN faculties f ON b.faculty_id = f.faculty_id
        WHERE f.department = ?
        AND b.status='approved'
        AND (b.target_batch=? OR b.target_batch='Everyone')
    """, (student_dept, student['semester']))
    total_schedules = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*)
        FROM venues
        WHERE department = ?
        OR department = 'Independent'
    """, (student_dept,))
    total_venues = cursor.fetchone()[0]

    cursor.execute("""
        SELECT v.name, b.booking_type, b.date, b.start_time, b.end_time
        FROM bookings b
        JOIN venues v ON b.venue_id = v.venue_id
        JOIN faculties f ON b.faculty_id = f.faculty_id
        WHERE f.department = ?
        AND b.status='approved'
        AND (b.target_batch=? OR b.target_batch='Everyone')
        ORDER BY b.date DESC
        LIMIT 4
    """, (student_dept, student['semester']))
    recent_schedules = cursor.fetchall()
    
    formatted_schedules = []

    for r in recent_schedules:
        schedule = dict(r)

        schedule['date'] = datetime.strptime(schedule['date'], "%Y-%m-%d").strftime("%d-%b-%Y")
        schedule['start_time'] = datetime.strptime(schedule['start_time'], "%H:%M").strftime("%I:%M %p")
        schedule['end_time'] = datetime.strptime(schedule['end_time'], "%H:%M").strftime("%I:%M %p")

        formatted_schedules.append(schedule)

    conn.close()

    return render_template(
        "dash_student.html",
        student=student,
        total_faculties=total_faculties,
        total_venues=total_venues,
        total_schedules=total_schedules,
        recent_schedules=formatted_schedules
    )
    

# ---------------- View Faculties ----------------
@app.route('/student/view_faculties')
def student_view_faculties():

    if 'user_id' not in session or session['role'] != 'student':
        return redirect('/login')

    search = request.args.get('search', '').strip()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT programme
        FROM students
        WHERE user_id = ?
    """, (session['user_id'],))

    student = cursor.fetchone()
    student_dept = student['programme']

    if search:

        cursor.execute("""
            SELECT f.faculty_id, f.name, f.contact, f.register_no, f.designation, f.photo, f.isHOD, u.email
            FROM faculties f
            JOIN users u ON f.user_id = u.user_id
            WHERE f.department = ?
            AND (
                f.name LIKE ?
                OR f.register_no LIKE ?
                OR f.designation LIKE ?
            )
            ORDER BY f.name ASC
        """, (student_dept, f"%{search}%", f"%{search}%", f"%{search}%"))

    else:

        cursor.execute("""
            SELECT f.faculty_id, f.name, f.contact, f.register_no, f.designation, f.photo, f.isHOD, u.email
            FROM faculties f
            JOIN users u ON f.user_id = u.user_id
            WHERE f.department = ?
            ORDER BY f.name ASC
        """, (student_dept,))

    faculties = cursor.fetchall()

    conn.close()

    return render_template(
        "student_view_faculties.html",
        faculties=faculties,
        student_dept=student_dept,
        search=search
    )
    
    
# ---------------- Session Schedule ----------------
@app.route('/student/session_schedule')
def student_session_schedule():

    if 'user_id' not in session or session['role'] != 'student':
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT programme, semester
        FROM students
        WHERE user_id=?
    """, (session['user_id'],))

    student = cursor.fetchone()
    semester = student['semester']
    department = student['programme']

    cursor.execute("""
        SELECT f.name AS faculty_name,
               v.name AS venue_name,
               b.date,
               b.start_time,
               b.end_time,
               b.purpose
        FROM bookings b
        JOIN faculties f ON b.faculty_id = f.faculty_id
        JOIN venues v ON b.venue_id = v.venue_id
        WHERE b.booking_type='session'
        AND b.status='approved'
        AND b.target_batch=?
        AND f.department=?
        ORDER BY b.date DESC
    """, (semester, department))

    sessions = cursor.fetchall()

    live_sessions = []
    upcoming_sessions = []
    past_sessions = []

    now = datetime.now()

    for s in sessions:

        start_dt = datetime.strptime(s['date'] + " " + s['start_time'], "%Y-%m-%d %H:%M")
        end_dt = datetime.strptime(s['date'] + " " + s['end_time'], "%Y-%m-%d %H:%M")

        session_dict = dict(s)

        session_dict['date'] = datetime.strptime(s['date'], "%Y-%m-%d").strftime("%d-%b-%Y")
        session_dict['start_time'] = datetime.strptime(s['start_time'], "%H:%M").strftime("%I:%M %p")
        session_dict['end_time'] = datetime.strptime(s['end_time'], "%H:%M").strftime("%I:%M %p")

        if start_dt <= now <= end_dt:
            live_sessions.append(session_dict)

        elif now < start_dt:
            upcoming_sessions.append(session_dict)

        else:
            past_sessions.append(session_dict)

    conn.close()

    return render_template(
        "student_session_schedule.html",
        live_sessions=live_sessions,
        upcoming_sessions=upcoming_sessions,
        past_sessions=past_sessions
    )


# ---------------- Event Schedule ----------------
@app.route('/student/event_schedule')
def student_event_schedule():

    if 'user_id' not in session or session['role'] != 'student':
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT programme, semester
        FROM students
        WHERE user_id=?
    """, (session['user_id'],))

    student = cursor.fetchone()
    semester = student['semester']
    department = student['programme']

    cursor.execute("""
        SELECT f.name AS faculty_name,
               v.name AS venue_name,
               b.date,
               b.start_time,
               b.end_time,
               b.purpose
        FROM bookings b
        JOIN faculties f ON b.faculty_id = f.faculty_id
        JOIN venues v ON b.venue_id = v.venue_id
        WHERE b.booking_type='event'
        AND b.status='approved'
        AND f.department = ?
        AND (b.target_batch=? OR b.target_batch='Everyone')
        ORDER BY b.date DESC
    """, (department, semester))

    events = cursor.fetchall()

    live_events = []
    upcoming_events = []
    past_events = []

    now = datetime.now()

    for e in events:

        start_dt = datetime.strptime(e['date'] + " " + e['start_time'], "%Y-%m-%d %H:%M")
        end_dt = datetime.strptime(e['date'] + " " + e['end_time'], "%Y-%m-%d %H:%M")

        event = dict(e)

        event['date'] = datetime.strptime(e['date'], "%Y-%m-%d").strftime("%d-%b-%Y")
        event['start_time'] = datetime.strptime(e['start_time'], "%H:%M").strftime("%I:%M %p")
        event['end_time'] = datetime.strptime(e['end_time'], "%H:%M").strftime("%I:%M %p")

        if start_dt <= now <= end_dt:
            live_events.append(event)

        elif now < start_dt:
            upcoming_events.append(event)

        else:
            past_events.append(event)

    conn.close()

    return render_template(
        "student_event_schedule.html",
        live_events=live_events,
        upcoming_events=upcoming_events,
        past_events=past_events
    )
    
    
# ---------------- View Events ----------------
@app.route('/student/view_events')
def student_view_events():

    if 'user_id' not in session or session['role'] != 'student':
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM events
        ORDER BY start_date DESC
    """)

    events = cursor.fetchall()
    conn.close()

    today = datetime.now().date()

    live_events = []
    upcoming_events = []
    past_events = []

    for e in events:

        e = dict(e)

        start = datetime.strptime(e['start_date'], "%Y-%m-%d").date()
        end = datetime.strptime(e['end_date'], "%Y-%m-%d").date()

        # format for display
        e['start_date'] = start.strftime("%d-%b-%Y")
        e['end_date'] = end.strftime("%d-%b-%Y")

        if start <= today <= end:
            live_events.append(e)

        elif today < start:
            upcoming_events.append(e)

        else:
            past_events.append(e)

    return render_template(
        "student_view_events.html",
        live_events=live_events,
        upcoming_events=upcoming_events,
        past_events=past_events
    )
    

# ---------------- Student Chatspace ----------------
@app.route('/student/chatspace')
def student_chatspace():
    if 'user_id' not in session or session['role'] != 'student':
        return redirect('/login')

    search = request.args.get('search', '').strip()
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT student_id FROM students WHERE user_id = ?", (session['user_id'],))
    student = cursor.fetchone()
    student_id = student['student_id']

    if search:
        cursor.execute("""
            SELECT f.faculty_id, f.name, f.designation, f.register_no, f.isHOD,
            SUM(CASE WHEN c.is_read = 0 AND c.sender_role='faculty' THEN 1 ELSE 0 END) AS unread_count
            FROM chats c
            JOIN faculties f ON c.faculty_id = f.faculty_id
            WHERE c.student_id = ?
            AND (f.name LIKE ? OR f.register_no LIKE ? OR f.designation LIKE ?)
            GROUP BY f.faculty_id
            ORDER BY MAX(c.sent_time) DESC
        """, (student_id, f"%{search}%", f"%{search}%", f"%{search}%"))
    else:
        cursor.execute("""
            SELECT f.faculty_id, f.name, f.designation, f.register_no, f.isHOD,
                SUM(CASE WHEN c.is_read = 0 AND c.sender_role='faculty' THEN 1 ELSE 0 END) AS unread_count
            FROM chats c
            JOIN faculties f ON f.faculty_id = c.faculty_id
            WHERE c.student_id = ?
            GROUP BY f.faculty_id
            ORDER BY MAX(c.sent_time) DESC
        """, (student_id,))

    chats = cursor.fetchall()
    conn.close()

    return render_template("student_chatspace.html", chats=chats, search=search)
    
    
# ---------------- Student Chatpage ----------------
@app.route('/student/chatpage/<int:faculty_id>', methods=['GET','POST'])
def student_chatpage(faculty_id):
    if 'user_id' not in session or session['role'] != 'student':
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT student_id FROM students WHERE user_id = ?", (session['user_id'],))
    student_id = cursor.fetchone()['student_id']

    if request.method == 'POST':
        message = request.form['message']
        cursor.execute("""
            INSERT INTO chats (faculty_id, student_id, sender_role, message, is_read)
            VALUES (?, ?, 'student', ?, 0)
        """, (faculty_id, student_id, message))
        conn.commit()

    cursor.execute("""
        UPDATE chats
        SET is_read = 1
        WHERE faculty_id = ? AND student_id = ? AND sender_role = 'faculty' AND is_read = 0
    """, (faculty_id, student_id))
    conn.commit()

    cursor.execute("SELECT name FROM faculties WHERE faculty_id = ?", (faculty_id,))
    faculty = cursor.fetchone()

    cursor.execute("""
        SELECT *
        FROM chats
        WHERE faculty_id = ? AND student_id = ?
        ORDER BY sent_time
    """, (faculty_id, student_id))
    messages = cursor.fetchall()
    conn.close()

    return render_template(
        "student_chatpage.html",
        messages=messages,
        faculty=faculty,
        faculty_id=faculty_id
    )


# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# ---------------- RUN APP ----------------
if __name__ == "__main__":
    app.run(debug=True)