import logging
import re

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services.ansible_session import issue_session, verify_session
from app.services.credentials import (
    verify_admin_password,
    InvalidMasterPassword,
    TooManyLoginAttempts,
)
from app.services.db.credentials_db import get_all_credentials_with_server_info
from app.services.vault_client import get_vault_client, VaultReadError

logger = logging.getLogger("inventory.api")
_audit = logging.getLogger("audit")

router = APIRouter(prefix="/inventory", tags=["inventory"])


def _ctx(request: Request) -> tuple[str, str]:
    ip = getattr(request.state, "client_ip", None) or (
        request.client.host if request.client else "unknown"
    )
    rid = getattr(request.state, "request_id", "-")
    return ip, rid


def _require_session(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    username = verify_session(auth.removeprefix("Bearer ").strip())
    if not username:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")

    return username

_RU_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def _slug(name: str) -> str:
    transliterated = "".join(_RU_TRANSLIT.get(ch, ch) for ch in name.lower())
    slug = re.sub(r"[^a-z0-9]+", "_", transliterated).strip("_")
    return slug or "unnamed"


def _assign_slug(name: str, assigned: dict[str, str], used: set[str]) -> str:
    if name in assigned:
        return assigned[name]

    base = _slug(name)
    slug, i = base, 2
    while slug in used:
        slug = f"{base}_{i}"
        i += 1

    assigned[name] = slug
    used.add(slug)
    return slug


class AnsibleLoginRequest(BaseModel):
    username: str
    master_password: str


@router.post("/ansible/login")
def ansible_login(data: AnsibleLoginRequest, request: Request):
    client_ip, request_id = _ctx(request)

    try:
        verify_admin_password(data.username, data.master_password, client_ip)
    except TooManyLoginAttempts as e:
        _audit.info(
            "action=ansible_login username=%s result=throttled ip=%s request_id=%s",
            data.username, client_ip, request_id,
        )
        return JSONResponse(
            status_code=429,
            content={"error_code": "LOGIN_THROTTLED", "retry_after": e.retry_after_seconds},
        )
    except InvalidMasterPassword:
        _audit.info(
            "action=ansible_login username=%s result=invalid_password ip=%s request_id=%s",
            data.username, client_ip, request_id,
        )
        return JSONResponse(status_code=403, content={"error_code": "INVALID_MASTER_PASSWORD"})

    token, ttl = issue_session(data.username)
    request.state.actor = data.username

    _audit.info(
        "action=ansible_login username=%s result=ok ip=%s request_id=%s",
        data.username, client_ip, request_id,
    )
    return {"success": True, "data": {"token": token, "expires_in": ttl}}


@router.get("/ansible")
def ansible_inventory(request: Request):
    username = _require_session(request)

    client_ip, request_id = _ctx(request)
    request.state.actor = username

    rows = get_all_credentials_with_server_info()
    vault = get_vault_client()
    backend_token = vault._get_backend_token()

    host_slugs: dict[str, str] = {}
    host_slugs_used: set[str] = set()
    branch_slugs: dict[str, str] = {}
    branch_slugs_used: set[str] = set()

    hostvars: dict[str, dict] = {}
    groups: dict[str, set[str]] = {}

    for row in rows:
        if row["device_type"] != "linux":
            continue

        display_name = row["server_name"]
        host = _assign_slug(display_name, host_slugs, host_slugs_used)

        if host in hostvars:
            continue

        try:
            secret = vault.read_kv_v2(backend_token, row["vault_path"])
        except VaultReadError:
            logger.warning(
                "inventory: vault read skipped path=%s host=%s", row["vault_path"], display_name
            )
            continue

        hostvars[host] = {
            "ansible_host": row["ip"],
            "ansible_port": row["port"],
            "ansible_user": secret.get("username", ""),
            "ansible_ssh_pass": secret.get("password", ""),
            "opscontrol_display_name": display_name,
            "opscontrol_branch": row["branch"],
        }
        group = _assign_slug(row["branch"], branch_slugs, branch_slugs_used)
        groups.setdefault(group, set()).add(host)

    _audit.info(
        "action=ansible_inventory_fetch username=%s host_count=%d ip=%s request_id=%s",
        username, len(hostvars), client_ip, request_id,
    )

    result: dict = {"_meta": {"hostvars": hostvars}}
    for group, hosts in groups.items():
        result[group] = {"hosts": sorted(hosts)}
    result["all"] = {"children": sorted(groups.keys())}
    return result
