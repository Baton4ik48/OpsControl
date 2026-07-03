from core.ssh.interactive import rotate_cli_password, wait_prompt, wait_prompt_either


def rotate_cisco_password(
    host: str,
    username: str,
    current_password: str,
    new_password: str,
    port: int = 22,
    timeout: int = 15,
) -> None:
    """
    Меняет пароль пользователя на коммутаторе Cisco 2960/2950 через интерактивный SSH.

    Последовательность команд:
      connect → hostname> (privilege 1) или hostname# (privilege 15) →
      [если >]: enable → hostname# →
      configure terminal → hostname(config)# →
      username <user> password <pass> → hostname(config)# →
      end     → hostname# →
      write memory → hostname# → disconnect

    Cisco IOS использует стандартный промпт `hostname(config)#`.
    Команда входа в конфиг: `configure terminal` (не `config`).
    Команда сохранения: `write memory`.

    ВАЖНО: пароль передаётся plaintext напрямую в CLI-команду.
    Не используется shlex.quote — CLI устройства не является shell,
    кавычки были бы приняты как часть пароля.

    Бросает SSHRotateError во всех случаях неуспеха.
    """

    def flow(channel, t):
        # Cisco с privilege 15 сразу даёт '#', с privilege 1 — '>'
        initial = wait_prompt_either(channel, (">", "#"), t)

        if initial == ">":
            channel.send("enable\n")
            wait_prompt(channel, "#", t)

        channel.send("configure terminal\n")
        wait_prompt(channel, "(config)#", t)

        channel.send(f"username {username} password {new_password}\n")
        wait_prompt(channel, "(config)#", t)

        # end — выходим сразу в privileged exec, минуя промежуточные уровни
        channel.send("end\n")
        wait_prompt(channel, "#", t)

        # Сохранение running-config → startup-config
        channel.send("write memory\n")
        wait_prompt(channel, "#", t)

    rotate_cli_password(
        host,
        username,
        current_password,
        new_password,
        port,
        timeout,
        flow,
        save_command="write memory",
    )
