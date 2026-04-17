
-- =========================================================
-- ТАБЛИЦЫ
-- =========================================================

CREATE TABLE IF NOT EXISTS branches (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS servers (
    id SERIAL PRIMARY KEY,
    branch_id INTEGER NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    ip VARCHAR(45) NOT NULL UNIQUE,
    device_type VARCHAR(32) NOT NULL DEFAULT 'linux'
);

CREATE TABLE IF NOT EXISTS ports (
    server_id INTEGER NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
    port INTEGER NOT NULL,
    last_success TIMESTAMP,
    last_failure TIMESTAMP,
    PRIMARY KEY (server_id, port)
);

CREATE TABLE IF NOT EXISTS credentials (
    id SERIAL PRIMARY KEY,
    server_id INTEGER NOT NULL,
    port INTEGER NOT NULL,
    vault_path VARCHAR(512) NOT NULL,
    updated_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    UNIQUE (server_id, port),
    FOREIGN KEY (server_id, port) REFERENCES ports(server_id, port) ON DELETE CASCADE
);

-- =========================================================
-- РОЛЬ ДЛЯ ПРИЛОЖЕНИЯ
-- =========================================================
CREATE ROLE app_role;
GRANT app_role TO login_ppm;

-- =========================================================
-- ПРАВА ДЛЯ app_role
-- =========================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_role;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO app_role;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO app_role;