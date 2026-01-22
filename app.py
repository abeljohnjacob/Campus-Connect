from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# ---------------- HOME / LANDING PAGE ----------------
@app.route("/")
def index():
    return render_template("index.html")


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")  # ignored for demo

        # -------- TEMPORARY ROLE-BASED LOGIC --------
        if email == "student@test.com":
            return redirect(url_for("student_dashboard"))
        elif email == "teacher@test.com":
            return redirect(url_for("teacher_dashboard"))
        elif email == "admin@test.com":
            return redirect(url_for("admin_dashboard"))
        else:
            return "Invalid demo user. Try student@test.com / teacher@test.com / admin@test.com"

    return render_template("login.html")


# ---------------- REGISTER ----------------
@app.route("/register")
def register():
    return render_template("register.html")


# ---------------- STUDENT DASHBOARD ----------------
@app.route("/student/dashboard")
def student_dashboard():
    return render_template("dash_student.html")


# ---------------- TEACHER DASHBOARD ----------------
@app.route("/teacher/dashboard")
def teacher_dashboard():
    return render_template("dash_teacher.html")


# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin/dashboard")
def admin_dashboard():
    return render_template("dash_admin.html")


# ---------------- RUN APP ----------------
if __name__ == "__main__":
    app.run(debug=True)
