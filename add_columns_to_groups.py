# add_columns_to_groups.py

import psycopg2
from psycopg2 import sql

# Конфигурация подключения к БД
db_config = {
    'dbname': 'kursach',
    'user': 'postgres',
    'password': 'root',  # Замените на ваш пароль
    'host': 'localhost',
    'port': '5432'
}

def add_columns_to_group_tables():
    try:
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        
        # Получение списка всех групп
        cur.execute("SELECT group_name FROM groups_list;")
        groups = [row[0] for row in cur.fetchall()]
        
        for group in groups:
            table_name = f"group_{group}"
            
            # Формирование SQL-запроса для добавления столбцов
            alter_table_query = sql.SQL("""
                ALTER TABLE {table}
                ADD COLUMN IF NOT EXISTS phone VARCHAR(20),
                ADD COLUMN IF NOT EXISTS city VARCHAR(100),
                ADD COLUMN IF NOT EXISTS date_of_birth DATE,
                ADD COLUMN IF NOT EXISTS admission_year INTEGER;
            """).format(table=sql.Identifier(table_name))
            
            cur.execute(alter_table_query)
            print(f"Столбцы добавлены в таблицу {table_name}")
        
        conn.commit()
        cur.close()
        conn.close()
        print("Все таблицы групп обновлены успешно.")
        
    except Exception as e:
        print("Ошибка при обновлении таблиц групп:", e)

if __name__ == "__main__":
    add_columns_to_group_tables()
