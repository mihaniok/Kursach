# db_handler.py

import psycopg2
from psycopg2 import sql

class DBHandler:
    def __init__(self, config):
        self.config = config
        self.init_db()

    def connect(self):
        conn = psycopg2.connect(**self.config)
        conn.set_client_encoding('UTF8')
        return conn

    def init_db(self):
        # Создание таблиц users и groups_list, если они не существуют
        with self.connect() as conn:
            with conn.cursor() as cur:
                # Таблица пользователей
                cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    display_name VARCHAR(100) NOT NULL,
                    group_name VARCHAR(100) NOT NULL,
                    email VARCHAR(255),
                    phone VARCHAR(20),
                    city VARCHAR(100),
                    date_of_birth DATE,
                    admission_year INTEGER,
                    date_joined TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """)

                # Таблица списка групп
                cur.execute("""
                CREATE TABLE IF NOT EXISTS groups_list (
                    group_name VARCHAR(100) PRIMARY KEY
                );
                """)
                conn.commit()

    def user_exists(self, username):
        query = "SELECT 1 FROM users WHERE username = %s;"
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (username,))
                return cur.fetchone() is not None

    def create_user(self, username, password_hash, display_name, group_name, email=None, phone=None, city=None, date_of_birth=None, admission_year=None):
        insert_user = """
        INSERT INTO users (username, password_hash, display_name, group_name, email, phone, city, date_of_birth, admission_year) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
        """
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(insert_user, (username, password_hash, display_name, group_name, email, phone, city, date_of_birth, admission_year))
                user_id = cur.fetchone()[0]
                conn.commit()
                return user_id

    def get_user(self, username):
        query = """
            SELECT id, username, password_hash, display_name, group_name, email, phone, city, date_of_birth, admission_year, date_joined 
            FROM users 
            WHERE username = %s;
        """
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (username,))
                return cur.fetchone()

    def group_exists(self, group_name):
        query = "SELECT 1 FROM groups_list WHERE group_name = %s;"
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (group_name,))
                return cur.fetchone() is not None

    def create_group(self, group_name):
        with self.connect() as conn:
            with conn.cursor() as cur:
                # Добавляем группу в список групп
                cur.execute("INSERT INTO groups_list (group_name) VALUES (%s) ON CONFLICT DO NOTHING;", (group_name,))
                # Создаем таблицу для группы с дополнительными полями
                create_group_table = sql.SQL("""
                CREATE TABLE IF NOT EXISTS {table} (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(100) NOT NULL,
                    display_name VARCHAR(100) NOT NULL,
                    phone VARCHAR(20),
                    city VARCHAR(100),
                    date_of_birth DATE,
                    admission_year INTEGER
                );
                """).format(table=sql.Identifier("group_" + group_name))
                cur.execute(create_group_table)
                conn.commit()

    def add_user_to_group(self, username, display_name, group_name, phone=None, city=None, date_of_birth=None, admission_year=None):
        table_name = "group_" + group_name
        insert_member = sql.SQL("""
            INSERT INTO {table} (username, display_name, phone, city, date_of_birth, admission_year) 
            VALUES (%s, %s, %s, %s, %s, %s);
        """).format(table=sql.Identifier(table_name))
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(insert_member, (username, display_name, phone, city, date_of_birth, admission_year))
                conn.commit()

    def get_group_members(self, group_name):
        if not self.group_exists(group_name):
            return []
        table_name = "group_" + group_name
        query = sql.SQL("""
            SELECT id, username, display_name, phone, city, date_of_birth, admission_year 
            FROM {table} 
            ORDER BY display_name ASC;
        """).format(table=sql.Identifier(table_name))
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                return cur.fetchall()

    def get_all_groups(self):
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT group_name FROM groups_list ORDER BY group_name;")
                return [row[0] for row in cur.fetchall()]

    def add_student(self, name, group, phone=None, city=None, date_of_birth=None, admission_year=None):
        """
        Добавляет студента в указанную группу.
        """
        table_name = "group_" + group
        insert_student = sql.SQL("""
            INSERT INTO {table} (username, display_name, phone, city, date_of_birth, admission_year) 
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;
        """).format(table=sql.Identifier(table_name))
        display_name = name  # В данном случае display_name = name, можно изменить по необходимости
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(insert_student, (name, display_name, phone, city, date_of_birth, admission_year))
                new_id = cur.fetchone()[0]
                conn.commit()
                return new_id

    def get_student_by_id(self, student_id, group_name=None):
        """
        Получает студента по ID. Если group_name указан, ищет только в этой группе.
        Если group_name не указан, перебирает все группы.
        """
        with self.connect() as conn:
            with conn.cursor() as cur:
                if group_name:
                    table_name = "group_" + group_name
                    query = sql.SQL("""
                        SELECT id, username, display_name, phone, city, date_of_birth, admission_year 
                        FROM {table} 
                        WHERE id = %s;
                    """).format(table=sql.Identifier(table_name))
                    cur.execute(query, (student_id,))
                    return cur.fetchone()
                else:
                    cur.execute("SELECT group_name FROM groups_list;")
                    groups = [row[0] for row in cur.fetchall()]
                    for group in groups:
                        table_name = "group_" + group
                        query = sql.SQL("""
                            SELECT id, username, display_name, phone, city, date_of_birth, admission_year 
                            FROM {table} 
                            WHERE id = %s;
                        """).format(table=sql.Identifier(table_name))
                        cur.execute(query, (student_id,))
                        student = cur.fetchone()
                        if student:
                            return student  # (id, username, display_name, phone, city, date_of_birth, admission_year)
        return None

    def update_user_profile(self, user_id, display_name, email=None, phone=None, city=None, date_of_birth=None, admission_year=None, new_password_hash=None):
        """
        Обновляет профиль пользователя.
        """
        fields = ["display_name = %s"]
        values = [display_name]

        if email is not None:
            fields.append("email = %s")
            values.append(email)
        
        if phone is not None:
            fields.append("phone = %s")
            values.append(phone)
        
        if city is not None:
            fields.append("city = %s")
            values.append(city)
        
        if date_of_birth is not None:
            fields.append("date_of_birth = %s")
            values.append(date_of_birth)
        
        if admission_year is not None:
            fields.append("admission_year = %s")
            values.append(admission_year)

        if new_password_hash is not None:
            fields.append("password_hash = %s")
            values.append(new_password_hash)

        values.append(user_id)

        query = f"UPDATE users SET {', '.join(fields)} WHERE id = %s;"

        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, tuple(values))
                conn.commit()

    def get_user_by_id(self, user_id):
        """
        Получает пользователя по ID.
        """
        query = """
            SELECT id, username, password_hash, display_name, group_name, email, phone, city, date_of_birth, admission_year, date_joined 
            FROM users 
            WHERE id = %s;
        """
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (user_id,))
                return cur.fetchone()

    def get_group_name_by_username(self, username):
        """
        Получает название группы по username пользователя.
        """
        query = "SELECT group_name FROM users WHERE username = %s;"
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (username,))
                result = cur.fetchone()
                if result:
                    return result[0]
                else:
                    return None

    def update_student_in_group(self, student_id, display_name, phone=None, city=None, date_of_birth=None, admission_year=None, group_name=None):
        """
        Обновляет данные студента в таблице группы.
        """
        if not group_name:
            return False
        
        table_name = "group_" + group_name
        update_query = sql.SQL("""
            UPDATE {table}
            SET display_name = %s,
                phone = %s,
                city = %s,
                date_of_birth = %s,
                admission_year = %s
            WHERE id = %s;
        """).format(table=sql.Identifier(table_name))
        
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(update_query, (display_name, phone, city, date_of_birth, admission_year, student_id))
                conn.commit()
                return True
