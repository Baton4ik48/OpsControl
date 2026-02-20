import subprocess
import sys
import shutil

class SshLauncher:

    @staticmethod
    def _check_binary(name: str) -> bool:
        return shutil.which(name) is not None

    @staticmethod
    def open(user: str, password: str, host: str):

        if sys.platform.startswith("win"):

            if not SshLauncher._check_binary("plink"):
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
                "-pw",
                password
            ])

        elif sys.platform.startswith("linux"):

            if not SshLauncher._check_binary("sshpass"):
                raise RuntimeError("SSHPASS_NOT_FOUND")

            subprocess.Popen([
                "x-terminal-emulator",
                "-e",
                "sshpass",
                "-p",
                password,
                "ssh",
                f"{user}@{host}"
            ])