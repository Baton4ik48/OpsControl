import subprocess
import sys
import shutil
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

    # =========================
    # SSH
    # =========================
    @staticmethod
    def _open_ssh(user, password, host, port):

        if sys.platform.startswith("win"):

            if not shutil.which("plink"):
                raise RuntimeError("PLINK_NOT_FOUND")

            subprocess.Popen([
                "cmd",
                "/c",
                "start",
                "cmd",
                "/k",
                "plink",
                "-ssh",
                f"{user}@{host}",
                "-P",
                str(port),
                "-pw",
                password
            ])

        elif sys.platform.startswith("linux"):

            if not shutil.which("sshpass"):
                raise RuntimeError("SSHPASS_NOT_FOUND")

            subprocess.Popen([
                "x-terminal-emulator",
                "-e",
                "sshpass",
                "-p",
                password,
                "ssh",
                "-p",
                str(port),
                f"{user}@{host}"
            ])

    # =========================
    # RDP
    # =========================
    @staticmethod
    def _open_rdp(user, password, host):

        if not sys.platform.startswith("win"):
            raise RuntimeError("RDP_ONLY_WINDOWS")
        subprocess.run([
            "cmdkey",
            f"/generic:TERMSRV/{host}",
            f"/user:{user}",
            f"/pass:{password}"
        ], check=False)

        try:
            proc = subprocess.Popen([
                "mstsc",
                f"/v:{host}"
            ])

            proc.wait()

        finally:
            subprocess.run([
                "cmdkey",
                f"/delete:TERMSRV/{host}"
            ], check=False)
    # =========================
    # WEB
    # =========================
    @staticmethod
    def _open_web(protocol, host, port):
        url = f"{protocol}://{host}:{port}"
        webbrowser.open(url)

    # =========================
    # EXTERNAL APP
    # =========================
    @staticmethod
    def open_external(app_path: str):

        if not os.path.exists(app_path):
            raise RuntimeError("EXTERNAL_APP_NOT_FOUND")

        try:
            subprocess.Popen([app_path])
        except Exception as e:
            raise RuntimeError(f"EXTERNAL_APP_LAUNCH_FAILED: {e}")