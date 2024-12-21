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
                    group_name VARCHAR(100) NOT NULL
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

    def create_user(self, username, password_hash, display_name, group_name):
        insert_user = """
        INSERT INTO users (username, password_hash, display_name, group_name)
        VALUES (%s, %s, %s, %s) RETURNING id;
        """
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(insert_user, (username, password_hash, display_name, group_name))
                user_id = cur.fetchone()[0]
                conn.commit()
                return user_id

    def get_user(self, username):
        query = "SELECT id, username, password_hash, display_name, group_name FROM users WHERE username = %s;"
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
                # Создаем таблицу для группы
                create_group_table = sql.SQL("""
                CREATE TABLE IF NOT EXISTS {table} (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(100) NOT NULL,
                    display_name VARCHAR(100) NOT NULL
                );
                """).format(table=sql.Identifier("group_" + group_name))
                cur.execute(create_group_table)
                conn.commit()

    def add_user_to_group(self, username, display_name, group_name):
        table_name = "group_" + group_name
        insert_member = sql.SQL("INSERT INTO {table} (username, display_name) VALUES (%s, %s);").format(
            table=sql.Identifier(table_name)
        )
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(insert_member, (username, display_name))
                conn.commit()

    def get_group_members(self, group_name):
        if not self.group_exists(group_name):
            return []
        table_name = "group_" + group_name
        query = sql.SQL("SELECT id, username, display_name FROM {table} ORDER BY id;").format(
            table=sql.Identifier(table_name)
        )
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                return cur.fetchall()

    def get_all_groups(self):
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT group_name FROM groups_list ORDER BY group_name;")
                return [row[0] for row in cur.fetchall()]
