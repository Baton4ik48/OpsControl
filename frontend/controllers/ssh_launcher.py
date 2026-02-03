import subprocess
import sys

class SshLauncher:
    @staticmethod
    def open(user: str, host: str):
        if sys.platform.startswith("win"):
            subprocess.Popen([
                "cmd",
                "/c",
                "start",
                "powershell",
                "-NoExit",
                f"ssh {user}@{host}"
            ])

        elif sys.platform.startswith("linux"):
            subprocess.Popen([
                "x-terminal-emulator",
                "-e",
                f"ssh {user}@{host}"
            ])

        elif sys.platform.startswith("darwin"):
            subprocess.Popen([
                "open",
                "-a", "Terminal",
                f"ssh {user}@{host}"
            ])
