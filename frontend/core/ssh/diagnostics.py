from core.ssh.common import connect_or_raise

DEFAULT_TIMEOUT = 10

# Ключ пункта меню "Своя команда..." — не входит в CHECKS,
# обрабатывается отдельно контроллером (запрашивает текст у пользователя).
CUSTOM_CHECK_KEY = "__custom__"

# Фиксированный набор read-only проверок для линукс-серверов (порт 22).
# key -> (человекочитаемое имя, shell-команда, файл иконки в resources/icons).
# Только чтение — ничего не меняет на сервере.
CHECKS: dict[str, tuple[str, str, str]] = {
    "os_release": ("Версия ОС / ядро", "cat /etc/os-release; uname -r", "os_release_image.png"),
    "uptime": ("Аптайм", "uptime", "uptime_image.png"),
    "disk": ("Диск", "df -h", "disk_image.png"),
    "memory": ("Память", "free -h", "memory_image.png"),
    "top": ("Топ процессов", "top -bn1 | head -n 20", "top_image.png"),
    "accounts": (
        "Локальные учётки",
        "awk -F: '$3>=1000{print $1, $3}' /etc/passwd",
        "accounts_image.png",
    ),
    "listening_ports": ("Слушающие порты", "ss -tlnp", "listening_ports_image.png"),
    "failed_units": ("Упавшие systemd-юниты", "systemctl --failed", "failed_units_image.png"),
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
