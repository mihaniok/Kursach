# app.py

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_wtf import CSRFProtect
from db_handler import DBHandler
from werkzeug.security import generate_password_hash, check_password_hash
from forms import RegistrationForm, LoginForm, ProfileForm
import os

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your_default_secret_key')  # Замените на ваш уникальный секретный ключ
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
        if 'user_id' not in session:
            flash("Пожалуйста, войдите в систему.")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    """Главная страница: перенаправление на регистрацию или на страницу группы."""
    if 'user_id' not in session:
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
        email = form.email.data.strip() if form.email.data else None
        phone = form.phone.data.strip() if form.phone.data else None
        city = form.city.data.strip() if form.city.data else None
        date_of_birth = form.date_of_birth.data
        admission_year = form.admission_year.data

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
        user_id = db.create_user(username, password_hash, display_name, group_name, email, phone, city, date_of_birth, admission_year)

        # Добавление пользователя в группу
        db.add_user_to_group(username, display_name, group_name, phone, city, date_of_birth, admission_year)

        # Логиним пользователя
        session['user_id'] = user_id
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

        user_id, u_name, password_hash, display_name, group_name, email, phone, city, date_of_birth, admission_year, date_joined = user

        # Проверка пароля
        if check_password_hash(password_hash, password):
            session['user_id'] = user_id
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
    session.pop('user_id', None)
    flash("Вы вышли из системы.")
    return redirect(url_for('login'))

@app.route('/my_group', methods=['GET'])
@login_required
def my_group():
    """Маршрут для отображения группы текущего пользователя."""
    user = db.get_user_by_id(session['user_id'])
    if user:
        user_id, username, password_hash, display_name, group_name, email, phone, city, date_of_birth, admission_year, date_joined = user
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
        members_list = [{"id": m[0], "username": m[1], "display_name": m[2], "phone": m[3], "city": m[4], "date_of_birth": m[5], "admission_year": m[6]} for m in members]
        return jsonify({"success": True, "group_name": group_name, "members": members_list})
    else:
        members = db.get_group_members(group_name)
        if not members and not db.group_exists(group_name):
            flash("Такой группы не существует.")
            return redirect(url_for('groups'))
        return render_template('view_group.html', group_name=group_name, members=members)

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
                "phone": student[3],
                "city": student[4],
                "date_of_birth": student[5].strftime('%Y-%m-%d') if student[5] else None,
                "admission_year": student[6]
            }
            return jsonify({"success": True, "student": student_dict})
        else:
            return jsonify({"success": False, "message": "Студент не найден."}), 404
    else:
        if not student:
            flash("Студент не найден.")
            return redirect(url_for('my_group'))
        return render_template('student_details.html', student=student)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Маршрут для просмотра и редактирования личного кабинета пользователя."""
    user = db.get_user_by_id(session['user_id'])
    if not user:
        flash("Пользователь не найден.")
        return redirect(url_for('logout'))

    user_id, username, password_hash, display_name, group_name, email, phone, city, date_of_birth, admission_year, date_joined = user

    form = ProfileForm(obj={
        'display_name': display_name,
        'email': email,
        'phone': phone,
        'city': city,
        'date_of_birth': date_of_birth,
        'admission_year': admission_year
    })

    if form.validate_on_submit():
        new_display_name = form.display_name.data.strip()
        new_email = form.email.data.strip() if form.email.data else None
        new_phone = form.phone.data.strip() if form.phone.data else None
        new_city = form.city.data.strip() if form.city.data else None
        new_date_of_birth = form.date_of_birth.data
        new_admission_year = form.admission_year.data
        current_password = form.current_password.data.strip()
        new_password = form.new_password.data.strip() if form.new_password.data else None

        # Проверка текущего пароля, если пользователь хочет изменить пароль
        if new_password:
            if not current_password:
                flash("Для изменения пароля необходимо ввести текущий пароль.")
                return redirect(url_for('profile'))

            if not check_password_hash(password_hash, current_password):
                flash("Текущий пароль неверен.")
                return redirect(url_for('profile'))

            new_password_hash = generate_password_hash(new_password)
        else:
            new_password_hash = None

        # Обновление профиля
        db.update_user_profile(
            user_id=user_id,
            display_name=new_display_name,
            email=new_email,
            phone=new_phone,
            city=new_city,
            date_of_birth=new_date_of_birth,
            admission_year=new_admission_year,
            new_password_hash=new_password_hash
        )

        flash("Профиль успешно обновлён.")
        return redirect(url_for('profile'))

    return render_template('profile.html', form=form, username=username, group_name=group_name, date_joined=date_joined)

if __name__ == '__main__':
    app.run(debug=True)
