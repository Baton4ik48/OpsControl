import subprocess
import sys
import shutil
import threading
import webbrowser
import os

# Старые Nateks-коммутаторы поддерживают только устаревшие SSH-алгоритмы,
# которые современный OpenSSH-клиент на Linux по умолчанию отключил
# (ssh-rsa host key, diffie-hellman-group1-sha1, 3des-cbc). Без явного
# разрешения этих алгоритмов подключение с Linux падает ещё на этапе
# согласования — на Windows проблемы не было, т.к. там PuTTY/KiTTY,
# у которых легаси-алгоритмы включены по умолчанию.
_NATEKS_LEGACY_SSH_OPTS = (
    "-o HostKeyAlgorithms=+ssh-rsa "
    "-o PubkeyAcceptedAlgorithms=+ssh-rsa "
    "-o KexAlgorithms=+diffie-hellman-group1-sha1 "
    "-o Ciphers=3des-cbc "
    "-o PubkeyAuthentication=no"
)


class ProtocolLauncher:

    @staticmethod
    def open(
        protocol: str,
        user: str,
        password: str,
        host: str,
        port: int,
        device_type: str = "linux",
    ):

        if protocol == "ssh":
            ProtocolLauncher._open_ssh(user, password, host, port, device_type)

        elif protocol == "rdp":
            ProtocolLauncher._open_rdp(user, password, host)

        elif protocol in ("http", "https"):
            ProtocolLauncher._open_web(protocol, host, port)

        else:
            raise RuntimeError("UNSUPPORTED_PROTOCOL")

    @staticmethod
    def _open_ssh(user, password, host, port, device_type="linux"):

        if sys.platform.startswith("win"):
            client = shutil.which("kitty") or shutil.which("putty")
            if not client:
                raise RuntimeError("PUTTY_NOT_FOUND")

            if user and password:
                # Автологин с паролем
                subprocess.Popen(
                    [client, "-ssh", f"{user}@{host}", "-P", str(port), "-pw", password]
                )
            else:
                # Без учётных данных — открываем терминал, пользователь введёт сам
                cmd = [client, "-ssh", host, "-P", str(port)]
                if user:
                    cmd = [client, "-ssh", f"{user}@{host}", "-P", str(port)]
                subprocess.Popen(cmd)

        elif sys.platform.startswith("linux"):
            extra_opts = (
                f" {_NATEKS_LEGACY_SSH_OPTS}"
                if device_type in ("nateks", "natex")
                else ""
            )

            if user and password:
                if not shutil.which("sshpass"):
                    raise RuntimeError("SSHPASS_NOT_FOUND")
                subprocess.Popen(
                    [
                        "x-terminal-emulator",
                        "-e",
                        "bash",
                        "-c",
                        f"sshpass -p '{password}' ssh -o StrictHostKeyChecking=no{extra_opts} -p {port} {user}@{host}; exec bash",
                    ]
                )
            else:
                # Без учётных данных — обычный SSH, пользователь введёт сам
                target = f"{user}@{host}" if user else host
                subprocess.Popen(
                    [
                        "x-terminal-emulator",
                        "-e",
                        "bash",
                        "-c",
                        f"ssh -o StrictHostKeyChecking=no{extra_opts} -p {port} {target}; exec bash",
                    ]
                )

    @staticmethod
    def _open_rdp(user, password, host):

        if sys.platform.startswith("win"):
            subprocess.run(
                [
                    "cmdkey",
                    f"/generic:TERMSRV/{host}",
                    f"/user:{user}",
                    f"/pass:{password}",
                ],
                check=False,
            )
            proc = subprocess.Popen(["mstsc", f"/v:{host}"])

            # Ждём завершения mstsc и чистим credential в фоне,
            # чтобы не блокировать главный поток и UI.
            def _cleanup():
                proc.wait()
                subprocess.run(["cmdkey", f"/delete:TERMSRV/{host}"], check=False)

            threading.Thread(target=_cleanup, daemon=True).start()

        elif sys.platform.startswith("linux"):
            # remmina  — GUI-клиент, поддерживает rdp:// URI
            # xfreerdp — консольный (пакет freerdp2-x11 / freerdp3-x11)
            # rdesktop — запасной вариант (пакет rdesktop)
            if shutil.which("remmina"):
                subprocess.Popen(
                    [
                        "remmina",
                        "-c",
                        f"rdp://{user}:{password}@{host}",
                    ]
                )
            elif shutil.which("xfreerdp"):
                subprocess.Popen(
                    [
                        "xfreerdp",
                        f"/v:{host}",
                        f"/u:{user}",
                        f"/p:{password}",
                        "/dynamic-resolution",
                        "+clipboard",
                        "/cert:ignore",
                    ]
                )
            elif shutil.which("rdesktop"):
                subprocess.Popen(
                    [
                        "rdesktop",
                        "-u",
                        user,
                        "-p",
                        password,
                        host,
                    ]
                )
            else:
                raise RuntimeError("RDP_CLIENT_NOT_FOUND")

        else:
            raise RuntimeError("RDP_UNSUPPORTED_OS")

    @staticmethod
    def _open_web(protocol, host, port):
        url = f"{protocol}://{host}:{port}"
        webbrowser.open(url)

    @staticmethod
    def open_external(app_path: str):

        if not os.path.exists(app_path):
            raise RuntimeError("EXTERNAL_APP_NOT_FOUND")

        try:
            subprocess.Popen([app_path])
        except Exception as e:
            raise RuntimeError(f"EXTERNAL_APP_LAUNCH_FAILED: {e}")
