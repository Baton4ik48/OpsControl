from core.ssh.common import connect_or_raise

DEFAULT_TIMEOUT = 10

# Ключ пункта меню "Своя команда..." — не входит в CHECKS,
# обрабатывается отдельно контроллером (запрашивает текст у пользователя).
CUSTOM_CHECK_KEY = "__custom__"

# Фиксированный набор read-only проверок для линукс-серверов (порт 22).
# key -> (человекочитаемое имя, shell-команда). Только чтение — ничего не
# меняет на сервере.
CHECKS: dict[str, tuple[str, str]] = {
    "os_release": ("Версия ОС / ядро", "cat /etc/os-release; uname -r"),
    "uptime": ("Аптайм", "uptime"),
    "disk": ("Диск", "df -h"),
    "memory": ("Память", "free -h"),
    "accounts": ("Локальные учётки", "awk -F: '$3>=1000{print $1, $3}' /etc/passwd"),
    "root_login": ("Root-логин по SSH", "sshd -T 2>/dev/null | grep -i permitrootlogin"),
    "listening_ports": ("Слушающие порты", "ss -tlnp"),
    "failed_units": ("Упавшие systemd-юниты", "systemctl --failed"),
    "last_logins": ("Последние входы", "last -n 20"),
}


def run_check(ip: str, port: int, username: str, password: str, command: str) -> str:
    """Выполняет одну команду по SSH, возвращает stdout (+ stderr, если он не пуст)."""
    client = connect_or_raise(ip, port, username, password, DEFAULT_TIMEOUT)
    try:
        _, stdout, stderr = client.exec_command(command, timeout=DEFAULT_TIMEOUT)
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
    finally:
        client.close()

    if err.strip():
        return f"{out}\n--- stderr ---\n{err}"
    return out
