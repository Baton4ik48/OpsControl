from prometheus_client import Counter, Gauge

vault_renew_total = Counter(
    "vault_renew_total",
    "Результаты попыток продления Vault-токена",
    ["result"],
)

vault_renew_last_success_timestamp = Gauge(
    "vault_renew_last_success_timestamp",
    "Unix-время последнего успешного продления Vault-токена",
)

login_failed_total = Counter(
    "login_failed_total",
    "Количество неудачных попыток логина",
)

login_blocked_total = Counter(
    "login_blocked_total",
    "Количество срабатываний блокировки login throttle",
)

db_pool_reinit_total = Counter(
    "db_pool_reinit_total",
    "Количество пересозданий пула соединений PostgreSQL после ошибки",
)
