#!/bin/sh
# =========================================================
# Vault Production Init Script
# Запускать ТОЛЬКО после init + unseal + login
# =========================================================

set -e

echo "🔍 Проверка VAULT_TOKEN..."

if [ -z "$VAULT_TOKEN" ]; then
  echo "❌ VAULT_TOKEN не установлен"
  exit 1
fi

echo "🔍 Проверка ENV..."

if [ -z "$POSTGRES_USER" ] || [ -z "$POSTGRES_PASSWORD" ] || [ -z "$VAULT_DATABASE_ROLE_NAME" ]; then
  echo "❌ Не заданы переменные окружения (POSTGRES_USER / POSTGRES_PASSWORD / VAULT_DATABASE_ROLE_NAME)"
  exit 1
fi

echo "⏳ Ожидание Vault (init)..."

until vault status 2>/dev/null | grep -q "Initialized.*true"; do
  sleep 2
done

echo "⏳ Ожидание Vault (unseal)..."

until vault status 2>/dev/null | grep -q "Sealed.*false"; do
  sleep 2
done

echo "✅ Vault готов"

# =========================================================
# 1. Database Secrets Engine
# =========================================================
echo "📦 Настройка Database engine..."

vault secrets enable database 2>/dev/null || true

vault write database/config/opscontrol-db \
  plugin_name=postgresql-database-plugin \
  connection_url="postgresql://{{username}}:{{password}}@postgres:5432/${POSTGRES_DB}?sslmode=disable" \
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
# 4. AppRole для backend
# =========================================================
echo "🔑 Настройка AppRole..."

vault auth enable approle 2>/dev/null || true

vault write auth/approle/role/backend-app \
  token_policies="opscontrol-db-policy,opscontrol-admin-policy" \
  token_period=1h \
  token_num_uses=0

ROLE_ID=$(vault read -field=role_id auth/approle/role/backend-app/role-id)
SECRET_ID=$(vault write -field=secret_id -f auth/approle/role/backend-app/secret-id)

echo "✅ AppRole готов"
echo "   VAULT_ROLE_ID=${ROLE_ID}"
echo "   VAULT_SECRET_ID=${SECRET_ID}"

# =========================================================
# 5. Userpass для администратора
# =========================================================
echo "👤 Настройка Userpass..."

vault auth enable userpass 2>/dev/null || true

vault write auth/userpass/users/admin \
  password="${VAULT_ADMIN_PASSWORD}" \
  policies="opscontrol-admin-policy"

echo "✅ Userpass готов (login: admin)"

# =========================================================
# ИТОГО
# =========================================================
echo ""
echo "=========================================="
echo "  Vault настроен (PROD)"
echo "=========================================="
echo "  VAULT_ROLE_ID=${ROLE_ID}"
echo "  VAULT_SECRET_ID=${SECRET_ID}"
echo "  Admin login: admin"
echo "=========================================="