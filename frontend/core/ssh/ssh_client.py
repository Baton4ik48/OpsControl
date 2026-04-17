import paramiko


class SshClient:
    def __init__(self, timeout=5):
        self.timeout = timeout

    def exec(self, host, username, password, command, port=22):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            client.connect(
                hostname=host,
                port=port,
                username=username,
                password=password,
                timeout=self.timeout,
                allow_agent=False,
                look_for_keys=False,
            )

            stdin, stdout, stderr = client.exec_command(command)

            out = stdout.read().decode(errors="ignore")
            err = stderr.read().decode(errors="ignore")

            return out, err

        finally:
            client.close()
