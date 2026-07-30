#!/usr/bin/env python3
"""
Ansible dynamic inventory: тянет список серверов и SSH-креды из opscontrol
backend (не из Vault напрямую — единая точка входа для админской машины).

Та же модель авторизации, что у Frontend: постоянных токенов нет, доступ
невозможен без мастер-пароля. Пароль запрашивается интерактивно (getpass)
при каждом запуске и живёт только в памяти этого процесса — нигде не
сохраняется и не логируется.

Настройка (только адрес бэкенда):
    export OPSCONTROL_BACKEND_URL="https://backend.internal/api"
    # опционально, иначе будет запрошен интерактивно:
    export OPSCONTROL_ANSIBLE_USER="admin"

Использование:
    ansible-inventory -i inventory_opscontrol.py --list
    ansible-playbook -i inventory_opscontrol.py site.yml

Перед запуском также стоит явно выставить (см. ansible-env.sh рядом):
    export ANSIBLE_CACHE_PLUGIN=memory
    export ANSIBLE_RETRY_FILES_ENABLED=False
чтобы Ansible не писал факты/секреты на диск через ansible.cfg.
"""

import argparse
import getpass
import json
import os
import sys
import urllib.error
import urllib.request

BACKEND_URL = os.environ.get("OPSCONTROL_BACKEND_URL", "").rstrip("/")
TIMEOUT = int(os.environ.get("OPSCONTROL_TIMEOUT", "10"))


def _post(path: str, payload: dict) -> dict:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{BACKEND_URL}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return _send(req)


def _get(path: str, token: str) -> dict:
    req = urllib.request.Request(
        f"{BACKEND_URL}{path}",
        headers={"Authorization": f"Bearer {token}"},
    )
    return _send(req)


def _send(req: urllib.request.Request) -> dict:
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        print(f"Backend returned {e.code}: {detail}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Cannot reach backend at {BACKEND_URL}: {e}", file=sys.stderr)
        sys.exit(1)


def fetch_inventory() -> dict:
    if not BACKEND_URL:
        print("OPSCONTROL_BACKEND_URL is not set", file=sys.stderr)
        sys.exit(1)

    username = os.environ.get("OPSCONTROL_ANSIBLE_USER") or input("Vault username: ")
    master_password = getpass.getpass("Master password: ")

    try:
        login = _post(
            "/inventory/ansible/login",
            {"username": username, "master_password": master_password},
        )
    finally:
        del master_password 

    token = login["data"]["token"]

    return _get("/inventory/ansible", token)


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="Ansible calls this to get the full inventory")
    group.add_argument("--host", help="Ansible calls this per-host when hostvars aren't inlined under --list")
    args = parser.parse_args()

    inventory = fetch_inventory()

    if args.list:
        print(json.dumps(inventory))
    else:
        hostvars = inventory.get("_meta", {}).get("hostvars", {})
        print(json.dumps(hostvars.get(args.host, {})))


if __name__ == "__main__":
    main()
