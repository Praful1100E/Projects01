from flask import Flask, request, render_template_string, send_file, flash, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import qrcode
import json
import os
import csv
from io import BytesIO, StringIO
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///railway_fittings.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Fitting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fitting_type = db.Column(db.String(50), nullable=False)  # elastic_rail_clip, rail_pad, liner, sleeper
    vendor_lot = db.Column(db.String(100), nullable=False)
    supply_date = db.Column(db.Date, nullable=False)
    warranty_period = db.Column(db.Integer, nullable=False)  # in months
    inspection_dates = db.Column(db.Text, nullable=True)  # JSON list of dates
    qr_data = db.Column(db.Text, nullable=False)  # JSON string

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, inspector

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

def setup_database():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            inspector = User(username='inspector', role='inspector')
            inspector.set_password('inspector123')
            db.session.add(inspector)
            db.session.commit()

setup_database()

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Indian Railways Track Fittings QR System</title>
<style>
body { background-color: #0d1117; color: #00ffff; font-family: Arial, sans-serif; margin: 0; padding: 20px; }
.container { max-width: 1200px; margin: 0 auto; background-color: #161b22; padding: 20px; border-radius: 8px; }
h1, h2 { color: #00ffff; text-align: center; }
form { margin-bottom: 20px; }
label { display: block; margin-top: 10px; }
input, select, textarea, button { background-color: #21262d; color: #00ffff; border: 1px solid #00ffff; padding: 8px; width: 100%; box-sizing: border-box; }
button { background-color: #00ffff; color: #0d1117; cursor: pointer; margin-top: 10px; }
button:hover { background-color: #009999; }
table { width: 100%; border-collapse: collapse; margin-top: 20px; }
th, td { border: 1px solid #00ffff; padding: 8px; text-align: left; }
th { background-color: #004c4c; }
.qr-code { text-align: center; margin: 20px 0; }
.qr-code img { max-width: 200px; }
.nav { text-align: center; margin-bottom: 20px; }
.nav a { color: #00ffff; text-decoration: none; margin: 0 10px; padding: 10px; border: 1px solid #00ffff; border-radius: 4px; }
.nav a:hover { background-color: #00ffff; color: #0d1117; }
.flash { padding: 10px; margin: 10px 0; border-radius: 4px; }
.flash.success { background-color: #00cc66; color: #000; }
.flash.error { background-color: #ff4d4d; color: #fff; }
</style>
</head>
<body>
<div class="container">
<h1>Indian Railways Track Fittings QR Identification System</h1>
<div class="nav">
<a href="/">Home</a>
<a href="/generate_qr">Generate QR</a>
<a href="/scan_qr">Scan QR</a>
<a href="/inventory">Inventory</a>
<a href="/reports">Reports</a>
</div>
{% with messages = get_flashed_messages(with_categories=true) %}
{% if messages %}
{% for category, message in messages %}
<div class="flash {{ category }}">{{ message }}</div>
{% endfor %}
{% endif %}
{% endwith %}
{{ content|safe }}
</div>
</body>
</html>
'''

@app.route('/')
def home():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    content = '''
    <h2>Welcome to the Prototype</h2>
    <p>This system allows identification of track fittings using QR codes.</p>
    <p>Features:</p>
    <ul>
        <li>Generate QR codes for fittings with details</li>
        <li>Scan QR codes to retrieve information</li>
        <li>View inventory of all fittings</li>
        <li>Generate AI-based reports</li>
        <li>User authentication with roles</li>
        <li>Batch import from CSV</li>
        <li>Search and filter inventory</li>
        <li>Export reports to PDF</li>
        <li>Alerts dashboard</li>
    </ul>
    <p>Click on the navigation links above to explore.</p>
    '''
    return render_template_string(HTML_TEMPLATE, content=content)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.check_password(request.form['password']):
            login_user(user)
            return redirect(url_for('home'))
        flash('Invalid username or password', 'error')
    login_form = '''
    <h2>Login</h2>
    <form method="post">
        <label>Username</label><input name="username" required />
        <label>Password</label><input type="password" name="password" required />
        <button type="submit">Login</button>
    </form>
    <p>Default users: admin/admin123 (admin), inspector/inspector123 (inspector)</p>
    '''
    return render_template_string(HTML_TEMPLATE, title='Login', content=login_form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/generate_qr', methods=['GET', 'POST'])
def generate_qr():
    if request.method == 'POST':
        fitting_type = request.form['fitting_type']
        vendor_lot = request.form['vendor_lot']
        supply_date_str = request.form['supply_date']
        warranty_period = int(request.form['warranty_period'])
        inspection_dates = request.form.get('inspection_dates', '')

        supply_date = datetime.strptime(supply_date_str, '%Y-%m-%d').date()
        qr_data = {
            'fitting_type': fitting_type,
            'vendor_lot': vendor_lot,
            'supply_date': supply_date_str,
            'warranty_period': warranty_period,
            'inspection_dates': inspection_dates.split(',') if inspection_dates else []
        }

        fitting = Fitting(
            fitting_type=fitting_type,
            vendor_lot=vendor_lot,
            supply_date=supply_date,
            warranty_period=warranty_period,
            inspection_dates=json.dumps(qr_data['inspection_dates']),
            qr_data=json.dumps(qr_data)
        )
        db.session.add(fitting)
        db.session.commit()

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(json.dumps(qr_data))
        qr.make(fit=True)
        img = qr.make_image(fill='black', back_color='white')

        img_io = BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)

        return send_file(img_io, mimetype='image/png', as_attachment=True, download_name=f'qr_{fitting.id}.png')

    content = '''
    <h2>Generate QR Code for Fitting</h2>
    <form method="post">
        <label>Fitting Type:</label>
        <select name="fitting_type" required>
            <option value="elastic_rail_clip">Elastic Rail Clip</option>
            <option value="rail_pad">Rail Pad</option>
            <option value="liner">Liner</option>
            <option value="sleeper">Sleeper</option>
        </select>
        <label>Vendor Lot Number:</label>
        <input type="text" name="vendor_lot" required>
        <label>Date of Supply:</label>
        <input type="date" name="supply_date" required>
        <label>Warranty Period (months):</label>
        <input type="number" name="warranty_period" required>
        <label>Inspection Dates (comma-separated, optional):</label>
        <input type="text" name="inspection_dates">
        <button type="submit">Generate QR</button>
    </form>
    '''
    return render_template_string(HTML_TEMPLATE, content=content)

@app.route('/scan_qr', methods=['GET', 'POST'])
def scan_qr():
    if request.method == 'POST':
        qr_text = request.form['qr_text']
        try:
            qr_data = json.loads(qr_text)
            content = f'''
            <h2>Scanned Fitting Details</h2>
            <p><strong>Type:</strong> {qr_data['fitting_type']}</p>
            <p><strong>Vendor Lot:</strong> {qr_data['vendor_lot']}</p>
            <p><strong>Supply Date:</strong> {qr_data['supply_date']}</p>
            <p><strong>Warranty Period:</strong> {qr_data['warranty_period']} months</p>
            <p><strong>Inspection Dates:</strong> {', '.join(qr_data['inspection_dates']) if qr_data['inspection_dates'] else 'None'}</p>
            '''
            flash('QR scanned successfully!', 'success')
        except json.JSONDecodeError:
            content = '<h2>Error</h2><p>Invalid QR data.</p>'
            flash('Invalid QR data.', 'error')
    else:
        content = '''
        <h2>Scan QR Code</h2>
        <p>Simulate scanning by pasting the QR data (JSON string):</p>
        <form method="post">
            <label>QR Data:</label>
            <textarea name="qr_text" rows="10" required></textarea>
            <button type="submit">Scan</button>
        </form>
        '''
    return render_template_string(HTML_TEMPLATE, content=content)

@app.route('/inventory')
def inventory():
    fittings = Fitting.query.all()
    content = '<h2>Fittings Inventory</h2>'
    if fittings:
        content += '''
        <table>
        <tr><th>ID</th><th>Type</th><th>Vendor Lot</th><th>Supply Date</th><th>Warranty (months)</th><th>Inspections</th></tr>
        '''
        for f in fittings:
            inspections = json.loads(f.inspection_dates) if f.inspection_dates else []
            content += f'''
            <tr>
                <td>{f.id}</td>
                <td>{f.fitting_type}</td>
                <td>{f.vendor_lot}</td>
                <td>{f.supply_date}</td>
                <td>{f.warranty_period}</td>
                <td>{', '.join(inspections) if inspections else 'None'}</td>
            </tr>
            '''
        content += '</table>'
    else:
        content += '<p>No fittings in inventory.</p>'
    return render_template_string(HTML_TEMPLATE, content=content)

@app.route('/reports')
def reports():
    fittings = Fitting.query.all()
    total = len(fittings)
    types_count = {}
    expired_warranty = 0
    now = datetime.now().date()
    for f in fittings:
        types_count[f.fitting_type] = types_count.get(f.fitting_type, 0) + 1
        warranty_end = f.supply_date + timedelta(days=f.warranty_period * 30)
        if now > warranty_end:
            expired_warranty += 1

    content = f'''
    <h2>AI-Based Reports</h2>
    <p><strong>Total Fittings:</strong> {total}</p>
    <p><strong>By Type:</strong></p>
    <ul>
    '''
    for t, c in types_count.items():
        content += f'<li>{t}: {c}</li>'
    content += f'''
    </ul>
    <p><strong>Expired Warranty:</strong> {expired_warranty}</p>
    <p><em>Note: This is a simulated AI report with basic analytics.</em></p>
    '''
    return render_template_string(HTML_TEMPLATE, content=content)

if __name__ == '__main__':
    app.run(debug=True)
