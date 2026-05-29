#!/bin/sh
set -e

echo "🔍 Проверка ENV..."

if [ -z "$VAULT_TOKEN" ]; then
  echo "❌ VAULT_TOKEN не установлен"
  exit 1
fi

if [ -z "$POSTGRES_USER" ] || [ -z "$POSTGRES_PASSWORD" ] || [ -z "$VAULT_DATABASE_ROLE_NAME" ]; then
  echo "❌ Не заданы переменные окружения"
  exit 1
fi


# =========================================================
# 1. Database Secrets Engine
# =========================================================

echo "📦 Настройка Database engine..."

vault secrets enable database 2>/dev/null || true

vault write database/config/opscontrol-db \
  plugin_name=postgresql-database-plugin \
  connection_url="postgresql://{{username}}:{{password}}@${POSTGRES_HOST}:5432/${POSTGRES_DB}?sslmode=disable"\
  allowed_roles="${VAULT_DATABASE_ROLE_NAME}" \
  username="${POSTGRES_USER}" \
  password="${POSTGRES_PASSWORD}"

vault write database/roles/${VAULT_DATABASE_ROLE_NAME} \
  db_name=opscontrol-db \
  creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; GRANT app_role TO \"{{name}}\";" \
  default_ttl="1h" \
  max_ttl="24h"

echo "✅ Database engine готов"

# =========================================================
# 2. KV v2 Engine
# =========================================================

echo "📦 Настройка KV engine..."

vault secrets enable -path=credentials kv-v2 2>/dev/null || true

echo "✅ KV engine готов"

# =========================================================
# 3. Политики
# =========================================================

echo "📜 Создание политик..."

vault policy write opscontrol-db-policy - <<EOF
path "database/creds/${VAULT_DATABASE_ROLE_NAME}" {
  capabilities = ["read"]
}
EOF

vault policy write opscontrol-admin-policy - <<EOF
path "credentials/data/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
path "credentials/metadata/*" {
  capabilities = ["list", "read", "delete"]
}
EOF

echo "✅ Политики созданы"

# =========================================================
# 4. AppRole
# =========================================================

echo "🔑 Настройка AppRole..."

vault auth enable approle 2>/dev/null || true

vault write auth/approle/role/backend-app \
  token_policies="opscontrol-db-policy,opscontrol-admin-policy" \
  token_ttl=1h \
  token_max_ttl=4h

# Устанавливаем фиксированные role_id и secret_id из переменных окружения.
# В CI эти значения заданы в variables и переданы в backend-контейнер при старте,
# поэтому бэкенд уже знает их — никакого рестарта не требуется.
vault write auth/approle/role/backend-app/role-id \
  role_id="${VAULT_ROLE_ID}"

vault write auth/approle/role/backend-app/custom-secret-id \
  secret_id="${VAULT_SECRET_ID}"

echo "✅ AppRole готов (role_id=${VAULT_ROLE_ID})"

# =========================================================
# 5. Userpass
# =========================================================

echo "👤 Настройка Userpass..."

vault auth enable userpass 2>/dev/null || true

vault write auth/userpass/users/admin \
  password="${VAULT_ADMIN_PASSWORD}" \
  policies="opscontrol-admin-policy"

echo "✅ Userpass готов"

echo "=========================================="
echo "Vault (DEV) настроен"
echo "=========================================="