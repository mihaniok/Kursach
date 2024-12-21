# app.py

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_wtf import CSRFProtect
from db_handler import DBHandler
from werkzeug.security import generate_password_hash, check_password_hash
from forms import RegistrationForm, LoginForm  # Импортируем формы
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Замените на ваш уникальный секретный ключ
csrf = CSRFProtect(app)  # Включение защиты от CSRF

# Настройки подключения к базе данных
db_config = {
    'dbname': 'kursach',      # Название вашей БД
    'user': 'postgres',       # Пользователь PostgreSQL
    'password': 'root',       # Пароль пользователя
    'host': 'localhost',
    'port': '5432'
}

# Инициализация обработчика БД
db = DBHandler(db_config)

def login_required(f):
    """Декоратор для защиты маршрутов, требующих авторизации."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash("Пожалуйста, войдите в систему.")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    """Главная страница: перенаправление на регистрацию или на страницу группы."""
    if 'username' not in session:
        return redirect(url_for('register'))
    else:
        return redirect(url_for('my_group'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Маршрут для регистрации нового пользователя."""
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        password = form.password.data.strip()
        display_name = form.display_name.data.strip()
        group_name = form.group_name.data.strip()

        # Проверка существования пользователя
        if db.user_exists(username):
            flash("Пользователь с таким именем уже существует.")
            return redirect(url_for('register'))

        # Хэширование пароля
        password_hash = generate_password_hash(password)

        # Проверка и создание группы, если она новая
        if not db.group_exists(group_name):
            db.create_group(group_name)

        # Создание пользователя
        db.create_user(username, password_hash, display_name, group_name)

        # Добавление пользователя в группу
        db.add_user_to_group(username, display_name, group_name)

        # Логиним пользователя
        session['username'] = username
        flash("Регистрация прошла успешно!")
        return redirect(url_for('my_group'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Маршрут для входа пользователя."""
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        password = form.password.data.strip()

        # Получение пользователя из БД
        user = db.get_user(username)
        if not user:
            flash("Пользователь не найден.")
            return redirect(url_for('login'))

        user_id, u_name, password_hash, display_name, group_name = user

        # Проверка пароля
        if check_password_hash(password_hash, password):
            session['username'] = u_name
            flash("Вы успешно вошли.")
            return redirect(url_for('my_group'))
        else:
            flash("Неверный пароль.")
            return redirect(url_for('login'))
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    """Маршрут для выхода пользователя."""
    session.pop('username', None)
    flash("Вы вышли из системы.")
    return redirect(url_for('login'))

@app.route('/my_group', methods=['GET'])
@login_required
def my_group():
    """Маршрут для отображения группы текущего пользователя."""
    user = db.get_user(session['username'])
    if user:
        user_id, username, password_hash, display_name, group_name = user
        members = db.get_group_members(group_name)
        return render_template('my_group.html', group_name=group_name, members=members)
    else:
        flash("Пользователь не найден.")
        return redirect(url_for('logout'))

@app.route('/groups', methods=['GET'])
@login_required
def groups():
    """
    Маршрут для отображения всех групп.
    - Если запрос был выполнен через AJAX (Accept: application/json или параметр ajax), возвращает JSON.
    - В противном случае, отображает HTML-страницу с группами.
    """
    # Проверяем, является ли запрос AJAX
    is_ajax = request.headers.get('Accept') == 'application/json' or request.args.get('ajax')

    if is_ajax:
        all_groups = db.get_all_groups()
        return jsonify({"success": True, "groups": all_groups})
    else:
        all_groups = db.get_all_groups()
        return render_template('groups.html', groups=all_groups)

@app.route('/group/<group_name>', methods=['GET'])
@login_required
def view_group(group_name):
    """
    Маршрут для просмотра участников конкретной группы.
    - Если запрос был выполнен через AJAX, возвращает JSON.
    - В противном случае, отображает HTML-страницу с участниками группы.
    """
    # Проверяем, является ли запрос AJAX
    is_ajax = request.headers.get('Accept') == 'application/json' or request.args.get('ajax')

    if is_ajax:
        members = db.get_group_members(group_name)
        if not members and not db.group_exists(group_name):
            return jsonify({"success": False, "message": "Такой группы не существует."}), 404
        members_list = [{"id": m[0], "username": m[1], "display_name": m[2]} for m in members]
        return jsonify({"success": True, "group_name": group_name, "members": members_list})
    else:
        members = db.get_group_members(group_name)
        if not members and not db.group_exists(group_name):
            flash("Такой группы не существует.")
            return redirect(url_for('groups'))
        return render_template('view_group.html', group_name=group_name, members=members)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_student():
    """
    Маршрут для добавления нового студента.
    - Если запрос POST с JSON, обрабатывает через AJAX и возвращает JSON.
    - В противном случае, обрабатывает стандартную форму и перенаправляет.
    """
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            name = data.get('name', '').strip()
            group = data.get('group', '').strip()

            if not name or not group:
                return jsonify({"success": False, "message": "Заполните все поля."}), 400

            try:
                # Проверка существования группы и создание, если необходимо
                if not db.group_exists(group):
                    db.create_group(group)

                # Добавление студента
                new_id = db.add_student(name, group)
                return jsonify({"success": True, "id": new_id}), 201
            except Exception as e:
                return jsonify({"success": False, "message": str(e)}), 500
        else:
            # Обработка стандартной формы
            name = request.form.get('name').strip()
            group = request.form.get('group').strip()

            if not name or not group:
                flash("Заполните все поля.")
                return redirect(url_for('add_student'))

            try:
                if not db.group_exists(group):
                    db.create_group(group)

                new_id = db.add_student(name, group)
                flash(f"Студент добавлен с ID {new_id}")
                return redirect(url_for('my_group'))
            except Exception as e:
                flash(f"Ошибка: {e}")
                return redirect(url_for('add_student'))

    return render_template('add_student.html')

@app.route('/student/<int:student_id>', methods=['GET'])
@login_required
def student_details(student_id):
    """
    Маршрут для просмотра деталей конкретного студента.
    - Если запрос был выполнен через AJAX, возвращает JSON.
    - В противном случае, отображает HTML-страницу с деталями студента.
    """
    student = db.get_student_by_id(student_id)
    if request.headers.get('Accept') == 'application/json' or request.args.get('ajax'):
        if student:
            student_dict = {
                "id": student[0],
                "username": student[1],
                "display_name": student[2],
                "group_name": student[3]
            }
            return jsonify({"success": True, "student": student_dict})
        else:
            return jsonify({"success": False, "message": "Студент не найден."}), 404
    else:
        if not student:
            flash("Студент не найден.")
            return redirect(url_for('my_group'))
        return render_template('student_details.html', student=student)

if __name__ == '__main__':
    app.run(debug=True)
