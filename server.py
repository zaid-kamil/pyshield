from flask import Flask, render_template, request, redirect, session, flash, send_file, send_from_directory, zipfile, make_response
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
import zipfile
import shutil
from werkzeug.utils import secure_filename
from datetime import datetime

import os

os.makedirs('static', exist_ok=True)
os.makedirs('templates', exist_ok=True)
os.makedirs('static/css', exist_ok=True)
os.makedirs('static/js', exist_ok=True)
os.makedirs('static/img', exist_ok=True)
os.makedirs('static/source_code', exist_ok=True)
os.makedirs('static/temp', exist_ok=True)


app = Flask(__name__)

app.secret_key = 'super secret key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shield.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SRC_FOLDER'] = 'static/source_code'
app.config['TEMP_FOLDER'] = 'static/temp'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'zip'}

db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))

class SourceCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    zip_file = db.Column(db.String(255))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(100), default='Pending')

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    source_code_id = db.Column(db.Integer, db.ForeignKey('source_code.id'))
    report_path = db.Column(db.String(255))
    date = db.Column(db.DateTime, default=datetime.utcnow)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def unzip_src_code(zip_file, name):
    src_folder = app.config['SRC_FOLDER']                                                       # source code folder
    temp_folder = app.config['TEMP_FOLDER']                                                     # temp folder
    os.makedirs(src_folder, exist_ok=True)                                                      # create source code folder if not exists
    os.makedirs(temp_folder, exist_ok=True)                                                     # create temp folder if not exists  
    zip_file.save(os.path.join(temp_folder, zip_file.filename))                                 # save zip file to temp folder
    with zipfile.ZipFile(os.path.join(temp_folder, zip_file.filename), 'r') as zip_ref:         # open zip file
        zip_ref.extractall(src_folder)                                                          # extract zip file to source code folder  
    os.rename(os.path.join(src_folder, zip_file.filename.rsplit('.', 1)[0]), os.path.join(src_folder, name))    # rename folder
    
def scan_src_code(name):
    src_folder = app.config['SRC_FOLDER']                                                       # source code folder
    temp_folder = app.config['TEMP_FOLDER']                                                     # temp folder
    os.makedirs(src_folder, exist_ok=True)                                                      # create source code folder if not exists
    os.makedirs(temp_folder, exist_ok=True)                                                     # create temp folder if not exists  
    os.system(f'python3 scan.py {os.path.join(src_folder, name)}')                              # run scan.py script



@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def index():
    return render_template('index.html')

# register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('User already exists!', 'danger')
            return redirect('/register')
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        flash('User successfully registered!', 'success')
        return redirect('/login')
    return render_template('register.html')

# login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            login_user(user)
            flash('User successfully logged in!', 'success')
            return redirect('/dashboard')
        flash('Invalid credentials!', 'danger')
        return redirect('/login')
    return render_template('login.html')

# logout
@app.route('/logout')
def logout():
    logout_user()
    flash('User successfully logged out!', 'success')
    return redirect('/')

# dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    source_codes = SourceCode.query.filter_by(user_id=current_user.id).all()
    reports = Report.query.join(SourceCode).filter(SourceCode.user_id==current_user.id).all()
    return render_template('dashboard.html', source_codes=source_codes, reports=reports)

# upload zip file
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        name = request.form['name']
        zip_file = request.files['zip_file']
        if zip_file and allowed_file(zip_file.filename):
            try:
                source_code = SourceCode(name=name, user_id=current_user.id, zip_file=zip_file.filename)
                db.session.add(source_code)
                db.session.commit()
                unzip_src_code(zip_file, name)
                scan_src_code(name)
                flash('Source code uploaded successfully!', 'success')
                return redirect('/dashboard')
            except Exception as e:
                print(e)
                flash('Invalid file!', 'danger')
                return redirect('/upload')
        else:
            flash('Invalid file!', 'danger')
            return redirect('/upload')
    return render_template('upload.html')


# download report
@app.route('/download/<int:id>')
@login_required
def download(id):
    try:
        report = Report.query.get(id)
        return send_file(report.report_path, as_attachment=True)
    except Exception as e:
        print(e)
        flash('Report not found!', 'danger')
        return redirect('/dashboard')


# delete source code
@app.route('/delete/<int:id>')
@login_required
def delete(id):
    try:
        source_code = SourceCode.query.get(id)
        db.session.delete(source_code)
        db.session.commit()
        shutil.rmtree(os.path.join(app.config['SRC_FOLDER'], source_code.name))
        flash('Source code deleted successfully!', 'success')
        return redirect('/dashboard')
    except Exception as e:
        print(e)
        flash('Source code not found!', 'danger')
        return redirect('/dashboard')

# delete report
@app.route('/delete_report/<int:id>')
@login_required
def delete_report(id):
    try:
        report = Report.query.get(id)
        db.session.delete(report)
        db.session.commit()
        os.remove(report.report_path)
        flash('Report deleted successfully!', 'success')
    except Exception as e:
        print(e)
        flash('Report not found!', 'danger')
    return redirect('/dashboard')

# view source code files
@app.route('/view/<int:id>')
@login_required
def view(id):
    try:
        source_code = SourceCode.query.get(id)
        files = os.listdir(os.path.join(app.config['SRC_FOLDER'], source_code.name))
        # name, size, type, created, modified, accessed, is_dir
        file_details = []
        for file in files:
            file_path = os.path.join(app.config['SRC_FOLDER'], source_code.name, file)
            file_stat = os.stat(file_path)
            file_details.append({
                'name': file,
                'size': file_stat.st_size,
                'type': 'File' if os.path.isfile(file_path) else 'Directory',
                'created': datetime.fromtimestamp(file_stat.st_ctime),
                'modified': datetime.fromtimestamp(file_stat.st_mtime),
                'accessed': datetime.fromtimestamp(file_stat.st_atime),
                'is_dir': os.path.isdir(file_path)
            })
        return render_template('view.html', files=file_details, name=source_code.name,)
    except Exception as e:
        print(e)
        flash('Source code not found!', 'danger')
        return redirect('/dashboard')

# view report
@app.route('/view_report/<int:id>')
@login_required
def view_report(id):
    try:
        report = Report.query.get(id)
        with open(report.report_path, 'r') as f:
            content = f.read()
        return render_template('view_report.html', content=content)
    except Exception as e:
        print(e)
        flash('Report not found!', 'danger')
        return redirect('/dashboard')
        

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='127.0.0.1', port=8000, debug=True)
 