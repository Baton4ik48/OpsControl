import socket

PORT_LABELS = {
    22:  "SSH",
    443: "HTTPS",
    3389: "RDP",
    20000: "CI",
    9877: "HTTPS",
    80: "HTTP",
}

def check_port(ip, port, timeout=2):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0  # 0 означает успешное подключение
    except Exception:
        return False

def get_label(port):
    return PORT_LABELS.get(port, "OTHER")

# def pluralize_days(days):
#     if days % 10 == 1 and days % 100 != 11:
#         return f"{days} день"
#     elif 2 <= days % 10 <= 4 and (days % 100 < 10 or days % 100 >= 20):
#         return f"{days} дня"
#     else:
#         return f"{days} дней"