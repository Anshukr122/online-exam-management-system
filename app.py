"""
Online Examination Management System (OEMS)
Flask Backend — Fully Fixed & Production-Ready
=========================================================
FIXES vs original:
  1. /exams and /results routes now exist and dispatch by role
  2. Sidebar href="#" links replaced with real url_for() calls
  3. role_required() now accepts *roles (multiple allowed)
  4. sqlite3.IntegrityError import fixed
  5. Delete routes use POST (security fix)
  6. Missing exams.html / results.html templates created
  7. Teacher dashboard stats enriched
"""

import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import models
from functools import wraps

app = Flask(__name__)
app.secret_key = 'oems_super_secret_key_change_in_production_2024'

# Initialise DB tables + seed data on startup
models.init_db()


# ─────────────────────────────────────────────────────────────────
# Decorators
# ─────────────────────────────────────────────────────────────────

def login_required(f):
    """Redirect to login if not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    """Allow access only to the listed roles. Usage: @role_required('admin','teacher')"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get('user_role') not in roles:
                flash("You don't have permission to view that page.", "danger")
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorator


# ─────────────────────────────────────────────────────────────────
# Auth Routes
# ─────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        conn = models.get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id']   = user['id']
            session['user_name'] = user['name']
            session['user_role'] = user['role']
            flash(f'Welcome back, {user["name"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name         = request.form.get('name', '').strip()
        email        = request.form.get('email', '').strip()
        password     = request.form.get('password', '')
        role         = request.form.get('role', 'student')
        security_pin = request.form.get('security_pin', '')

        if not all([name, email, password, security_pin]):
            flash('All fields are required.', 'danger')
            return render_template('register.html')

        conn = models.get_db_connection()
        try:
            conn.execute(
                'INSERT INTO users (name, email, password, role, security_pin) VALUES (?, ?, ?, ?, ?)',
                (name, email, generate_password_hash(password), role, security_pin)
            )
            conn.commit()
            flash('Account created! Please sign in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('That email is already registered.', 'danger')
        finally:
            conn.close()

    return render_template('register.html')


@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email        = request.form.get('email', '').strip()
        security_pin = request.form.get('security_pin', '')
        new_password = request.form.get('new_password', '')

        conn = models.get_db_connection()
        user = conn.execute(
            'SELECT * FROM users WHERE email = ? AND security_pin = ?',
            (email, security_pin)
        ).fetchone()

        if user:
            conn.execute('UPDATE users SET password = ? WHERE id = ?',
                         (generate_password_hash(new_password), user['id']))
            conn.commit()
            conn.close()
            flash('Password reset! Please sign in.', 'success')
            return redirect(url_for('login'))
        else:
            conn.close()
            flash('Invalid email or security PIN.', 'danger')

    return render_template('forgot_password.html')


@app.route('/logout')
def logout():
    name = session.get('user_name', 'User')
    session.clear()
    flash(f'Goodbye, {name}!', 'info')
    return redirect(url_for('login'))


# ─────────────────────────────────────────────────────────────────
# Dashboard  (role-aware)
# ─────────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    conn = models.get_db_connection()
    role = session.get('user_role')

    if role == 'admin':
        stats = {
            'students': conn.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0],
            'teachers': conn.execute("SELECT COUNT(*) FROM users WHERE role='teacher'").fetchone()[0],
            'exams':    conn.execute("SELECT COUNT(*) FROM exams").fetchone()[0],
            'results':  conn.execute("SELECT COUNT(*) FROM results").fetchone()[0],
        }
        recent_results = conn.execute('''
            SELECT r.*, e.title AS exam_title, u.name AS student_name
            FROM results r
            JOIN exams e ON r.exam_id   = e.id
            JOIN users u ON r.student_id = u.id
            ORDER BY r.date_taken DESC LIMIT 6
        ''').fetchall()
        conn.close()
        return render_template('dashboard.html', stats=stats, recent_results=recent_results)

    elif role == 'teacher':
        exams = conn.execute('''
            SELECT e.*,
                   COUNT(DISTINCT q.id) AS question_count,
                   COUNT(DISTINCT r.id) AS attempt_count
            FROM exams e
            LEFT JOIN questions q ON q.exam_id = e.id
            LEFT JOIN results   r ON r.exam_id = e.id
            WHERE e.teacher_id = ?
            GROUP BY e.id
            ORDER BY e.created_at DESC LIMIT 5
        ''', (session['user_id'],)).fetchall()
        stats = {
            'exams':   conn.execute(
                "SELECT COUNT(*) FROM exams WHERE teacher_id=?", (session['user_id'],)).fetchone()[0],
            'results': conn.execute('''
                SELECT COUNT(*) FROM results r
                JOIN exams e ON r.exam_id = e.id
                WHERE e.teacher_id = ?
            ''', (session['user_id'],)).fetchone()[0],
        }
        conn.close()
        return render_template('dashboard.html', exams=exams, stats=stats)

    else:  # student
        results = conn.execute('''
            SELECT r.*, e.title
            FROM results r
            JOIN exams e ON r.exam_id = e.id
            WHERE r.student_id = ?
            ORDER BY date_taken DESC LIMIT 5
        ''', (session['user_id'],)).fetchall()
        stats = {
            'taken': conn.execute(
                "SELECT COUNT(*) FROM results WHERE student_id=?", (session['user_id'],)).fetchone()[0],
            'available': conn.execute('''
                SELECT COUNT(*) FROM exams
                WHERE id NOT IN (SELECT exam_id FROM results WHERE student_id=?)
            ''', (session['user_id'],)).fetchone()[0],
        }
        conn.close()
        return render_template('dashboard.html', results=results, stats=stats)


# ─────────────────────────────────────────────────────────────────
# Users  (Admin only)
# ─────────────────────────────────────────────────────────────────

@app.route('/users')
@login_required
@role_required('admin')
def manage_users():
    conn  = models.get_db_connection()
    users = conn.execute(
        "SELECT id, name, email, role FROM users WHERE role != 'admin' ORDER BY role, name"
    ).fetchall()
    conn.close()
    return render_template('users.html', users=users)


@app.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
@role_required('admin')
def delete_user(user_id):
    conn = models.get_db_connection()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    flash("User deleted.", "success")
    return redirect(url_for('manage_users'))


# ─────────────────────────────────────────────────────────────────
# Exams  (unified route — dispatches by role)
# ─────────────────────────────────────────────────────────────────

@app.route('/exams')
@login_required
def exams():
    """
    FIX: This route is the target of the sidebar 'Exams' button for ALL roles.
    - admin   → lists all exams in the system
    - teacher → lists their own exams
    - student → redirects to available_exams
    """
    role = session.get('user_role')
    conn = models.get_db_connection()

    if role == 'admin':
        exam_list = conn.execute('''
            SELECT e.*, u.name AS teacher_name,
                   COUNT(DISTINCT q.id) AS question_count,
                   COUNT(DISTINCT r.id) AS attempt_count
            FROM exams e
            JOIN users u ON e.teacher_id = u.id
            LEFT JOIN questions q ON q.exam_id = e.id
            LEFT JOIN results   r ON r.exam_id = e.id
            GROUP BY e.id
            ORDER BY e.created_at DESC
        ''').fetchall()
        conn.close()
        return render_template('exams.html', exams=exam_list, view_type='admin')

    elif role == 'teacher':
        exam_list = conn.execute('''
            SELECT e.*,
                   COUNT(DISTINCT q.id) AS question_count,
                   COUNT(DISTINCT r.id) AS attempt_count
            FROM exams e
            LEFT JOIN questions q ON q.exam_id = e.id
            LEFT JOIN results   r ON r.exam_id = e.id
            WHERE e.teacher_id = ?
            GROUP BY e.id
            ORDER BY e.created_at DESC
        ''', (session['user_id'],)).fetchall()
        conn.close()
        return render_template('exams.html', exams=exam_list, view_type='teacher')

    else:  # student
        conn.close()
        return redirect(url_for('available_exams'))


# ─────────────────────────────────────────────────────────────────
# Results  (unified route — dispatches by role)
# ─────────────────────────────────────────────────────────────────

@app.route('/results')
@login_required
def results():
    """
    FIX: This route is the target of the sidebar 'Results' button for ALL roles.
    - admin   → all results across system
    - teacher → results for their exams only
    - student → redirects to student_results
    """
    role = session.get('user_role')
    conn = models.get_db_connection()

    if role == 'admin':
        result_list = conn.execute('''
            SELECT r.*, e.title AS exam_title,
                   us.name AS student_name,
                   ut.name AS teacher_name
            FROM results r
            JOIN exams e  ON r.exam_id    = e.id
            JOIN users us ON r.student_id = us.id
            JOIN users ut ON e.teacher_id = ut.id
            ORDER BY r.date_taken DESC
        ''').fetchall()
        conn.close()
        return render_template('results.html', results=result_list, view_type='admin')

    elif role == 'teacher':
        result_list = conn.execute('''
            SELECT r.*, e.title AS exam_title, u.name AS student_name
            FROM results r
            JOIN exams e ON r.exam_id    = e.id
            JOIN users u ON r.student_id = u.id
            WHERE e.teacher_id = ?
            ORDER BY r.date_taken DESC
        ''', (session['user_id'],)).fetchall()
        conn.close()
        return render_template('results.html', results=result_list, view_type='teacher')

    else:  # student
        conn.close()
        return redirect(url_for('student_results'))


# ─────────────────────────────────────────────────────────────────
# Exam CRUD  (Teacher)
# ─────────────────────────────────────────────────────────────────

@app.route('/exam/create', methods=['GET', 'POST'])
@login_required
@role_required('teacher')
def create_exam():
    if request.method == 'POST':
        title    = request.form.get('title', '').strip()
        duration = request.form.get('duration', 30)

        if not title:
            flash("Exam title is required.", "danger")
            return render_template('create_exam.html')

        conn   = models.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO exams (title, teacher_id, duration) VALUES (?, ?, ?)",
            (title, session['user_id'], duration)
        )
        exam_id = cursor.lastrowid
        conn.commit()
        conn.close()

        flash("Exam created! Now add your questions.", "success")
        return redirect(url_for('manage_questions', exam_id=exam_id))

    return render_template('create_exam.html')


@app.route('/exam/manage/<int:exam_id>', methods=['GET', 'POST'])
@login_required
@role_required('teacher')
def manage_questions(exam_id):
    conn = models.get_db_connection()
    exam = conn.execute(
        "SELECT * FROM exams WHERE id = ? AND teacher_id = ?",
        (exam_id, session['user_id'])
    ).fetchone()

    if not exam:
        conn.close()
        flash("Exam not found or permission denied.", "danger")
        return redirect(url_for('exams'))

    if request.method == 'POST':
        fields = ['question_text','option_a','option_b','option_c','option_d','correct_option']
        vals   = [request.form.get(f, '').strip() for f in fields]

        if all(vals):
            conn.execute('''
                INSERT INTO questions
                  (exam_id, question_text, option_a, option_b, option_c, option_d, correct_option)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', [exam_id] + vals)
            conn.commit()
            flash("Question added.", "success")
        else:
            flash("All fields are required.", "danger")

    questions = conn.execute(
        "SELECT * FROM questions WHERE exam_id = ? ORDER BY id", (exam_id,)
    ).fetchall()
    conn.close()
    return render_template('manage_questions.html', exam=exam, questions=questions)


@app.route('/exam/delete/<int:exam_id>', methods=['POST'])
@login_required
@role_required('teacher')
def delete_exam(exam_id):
    conn = models.get_db_connection()
    conn.execute("DELETE FROM exams WHERE id = ? AND teacher_id = ?", (exam_id, session['user_id']))
    conn.commit()
    conn.close()
    flash("Exam deleted.", "success")
    return redirect(url_for('exams'))


@app.route('/question/delete/<int:question_id>', methods=['POST'])
@login_required
@role_required('teacher')
def delete_question(question_id):
    conn     = models.get_db_connection()
    question = conn.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
    exam_id  = question['exam_id'] if question else None

    if question:
        exam = conn.execute(
            "SELECT id FROM exams WHERE id = ? AND teacher_id = ?",
            (exam_id, session['user_id'])
        ).fetchone()
        if exam:
            conn.execute("DELETE FROM questions WHERE id = ?", (question_id,))
            conn.commit()
            flash("Question removed.", "success")
        else:
            flash("Permission denied.", "danger")

    conn.close()
    return redirect(url_for('manage_questions', exam_id=exam_id))


@app.route('/exam/results/<int:exam_id>')
@login_required
@role_required('teacher')
def exam_results(exam_id):
    conn = models.get_db_connection()
    exam = conn.execute(
        "SELECT * FROM exams WHERE id = ? AND teacher_id = ?",
        (exam_id, session['user_id'])
    ).fetchone()

    if not exam:
        conn.close()
        flash("Exam not found.", "danger")
        return redirect(url_for('exams'))

    result_list = conn.execute('''
        SELECT r.*, u.name AS student_name
        FROM results r
        JOIN users u ON r.student_id = u.id
        WHERE r.exam_id = ?
        ORDER BY r.date_taken DESC
    ''', (exam_id,)).fetchall()
    conn.close()
    return render_template('exam_results.html', exam=exam, results=result_list)


# ─────────────────────────────────────────────────────────────────
# Student Routes
# ─────────────────────────────────────────────────────────────────

@app.route('/exams/available')
@login_required
@role_required('student')
def available_exams():
    conn  = models.get_db_connection()
    exams = conn.execute('''
        SELECT e.*, u.name AS teacher_name
        FROM exams e
        JOIN users u ON e.teacher_id = u.id
        WHERE e.id NOT IN (
            SELECT exam_id FROM results WHERE student_id = ?
        )
        ORDER BY e.created_at DESC
    ''', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('available_exams.html', exams=exams)


@app.route('/exam/take/<int:exam_id>', methods=['GET', 'POST'])
@login_required
@role_required('student')
def take_exam(exam_id):
    conn = models.get_db_connection()
    exam = conn.execute("SELECT * FROM exams WHERE id = ?", (exam_id,)).fetchone()

    if not exam:
        conn.close()
        flash("Exam not found.", "danger")
        return redirect(url_for('dashboard'))

    # Prevent retakes
    existing = conn.execute(
        "SELECT id FROM results WHERE student_id = ? AND exam_id = ?",
        (session['user_id'], exam_id)
    ).fetchone()
    if existing:
        conn.close()
        flash("You have already completed this exam.", "warning")
        return redirect(url_for('student_results'))

    questions = conn.execute(
        "SELECT id, question_text, option_a, option_b, option_c, option_d FROM questions WHERE exam_id = ?",
        (exam_id,)
    ).fetchall()

    if request.method == 'POST':
        score = 0
        total = len(questions)
        for q in questions:
            submitted = request.form.get(f'question_{q["id"]}')
            correct   = conn.execute(
                "SELECT correct_option FROM questions WHERE id = ?", (q["id"],)
            ).fetchone()['correct_option']
            if submitted == correct:
                score += 1

        conn.execute(
            "INSERT INTO results (student_id, exam_id, score, total) VALUES (?, ?, ?, ?)",
            (session['user_id'], exam_id, score, total)
        )
        conn.commit()
        conn.close()

        pct = round(score / total * 100) if total > 0 else 0
        flash(f'Exam submitted! You scored {score}/{total} ({pct}%).', 'success')
        return redirect(url_for('student_results'))

    conn.close()
    return render_template('take_exam.html', exam=exam, questions=questions)


@app.route('/my-results')
@login_required
@role_required('student')
def student_results():
    conn        = models.get_db_connection()
    result_list = conn.execute('''
        SELECT r.*, e.title, u.name AS teacher_name
        FROM results r
        JOIN exams e ON r.exam_id    = e.id
        JOIN users u ON e.teacher_id = u.id
        WHERE r.student_id = ?
        ORDER BY date_taken DESC
    ''', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('student_results.html', results=result_list)


# ─────────────────────────────────────────────────────────────────
# Admin: delete any exam
# ─────────────────────────────────────────────────────────────────

@app.route('/admin/exam/delete/<int:exam_id>', methods=['POST'])
@login_required
@role_required('admin')
def admin_delete_exam(exam_id):
    conn = models.get_db_connection()
    conn.execute("DELETE FROM exams WHERE id = ?", (exam_id,))
    conn.commit()
    conn.close()
    flash("Exam deleted.", "success")
    return redirect(url_for('exams'))


# ─────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
