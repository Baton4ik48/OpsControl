import subprocess
import sys
import shutil
import threading
import webbrowser
import os

class ProtocolLauncher:

    @staticmethod
    def open(protocol: str, user: str, password: str, host: str, port: int):

        if protocol == "ssh":
            ProtocolLauncher._open_ssh(user, password, host, port)

        elif protocol == "rdp":
            ProtocolLauncher._open_rdp(user, password, host)

        elif protocol in ("http", "https"):
            ProtocolLauncher._open_web(protocol, host, port)

        else:
            raise RuntimeError("UNSUPPORTED_PROTOCOL")

    @staticmethod
    def _open_ssh(user, password, host, port):

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
            if user and password:
                if not shutil.which("sshpass"):
                    raise RuntimeError("SSHPASS_NOT_FOUND")
                subprocess.Popen(
                    [
                        "x-terminal-emulator", "-e", "bash", "-c",
                        f"sshpass -p '{password}' ssh -o StrictHostKeyChecking=no -p {port} {user}@{host}; exec bash",
                    ]
                )
            else:
                # Без учётных данных — обычный SSH, пользователь введёт сам
                target = f"{user}@{host}" if user else host
                subprocess.Popen(
                    [
                        "x-terminal-emulator", "-e", "bash", "-c",
                        f"ssh -o StrictHostKeyChecking=no -p {port} {target}; exec bash",
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
                        "-u", user,
                        "-p", password,
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
