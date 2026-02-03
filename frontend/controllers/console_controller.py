from core.ssh.ssh_client import SshClient
import socket

class ConsoleController:
    def __init__(self, output_callback):
        self.out = output_callback
        self.ssh = SshClient()

    def handle(self, command: str):
        command = command.strip()
        if not command:
            return

        parts = command.split()
        cmd = parts[0]
        args = parts[1:]

        if cmd == "help":
            self._help()
        elif cmd == "clear":
            self.out("__clear__")
        elif cmd == "ssh":
            self._ssh(args)
        else:
            self.out(f"Неизвестная команда: {cmd}")

    # =========================
    # HELP
    # =========================
    def _help(self):
        self.out("Доступные команды:")
        self.out("  ssh user@host password command")
        self.out("  clear")
        self.out("  help")

    # =========================
    # SSH
    # =========================
    def _ssh(self, args):
        if len(args) < 3:
            self.out("Использование: ssh user@host password command")
            return

        user_host = args[0]
        password = args[1]
        command = " ".join(args[2:])

        if "@" not in user_host:
            self.out("Ошибка: формат user@host")
            return

        username, host = user_host.split("@", 1)

        self.out(f"$ {command}")

        try:
            out, err = self.ssh.exec(
                host=host,
                username=username,
                password=password,
                command=command
            )

            if out:
                self.out(out.rstrip())
            if err:
                self.out(f"[stderr]\n{err.rstrip()}")

        except socket.timeout:
            self.out("Ошибка: таймаут подключения")
        except Exception as e:
            self.out(f"SSH error: {e}")
