import subprocess
import sys
import shutil


class ProtocolLauncher:

    @staticmethod
    def open(protocol: str, user: str, password: str, host: str, port: int):

        if protocol == "ssh":
            ProtocolLauncher._open_ssh(user, password, host, port)

        elif protocol == "rdp":
            ProtocolLauncher._open_rdp(user, password, host)

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