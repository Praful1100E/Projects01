from flask import Flask, request, redirect, url_for, flash, render_template_string
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from ortools.sat.python import cp_model
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_secret_key_here')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///smart_timetable.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

class Faculty(db.Model):
    __tablename__ = 'faculty'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    max_load = db.Column(db.Integer, default=18)
    availability = db.Column(db.String(500))
    department = db.relationship('Department', backref='faculty')

class Classroom(db.Model):
    __tablename__ = 'classrooms'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    room_type = db.Column(db.String(50), nullable=False)

class Subject(db.Model):
    __tablename__ = 'subjects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    credits = db.Column(db.Integer, nullable=False)
    weekly_classes = db.Column(db.Integer, nullable=False)
    department = db.relationship('Department', backref='subjects')

class Batch(db.Model):
    __tablename__ = 'batches'
    id = db.Column(db.Integer, primary_key=True)
    program = db.Column(db.String(100), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    students = db.Column(db.Integer, nullable=False)
    __table_args__ = (db.UniqueConstraint('program', 'semester', name='_batch_uc'),)

class LunchBreak(db.Model):
    __tablename__ = 'lunchbreaks'
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('batches.id'), nullable=False)
    day = db.Column(db.String(10), nullable=False)
    start_time = db.Column(db.String(10), nullable=False)
    end_time = db.Column(db.String(10), nullable=False)
    batch = db.relationship('Batch', backref='lunchbreaks')

class Schedule(db.Model):
    __tablename__ = 'schedules'
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('batches.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'), nullable=False)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)
    day = db.Column(db.String(10), nullable=False)
    time_slot = db.Column(db.String(10), nullable=False)
    batch = db.relationship('Batch')
    subject = db.relationship('Subject')
    faculty = db.relationship('Faculty')
    classroom = db.relationship('Classroom')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def setup_database():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            faculty_user = User(username='faculty1', role='faculty')
            faculty_user.set_password('faculty123')
            db.session.add(faculty_user)
            depthead = User(username='depthead', role='dept_head')
            depthead.set_password('dept123')
            db.session.add(depthead)
            if not Department.query.first():
                db.session.add_all([
                    Department(name='Computer Science'),
                    Department(name='Electrical'),
                    Department(name='Mechanical')
                ])
            db.session.commit()

setup_database()

BASE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <title>{{ title }}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { background:#121212; color:#00ffff; font-family: Arial, sans-serif; margin:0; padding:0; }
        nav { background:#222; padding:0.5em 1em; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.8em; }
        nav a { color:#00ced1; text-decoration:none; font-weight:bold; }
        nav a:hover { color:#009999; }
        .container { max-width:900px; margin:2em auto; padding:1em; background:#222; border-radius:8px; }
        input, select, textarea, button { background:#222; color:#00ffff; border:1px solid #00ced1; padding:0.6em; margin-top:0.5em; width:100%; box-sizing:border-box; }
        button { background:#00ced1; border:none; cursor:pointer; margin-top:1em; font-weight:bold; }
        button:hover { background:#009999; }
        table { width:100%; border-collapse:collapse; margin-top:1em; }
        th, td { border:1px solid #00ced1; padding:0.5em; text-align:left; }
        th { background:#009999; color:#000; font-weight:bold; }
        .flash-error { background:#ff4d4d; color:#fff; padding:1em; margin-bottom:1em; border-radius:6px; }
        .flash-success { background:#00cc66; color:#000; padding:1em; margin-bottom:1em; border-radius:6px; }
        .admin-only { color:#ff4d4d; font-weight:bold; }
        .lunch-break { background:#cc0000; color:#fff; font-weight:bold; }
        @media (max-width: 600px) {
            nav { flex-direction:column; align-items:flex-start; }
            nav a { margin:0.3em 0; }
            table, thead, tbody, th, td, tr { display:block; }
            thead tr { position:absolute; top:-9999px; left:-9999px; }
            tr { margin-bottom:1em; border:1px solid #00ced1; }
            td { border:none; border-bottom:1px solid #00ced1; position:relative; padding-left:50%; }
            td:before { position:absolute; top:0; left:6px; width:45%; padding-right:10px; white-space:nowrap; }
            td:nth-of-type(1):before { content:"Day"; }
            td:nth-of-type(2):before { content:"Time"; }
            td:nth-of-type(3):before { content:"Subject"; }
            td:nth-of-type(4):before { content:"Faculty"; }
            td:nth-of-type(5):before { content:"Classroom"; }
        }
    </style>
</head>
<body>
<nav>
    <div><strong>Smart Timetable</strong></div>
    <div>
        <a href="/dashboard">Dashboard</a>
        <a href="/view_data">View Data</a>
        {% if current_user.is_authenticated and current_user.role == "admin" %}
            <a href="/add_entity/faculty" class="admin-only">Add Faculty</a>
            <a href="/add_entity/classroom" class="admin-only">Add Classroom</a>
            <a href="/add_entity/subject" class="admin-only">Add Subject</a>
            <a href="/add_entity/batch" class="admin-only">Add Batch</a>
            <a href="/add_lunchbreak" class="admin-only">Add Lunch Break</a>
        {% endif %}
        <a href="/generate_timetable">Generate Timetable</a>
        <a href="/view_timetable">View Timetable</a>
        {% if current_user.is_authenticated %}
            <a href="/logout">Logout</a>
        {% else %}
            <a href="/login">Login</a>
        {% endif %}
    </div>
</nav>
<div class="container">
    {% for category, message in get_flashed_messages(with_categories=True) %}
        <div class="flash-{{ category }}">{{ message }}</div>
    {% endfor %}
    {{ content|safe }}
</div>
</body>
</html>
'''

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.check_password(request.form['password']):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password', 'error')
    login_form = '''
    <h2>Login</h2>
    <form method="post">
        <label>Username</label><input name="username" required />
        <label>Password</label><input type="password" name="password" required />
        <button type="submit">Login</button>
    </form>
    '''
    return render_template_string(BASE_TEMPLATE, title='Login', content=login_form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    links = []
    if current_user.role == 'admin':
        links.append('<p><a href="/add_entity/faculty" class="admin-only">Add Faculty</a></p>')
        links.append('<p><a href="/add_entity/classroom" class="admin-only">Add Classroom</a></p>')
        links.append('<p><a href="/add_entity/subject" class="admin-only">Add Subject</a></p>')
        links.append('<p><a href="/add_entity/batch" class="admin-only">Add Batch</a></p>')
        links.append('<p><a href="/add_lunchbreak" class="admin-only">Add Lunch Break</a></p>')
    dashboard_content = f'''
    <p>Welcome, <strong>{current_user.username}</strong>!</p>
    <p>Your role: <span class="{'admin-only' if current_user.role == 'admin' else ''}">{current_user.role}</span></p>
    {"".join(links)}
    <p><a href="/view_timetable">View Timetable</a></p>
    <p><a href="/generate_timetable">Generate Timetable</a></p>
    '''
    return render_template_string(BASE_TEMPLATE, title='Dashboard', content=dashboard_content)

@app.route('/add_entity/<entity>', methods=['GET', 'POST'])
@login_required
def add_entity(entity):
    if current_user.role != 'admin':
        flash('Only admins can add or edit data.', 'error')
        return redirect(url_for('dashboard'))
    model_map = {
        'faculty': Faculty,
        'classroom': Classroom,
        'subject': Subject,
        'batch': Batch
    }
    model = model_map.get(entity)
    if not model:
        flash('Invalid entity type.', 'error')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        try:
            if entity == 'faculty':
                if not Department.query.get(int(request.form['department_id'])):
                    raise ValueError('Department does not exist.')
                item = Faculty(
                    name=request.form['name'],
                    department_id=int(request.form['department_id']),
                    max_load=int(request.form.get('max_load', 18)),
                    availability=request.form.get('availability', '')
                )
            elif entity == 'classroom':
                item = Classroom(
                    name=request.form['name'],
                    capacity=int(request.form['capacity']),
                    room_type=request.form['room_type']
                )
            elif entity == 'subject':
                if not Department.query.get(int(request.form['department_id'])):
                    raise ValueError('Department does not exist.')
                item = Subject(
                    name=request.form['name'],
                    department_id=int(request.form['department_id']),
                    credits=int(request.form['credits']),
                    weekly_classes=int(request.form['weekly_classes'])
                )
            elif entity == 'batch':
                item = Batch(
                    program=request.form['program'],
                    semester=int(request.form['semester']),
                    students=int(request.form['students'])
                )
            db.session.add(item)
            db.session.commit()
            flash(f'{entity.capitalize()} added successfully.', 'success')
            return redirect(url_for('add_entity', entity=entity))
        except Exception as e:
            flash(f'Error adding {entity}: {str(e)}', 'error')
    dept_options = ''
    if entity in ('faculty', 'subject'):
        depts = Department.query.order_by(Department.name).all()
        if not depts:
            flash('No departments exist. Add departments first.', 'error')
            return redirect(url_for('dashboard'))
        dept_options = ''.join(f'<option value="{d.id}">{d.name}</option>' for d in depts)
    fields = {
        'faculty': [('name','text'), ('department_id','select',dept_options), ('max_load','number',18), ('availability','text')],
        'classroom': [('name','text'), ('capacity','number'), ('room_type','text')],
        'subject': [('name','text'), ('department_id','select',dept_options), ('credits','number'), ('weekly_classes','number')],
        'batch': [('program','text'), ('semester','number'), ('students','number')]
    }.get(entity, [])
    rows = ''
    for field in fields:
        if len(field) == 3:
            rows += f'<label>{field[0].replace("_"," ").title()}</label><select name="{field[0]}"{" required" if field[0] in ("department_id", "name") else ""}>{field[2] if field[1] == "select" else ""}</select>'
        else:
            rows += f'<label>{field[0].replace("_"," ").title()}</label><input name="{field[0]}" type="{field[1]}" value="{field[2] if len(field) > 2 else ""}"{" required" if field[0] in ("name", "department_id", "capacity", "room_type", "credits", "weekly_classes", "program", "semester", "students") else ""} />'
    content = f'''
    <h2>Add {entity.capitalize()}</h2>
    <form method="post">{rows}<button type="submit">Add</button></form>
    <p><a href="/dashboard">Back to Dashboard</a></p>
    '''
    return render_template_string(BASE_TEMPLATE, title=f'Add {entity.capitalize()}', content=content)

@app.route('/add_lunchbreak', methods=['GET', 'POST'])
@login_required
def add_lunchbreak():
    if current_user.role != 'admin':
        flash('Only admins can add or edit lunch breaks.', 'error')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        try:
            batch = Batch.query.get(int(request.form['batch_id']))
            if not batch:
                raise ValueError('Batch does not exist.')
            lb = LunchBreak(
                batch_id=int(request.form['batch_id']),
                day=request.form['day'],
                start_time=request.form['start_time'],
                end_time=request.form['end_time']
            )
            db.session.add(lb)
            db.session.commit()
            flash('Lunch break added successfully.', 'success')
            return redirect(url_for('add_lunchbreak'))
        except Exception as e:
            flash(f'Error adding lunch break: {str(e)}', 'error')
    batch_options = ''.join(f'<option value="{b.id}">{b.program} (Sem {b.semester})</option>' for b in Batch.query.order_by(Batch.program, Batch.semester))
    if not batch_options:
        flash('No batches exist. Add a batch first.', 'error')
        return redirect(url_for('dashboard'))
    content = f'''
    <h2>Add Lunch Break</h2>
    <form method="post">
        <label>Batch</label><select name="batch_id" required>{batch_options}</select>
        <label>Day</label><select name="day" required>
            <option>Mon</option><option>Tue</option><option>Wed</option><option>Thu</option><option>Fri</option>
        </select>
        <label>Start Time</label><input name="start_time" type="time" required />
        <label>End Time</label><input name="end_time" type="time" required />
        <button type="submit">Add Lunch Break</button>
    </form>
    <p><a href="/dashboard">Back to Dashboard</a></p>
    '''
    return render_template_string(BASE_TEMPLATE, title='Add Lunch Break', content=content)

@app.route('/view_data')
@login_required
def view_data():
    models = [Faculty, Classroom, Subject, Batch, LunchBreak]
    content = '<h2>All Data</h2>'
    for model in models:
        content += f'<h3>{model.__tablename__.replace("_"," ").title()}</h3>'
        items = model.query.all()
        if items:
            cols = [c.name for c in model.__table__.columns]
            content += '<table><thead><tr>'
            for col in cols:
                content += f'<th>{col.replace("_"," ").title()}</th>'
            content += '</tr></thead><tbody>'
            for item in items:
                content += '<tr>'
                for col in cols:
                    content += f'<td>{getattr(item, col)}</td>'
                content += '</tr>'
            content += '</tbody></table>'
        else:
            content += '<p>No data</p>'
    return render_template_string(BASE_TEMPLATE, title='View Data', content=content)

@app.route('/generate_timetable')
@login_required
def generate_timetable():
    if current_user.role != 'admin':
        flash('Only admins can generate timetables.', 'error')
        return redirect(url_for('dashboard'))
    model = cp_model.CpModel()
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
    hours = ['9-10am', '10-11am', '11-12pm', '1-2pm', '2-3pm']
    batches = Batch.query.order_by(Batch.program, Batch.semester).all()
    subjects = Subject.query.order_by(Subject.name).all()
    faculty = Faculty.query.order_by(Faculty.name).all()
    classrooms = Classroom.query.order_by(Classroom.name).all()
    lunchbreaks = LunchBreak.query.all()

    timetable_vars = {}
    for b in batches:
        for s in subjects:
            for d in days:
                for h in hours:
                    for c in classrooms:
                        for f in faculty:
                            if f.department_id == s.department_id:
                                timetable_vars[(b.id, s.id, d, h, c.id, f.id)] = model.NewBoolVar(f'b{b.id}_s{s.id}_d{d}_h{h}_c{c.id}_f{f.id}')

    # Each subject must meet weekly_classes times per batch
    for b in batches:
        for s in subjects:
            vars = [timetable_vars[(b.id, s.id, d, h, c.id, f.id)]
                   for d in days for h in hours for c in classrooms for f in faculty if (b.id, s.id, d, h, c.id, f.id) in timetable_vars]
            model.Add(sum(vars) == s.weekly_classes)

    # Prevent double-booking of classrooms
    for d in days:
        for h in hours:
            for c in classrooms:
                vars = [timetable_vars[(b.id, s.id, d, h, c.id, f.id)]
                      for b in batches for s in subjects for f in faculty if (b.id, s.id, d, h, c.id, f.id) in timetable_vars]
                model.Add(sum(vars) <= 1)

    # Faculty max load
    for f in faculty:
        vars = [timetable_vars[(b.id, s.id, d, h, c.id, f.id)]
              for b in batches for s in subjects for d in days for h in hours for c in classrooms if (b.id, s.id, d, h, c.id, f.id) in timetable_vars]
        model.Add(sum(vars) <= f.max_load)

    # Lunch break constraints
    for lb in lunchbreaks:
        for s in subjects:
            for c in classrooms:
                for f in faculty:
                    if (lb.batch_id, s.id, lb.day, lb.start_time, c.id, f.id) in timetable_vars:
                        model.Add(timetable_vars[(lb.batch_id, s.id, lb.day, lb.start_time, c.id, f.id)] == 0)

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        Schedule.query.delete()
        db.session.commit()
        for key in timetable_vars:
            if solver.Value(timetable_vars[key]) == 1:
                (batch_id, subject_id, day, hour, classroom_id, faculty_id) = key
                db.session.add(Schedule(
                    batch_id=batch_id,
                    subject_id=subject_id,
                    faculty_id=faculty_id,
                    classroom_id=classroom_id,
                    day=day,
                    time_slot=hour
                ))
        db.session.commit()
        flash('Timetable generated successfully.', 'success')
    else:
        flash('No feasible schedule found with current constraints.', 'error')
    return redirect(url_for('view_timetable'))

@app.route('/view_timetable')
@login_required
def view_timetable():
    schedules = Schedule.query.all()
    content = '<h2>Generated Timetable</h2>'
    if not schedules:
        content += '<p>No timetable generated yet.</p>'
    else:
        timetable = {}
        for s in schedules:
            batch_name = f"{s.batch.program} (Sem {s.batch.semester})"
            if batch_name not in timetable:
                timetable[batch_name] = []
            timetable[batch_name].append(s)
        for batch in timetable:
            batch_id = Batch.query.filter_by(program=batch.split(' (')[0]).first().id
            lunches = LunchBreak.query.filter_by(batch_id=batch_id).all()
            lunch_slots = {(lb.day, lb.start_time) for lb in lunches}
            timetable[batch] = sorted(
                timetable[batch],
                key=lambda x: (['Mon','Tue','Wed','Thu','Fri'].index(x.day), x.time_slot)
            )
            content += f'<h3>{batch}</h3><table><thead><tr><th>Day</th><th>Time</th><th>Subject</th><th>Faculty</th><th>Classroom</th></tr></thead><tbody>'
            for sch in timetable[batch]:
                is_lunch = (sch.day, sch.time_slot) in lunch_slots
                row_class = ' class="lunch-break"' if is_lunch else ''
                content += f'<tr{row_class}><td>{sch.day}</td><td>{sch.time_slot}</td><td>{sch.subject.name}</td><td>{sch.faculty.name}</td><td>{sch.classroom.name}</td></tr>'
            content += '</tbody></table>'
    content += '<p><a href="/dashboard">Back to Dashboard</a></p>'
    return render_template_string(BASE_TEMPLATE, title='Timetable', content=content)

if __name__ == '__main__':
    app.run(debug=True)
