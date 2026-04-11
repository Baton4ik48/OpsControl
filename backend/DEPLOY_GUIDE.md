# PortPassManager — Руководство по развёртыванию

## Структура проекта

```
PortPassManager/
└── backend/
    ├── app/
    ├── config/
    ├── .env
    ├── .dockerignore
    ├── Dockerfile
    ├── docker-compose.yml
    ├── requirements.txt
    ├── vault-init.sh
    └── init.sql
```

---

## Шаг 1 — Запуск контейнеров

```bash
cd backend/
sudo docker compose up -d
```

Проверка:
```bash
sudo docker compose ps
# Все 3 контейнера должны быть Up: ppm-postgres, ppm-vault, ppm-backend
```

---

## Шаг 2 — Инициализация PostgreSQL

```bash
cat init.sql | sudo docker compose exec -T postgres psql -U login_ppm -d ppm_database
```

Проверка:
```bash
sudo docker compose exec postgres psql -U login_ppm -d ppm_database -c "\dt"
# Должно показать: branches, servers, ports, credentials

sudo docker compose exec postgres psql -U login_ppm -d ppm_database -c "\du app_role"
# Должно показать: app_role | Cannot login
```

---

## Шаг 3 — Инициализация Vault

```bash
sudo docker compose exec -e VAULT_ADDR=http://127.0.0.1:8200 -e VAULT_TOKEN=myroot vault sh /vault-init.sh
```

Скрипт выдаст `VAULT_ROLE_ID` и `VAULT_SECRET_ID`.

---

## Шаг 4 — Обновить .env

Вписать полученные значения в `.env`:
```
VAULT_ROLE_ID=<значение из шага 3>
VAULT_SECRET_ID=<значение из шага 3>
```

---

## Шаг 5 — Перезапуск бэкенда

```bash
sudo docker compose stop backend
sudo docker compose up -d backend
sudo docker compose logs backend
```

Успех — в логах:
```
DB creds mode: vault
[VAULT] NEW DB CREDS ISSUED
PostgreSQL pool initialized
Uvicorn running on http://0.0.0.0:8000
```

---

## Шаг 6 — Проверка API

```bash
curl http://localhost:8001/api/status
curl http://localhost:8001/api/tree
```

---

## После каждого docker compose down/up

Vault dev-режим теряет данные. Повторить шаги 3-5:
1. Запустить `vault-init.sh`
2. Обновить `VAULT_ROLE_ID` и `VAULT_SECRET_ID` в `.env`
3. Перезапустить backend

PostgreSQL данные сохраняются в volume `pg_data` и НЕ теряются.

---

## Файлы конфигурации

### init.sql

```sql
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
    ip VARCHAR(45) NOT NULL UNIQUE
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
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
```




### vault-init.sh

```bash
#!/bin/bash
# =========================================================
# Vault Dev Init Script
# =========================================================

VAULT_ADDR="http://127.0.0.1:8200"
VAULT_TOKEN="${VAULT_DEV_ROOT_TOKEN_ID:-myroot}"
export VAULT_ADDR VAULT_TOKEN

echo "⏳ Ожидание Vault..."
until vault status > /dev/null 2>&1; do
  sleep 1
done
echo "✅ Vault доступен"

# --- Database Secrets Engine ---
echo "📦 Настройка Database engine..."
vault secrets enable database 2>/dev/null

vault write database/config/ppm-db \
  plugin_name=postgresql-database-plugin \
  connection_url="postgresql://{{username}}:{{password}}@postgres:5432/ppm_database?sslmode=disable" \
  allowed_roles="postgres-dynamic" \
  username="login_ppm" \
  password="7946130q!"

vault write database/roles/postgres-dynamic \
  db_name=ppm-db \
  creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; GRANT app_role TO \"{{name}}\";" \
  default_ttl="1h" \
  max_ttl="24h"

echo "✅ Database engine готов"

# --- KV v2 Engine ---
echo "📦 Настройка KV engine..."
vault secrets enable -path=credentials kv-v2 2>/dev/null
echo "✅ KV engine готов"

# --- Политики ---
echo "📜 Создание политик..."

vault policy write ppm-db-policy - <<EOF
path "database/creds/postgres-dynamic" {
  capabilities = ["read"]
}
EOF

vault policy write ppm-admin-policy - <<EOF
path "credentials/data/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
path "credentials/metadata/*" {
  capabilities = ["list", "read", "delete"]
}
EOF

echo "✅ Политики созданы"

# --- AppRole ---
echo "🔑 Настройка AppRole..."
vault auth enable approle 2>/dev/null

vault write auth/approle/role/backend-app \
  token_policies="ppm-db-policy" \
  token_period=1h \
  token_num_uses=0

ROLE_ID=$(vault read -field=role_id auth/approle/role/backend-app/role-id)
SECRET_ID=$(vault write -field=secret_id -f auth/approle/role/backend-app/secret-id)

echo "✅ AppRole готов"
echo "   VAULT_ROLE_ID=${ROLE_ID}"
echo "   VAULT_SECRET_ID=${SECRET_ID}"

# --- Userpass ---
echo "👤 Настройка Userpass..."
vault auth enable userpass 2>/dev/null

vault write auth/userpass/users/admin \
  password="7946130" \
  policies="ppm-admin-policy"

echo "✅ Userpass готов (login: admin)"

# --- Итого ---
echo ""
echo "=========================================="
echo "  Vault настроен!"
echo "=========================================="
echo "  VAULT_ROLE_ID=${ROLE_ID}"
echo "  VAULT_SECRET_ID=${SECRET_ID}"
echo "  Admin login: admin"
echo "=========================================="
```

### docker-compose.yml

```yaml
version: "3.8"
services:
  postgres:
    image: postgres:16
    container_name: ppm-postgres
    restart: always
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - pg_data:/var/lib/postgresql/data
    ports:
      - "5433:5432"

  vault:
    image: hashicorp/vault:1.15
    container_name: ppm-vault
    restart: always
    environment:
      VAULT_DEV_ROOT_TOKEN_ID: ${VAULT_DEV_ROOT_TOKEN_ID}
      VAULT_DEV_LISTEN_ADDRESS: "0.0.0.0:8200"
    volumes:
      - vault_data:/vault/file
      - ./vault-init.sh:/vault-init.sh:ro
    ports:
      - "8200:8200"
    cap_add:
      - IPC_LOCK

  backend:
    build: .
    container_name: ppm-backend
    restart: always
    depends_on:
      - postgres
      - vault
    env_file:
      - .env
    environment:
      POSTGRES_HOST: postgres
      VAULT_ADDR: http://vault:8200
    volumes:
      - ./.env:/app/.env:ro
    ports:
      - "8001:8000"

volumes:
  pg_data:
  vault_data:
```

### .env (шаблон)

```env
APP_ENV=dev

# Vault
VAULT_HTTP_TIMEOUT=2
VAULT_ADDR=http://vault:8200
VAULT_AUTH_METHOD=approle
VAULT_ROLE_ID=<заполнить после vault-init.sh>
VAULT_SECRET_ID=<заполнить после vault-init.sh>
VAULT_DEV_ROOT_TOKEN_ID=myroot
VAULT_DATABASE_ROLE_NAME=postgres-dynamic

# PostgreSQL
DB_CREDS_MODE=vault
POSTGRES_CONNECT_TIMEOUT=5
POSTGRES_QUERY_TIMEOUT=3
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=ppm_database
POSTGRES_USER=login_ppm
POSTGRES_PASSWORD=7946130q!
```

### Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### .dockerignore

```
.env
__pycache__
*.pyc
.git
```

---

## Для офлайн-сервера (Astra Linux, production Vault)

На офлайн-сервере Vault работает в production-режиме (не dev).
Отличия:
- Используется `vault-config/config.hcl` вместо `VAULT_DEV_*`
- Нужна инициализация: `vault operator init`
- Нужна распечатка: `vault operator unseal`
- Данные НЕ теряются при перезапуске
- `vault-init.sh` запускается только один раз после первой инициализации

### vault-config/config.hcl (для production)

```hcl
storage "file" {
  path = "/vault/data"
}

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 1
}

api_addr = "http://vault:8200"

disable_mlock = true
ui            = true
```

### docker-compose.yml секция vault (для production)

```yaml
  vault:
    image: hashicorp/vault:1.15
    restart: always
    user: root
    environment:
      SKIP_SETCAP: "true"
    volumes:
      - vault_data:/vault/data
      - ./vault-config:/vault/config
      - ./vault-init.sh:/vault-init.sh:ro
    ports:
      - "8200:8200"
    cap_add:
      - IPC_LOCK
    command: vault server -config=/vault/config/config.hcl
```
