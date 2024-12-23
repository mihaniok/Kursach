-- docker-init/init.sql

-- Создание таблицы users
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

-- Создание таблицы groups_list
CREATE TABLE IF NOT EXISTS groups_list (
    group_name VARCHAR(100) PRIMARY KEY
);

-- Добавление существующих групп (пример)
INSERT INTO groups_list (group_name) VALUES ('CS101') ON CONFLICT DO NOTHING;
INSERT INTO groups_list (group_name) VALUES ('CS102') ON CONFLICT DO NOTHING;

-- Создание таблиц для групп
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'group_CS101') THEN
        CREATE TABLE group_CS101 (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) NOT NULL,
            display_name VARCHAR(100) NOT NULL,
            phone VARCHAR(20),
            city VARCHAR(100),
            date_of_birth DATE,
            admission_year INTEGER
        );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'group_CS102') THEN
        CREATE TABLE group_CS102 (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) NOT NULL,
            display_name VARCHAR(100) NOT NULL,
            phone VARCHAR(20),
            city VARCHAR(100),
            date_of_birth DATE,
            admission_year INTEGER
        );
    END IF;
END
$$;
