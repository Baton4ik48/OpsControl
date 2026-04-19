# OpsControl — Production Deployment Guide

---

## 📁 Структура проекта

```
backend/
├── app/
├── vault-config/
├── pg-data/
├── vault-data/
├── .env
├── .dockerignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── vault-init.sh
└── init.sql
```

---
## Шаг 0 — Сборка image backend

docker build -t name-backend:v1.0 .


## 🚀 Шаг 1 — Запуск контейнеров

```bash
cd backend
docker compose up -d
```

Проверка:

```bash
docker compose ps
```

Должно быть:

* *-postgres
* *-vault
* *-backend

---

## 🐘 Шаг 2 — Инициализация PostgreSQL

```bash
cat init.sql | docker compose exec -T postgres psql -U login_ppm -d ppm_database
```

Проверка:

```bash
docker compose exec postgres psql -U login_ppm -d ppm_database -c "\dt"
docker compose exec postgres psql -U login_ppm -d ppm_database -c "\du app_role"
```

---

## 🔐 Шаг 3 — Инициализация Vault (ПЕРВЫЙ ЗАПУСК)

### 1. Init

```bash
docker compose exec vault vault operator init
```

Сохранить:

* Unseal Key 1
* Unseal Key 2
* Unseal Key 3
* Root Token

---

### 2. Unseal (3 раза)

```bash
docker compose exec vault vault operator unseal
```
Должно быть после ввода третьего ключа:

Initialized: true
Sealed: false
---


## ⚙️ Шаг 4 — Настройка Vault

⚠️ Это root токен, только для настройки Vault

```bash
docker compose exec -e VAULT_TOKEN=hvs.cnIkuzn36jdYm72zPS1Crn4N  vault sh /vault-init.sh
```

На выходе получишь:

```
VAULT_ROLE_ID=...
VAULT_SECRET_ID=...
```

---

## 📝 Шаг 5 — Обновить .env

```env
VAULT_ROLE_ID=...
VAULT_SECRET_ID=...
```


---

## 🔄 Шаг 6 — Перезапуск backend

```bash
docker compose up -d --no-deps backend
```

Проверка:

```bash
docker logs ppm-backend
```

Успех:

```
DB creds mode: vault
[VAULT] NEW DB CREDS ISSUED
PostgreSQL pool initialized
```

---

## 🌐 Шаг 7 — Проверка API

```bash
curl http://localhost:8001/api/status
curl http://localhost:8001/api/tree
```


### Если сделал:

```bash
docker compose down -v
```

👉 нужно заново:

1. vault operator init
2. vault operator unseal
3. export VAULT_TOKEN
4. vault-init.sh
5. обновить `.env`

---

## 💣 ВАЖНО

### Root Token

* используется только для init
* НЕ хранится в `.env`
* НЕ используется backend

---

### Backend использует

```env
VAULT_ROLE_ID
VAULT_SECRET_ID
```

---

