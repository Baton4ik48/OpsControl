from core.ssh.interactive import rotate_cli_password, wait_prompt


def rotate_nateks_password(
    host: str,
    username: str,
    current_password: str,
    new_password: str,
    port: int = 22,
    timeout: int = 15,
) -> None:
    """
    Меняет пароль пользователя на коммутаторе Nateks через интерактивный SSH.

    Последовательность команд:
      connect → hostname> → enable → hostname# →
      config  → hostname_config# →
      username <user> password <pass> → hostname_config# →
      exit    → hostname# →
      write   → hostname# → disconnect

    Nateks NTX-серия использует промпт вида `hostname_config#`,
    а не Cisco-стиль `hostname(config)#`.

    ВАЖНО: пароль передаётся plaintext напрямую в CLI-команду.
    Не используется shlex.quote — CLI устройства не является shell,
    кавычки были бы приняты как часть пароля.

    Бросает SSHRotateError во всех случаях неуспеха.
    """

    def flow(channel, t):
        wait_prompt(channel, ">", t)

        channel.send("enable\n")
        wait_prompt(channel, "#", t)

        channel.send("config\n")
        wait_prompt(channel, "config#", t)

        channel.send(f"username {username} password {new_password}\n")
        wait_prompt(channel, "config#", t)

        channel.send("exit\n")
        wait_prompt(channel, "#", t)

        # Сохранение running-config → startup-config
        channel.send("write\n")
        wait_prompt(channel, "#", t)

    rotate_cli_password(
        host,
        username,
        current_password,
        new_password,
        port,
        timeout,
        flow,
        save_command="write",
    )
