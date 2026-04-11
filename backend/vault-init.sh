#!/bin/bash
# =========================================================
# Vault Dev Init Script
# Настраивает Vault с нуля после каждого перезапуска
# =========================================================

VAULT_ADDR="http://127.0.0.1:8200"
VAULT_TOKEN="${VAULT_DEV_ROOT_TOKEN_ID:-myroot}"

export VAULT_ADDR VAULT_TOKEN

echo "⏳ Ожидание Vault..."
until vault status > /dev/null 2>&1; do
  sleep 1
done
echo "✅ Vault доступен"

# =========================================================
# 1. Database Secrets Engine
# =========================================================
echo "📦 Настройка Database engine..."

vault secrets enable database 2>/dev/null

vault write database/config/ppm-db \
  plugin_name=postgresql-database-plugin \
  connection_url="postgresql://{{username}}:{{password}}@postgres:5432/ppm_database?sslmode=disable" \
  allowed_roles="postgres-dynamic" \
  username="login_ppm" \
  password="***REMOVED-SEE-INCIDENT***"

vault write database/roles/postgres-dynamic \
  db_name=ppm-db \
  creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; GRANT app_role TO \"{{name}}\";" \
  default_ttl="1h" \
  max_ttl="24h"

echo "✅ Database engine готов"

# =========================================================
# 2. KV v2 Engine (для паролей к серверам)
# =========================================================
echo "📦 Настройка KV engine..."

vault secrets enable -path=credentials kv-v2 2>/dev/null

echo "✅ KV engine готов"

# =========================================================
# 3. Политики
# =========================================================
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

# =========================================================
# 4. AppRole для бэкенда
# =========================================================
echo "🔑 Настройка AppRole..."

vault auth enable approle 2>/dev/null

vault write auth/approle/role/backend-app \
  token_policies="ppm-db-policy,ppm-admin-policy" \
  token_period=1h \
  token_num_uses=0
  
# Получаем role_id и secret_id
ROLE_ID=$(vault read -field=role_id auth/approle/role/backend-app/role-id)
SECRET_ID=$(vault write -field=secret_id -f auth/approle/role/backend-app/secret-id)

echo "✅ AppRole готов"
echo "   VAULT_ROLE_ID=${ROLE_ID}"
echo "   VAULT_SECRET_ID=${SECRET_ID}"

# =========================================================
# 5. Userpass для администратора
# =========================================================
echo "👤 Настройка Userpass..."

vault auth enable userpass 2>/dev/null

vault write auth/userpass/users/admin \
  password="7946130" \
  policies="ppm-admin-policy"

echo "✅ Userpass готов (login: admin)"

# =========================================================
# ИТОГО
# =========================================================
echo ""
echo "=========================================="
echo "  Vault настроен!"
echo "=========================================="
echo "  VAULT_ROLE_ID=${ROLE_ID}"
echo "  VAULT_SECRET_ID=${SECRET_ID}"
echo "  Admin login: admin"
echo "=========================================="