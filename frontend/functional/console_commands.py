import paramiko
import socket
import threading

class ConsoleCommands:
    def __init__(self, output_callback):
        self.out = output_callback

        # SSH state
        self.ssh_client = None
        self.ssh_channel = None
        self.waiting_password = False
        self.ssh_connect_info = None  # (user, host, port)

    # =========================================================
    #                 SSH — инициатор
    # =========================================================
    def ssh(self, args):
        if len(args) == 0:
            self.out("Использование: ssh user@host")
            return

        conn = args[0]

        if "@" not in conn:
            self.out("Ошибка: формат должен быть user@host")
            return

        username, host = conn.split("@", 1)

        port = 22

        self.ssh_connect_info = (username, host, port)
        self.waiting_password = True

        self.out("Password: ")   # ввод скрыт в ConsoleWidget

    # =========================================================
    #                SSH — подключение
    # =========================================================
    def ssh_connect(self, password):
        username, host, port = self.ssh_connect_info

        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            client.connect(
                hostname=host,
                port=port,
                username=username,
                password=password,
                timeout=5,
                allow_agent=False,
                look_for_keys=False
            )

            self.out("\n=== SSH подключение установлено ===")

            channel = client.invoke_shell()
            self.ssh_client = client
            self.ssh_channel = channel

            # Запуск потока чтения
            threading.Thread(target=self.read_ssh_output, daemon=True).start()

        except socket.timeout:
            self.out("\nОшибка: таймаут подключения.")
        except paramiko.ssh_exception.AuthenticationException:
            self.out("\nОшибка: неверный пароль.")
        except Exception as e:
            self.out(f"\nОшибка SSH: {e}")

        self.waiting_password = False
        self.ssh_connect_info = None

    # =========================================================
    #     Читаем поток SSH и выводим его в консоль
    # =========================================================
    def read_ssh_output(self):
        try:
            while True:
                if self.ssh_channel.recv_ready():
                    data = self.ssh_channel.recv(4096)
                    if not data:
                        break
                    self.out(data.decode(errors="ignore"))

                if self.ssh_channel.closed:
                    break
        except:
            pass

        self.out("\n=== SSH соединение закрыто ===")
        self.ssh_channel = None
        self.ssh_client = None

    # =========================================================
    #         Передача команд в SSH
    # =========================================================
    def ssh_send(self, text):
        if self.ssh_channel:
            self.ssh_channel.send(text + "\n")

    # =========================================================
    #     CLEAR
    # =========================================================
    def clear(self, args):
        self.out("__clear_console__")

    # =========================================================
    #     HELP
    # =========================================================
    def help(self, args):
        self.out("Доступные команды:")
        self.out("  ssh user@host     – подключение по SSH")
        self.out("  clear             – очистить консоль")
        self.out("  help              – список команд")

    # =========================================================
    #      ОСНОВНАЯ ЛОГИКА ОБРАБОТКИ ВВОДА
    # =========================================================
    def handle(self, command: str):
        # режим ввода пароля
        if self.waiting_password:
            self.ssh_connect(command)
            return

        # режим SSH
        if self.ssh_channel:
            self.ssh_send(command)
            return

        # обычный режим
        parts = command.split()
        if not parts:
            return

        cmd = parts[0]
        args = parts[1:]

        if cmd == "ssh":
            self.ssh(args)
        elif cmd == "clear":
            self.clear(args)
        elif cmd == "help":
            self.help(args)
        else:
            self.out(f"Неизвестная команда: {cmd}. Напишите help")
