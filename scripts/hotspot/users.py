#!/usr/bin/env python3
"""VPN client users manager for iOS and Android profiles.

Manages IKEv2 user credentials, generates iOS .mobileconfig profiles,
Android settings / .sswan configs, and synchronizes with remote VPS strongSwan.
"""

import json
import os
import random
import re
import string
from typing import Any, Optional

from .constants import CONFIG
from .context import Context
from .mobileconfig import generate_mobileconfig, generate_sswan_config
from .remote import get_remote_vps_target
from .runner import get_host_path, log, run_args

__all__ = [
    "generate_secure_password",
    "get_users_file_path",
    "get_profiles_dir",
    "load_vpn_users",
    "save_vpn_users",
    "sync_vps_user",
    "add_vpn_user",
    "pause_vpn_user",
    "resume_vpn_user",
    "delete_vpn_user",
    "get_vpn_user",
    "list_vpn_users",
    "handle_users_cli",
    "generate_mobileconfig",
    "generate_sswan_config",
]

# flake8: noqa: E501

_VPS_TEMPLATES = {
    "add": (
        'grep -qE "^[#[:space:]]*{u}[[:space:]]*:" /etc/ipsec.secrets 2>/dev/null '
        '&& sed -i -E "s/^[#[:space:]]*{u}[[:space:]]*:.*/{u} : EAP \\"{p}\\"/" /etc/ipsec.secrets '
        '|| echo "{u} : EAP \\"{p}\\"" >> /etc/ipsec.secrets; '
        "ipsec rereadsecrets 2>/dev/null || strongswan rereadsecrets 2>/dev/null || true"
    ),
    "pause": (
        'sed -i -E "s/^([[:space:]]*{u}[[:space:]]*:[[:space:]]*EAP)/# \\1/" /etc/ipsec.secrets; '
        "ipsec rereadsecrets 2>/dev/null || strongswan rereadsecrets 2>/dev/null || true; "
        "ipsec stroke down-nb ikev2-{u} 2>/dev/null || ipsec down {u} 2>/dev/null || true"
    ),
    "resume": (
        'sed -i -E "s/^#[[:space:]]*({u}[[:space:]]*:[[:space:]]*EAP)/\\1/" /etc/ipsec.secrets; '
        "ipsec rereadsecrets 2>/dev/null || strongswan rereadsecrets 2>/dev/null || true"
    ),
    "delete": (
        'sed -i -E "/^[#[:space:]]*{u}[[:space:]]*:[[:space:]]*EAP/d" /etc/ipsec.secrets; '
        "ipsec rereadsecrets 2>/dev/null || strongswan rereadsecrets 2>/dev/null || true; "
        "ipsec stroke down-nb ikev2-{u} 2>/dev/null || ipsec down {u} 2>/dev/null || true; "
        "rm -f /var/www/*/ios/{u}.mobileconfig 2>/dev/null || true"
    ),
}


def generate_secure_password() -> str:
    """Generate a clean, strong password (e.g. Good@5824)."""
    return f"Good@{''.join(random.choices(string.digits, k=4))}"


def _get_path(sub: str) -> str:
    ctx = Context.get()
    pref = getattr(ctx, "get_host_path", get_host_path)(f"/etc/goodwifi/{sub}")
    for candidate in [pref, f"/tmp/goodwifi/{sub}"]:
        try:
            d = os.path.dirname(candidate) if "." in sub else candidate
            os.makedirs(d, exist_ok=True)
            return candidate
        except Exception:
            pass
    return f"/tmp/goodwifi/{sub}"


def get_users_file_path() -> str:
    """Return persistent path for vpn users json data."""
    return _get_path("vpn_users.json")


def get_profiles_dir() -> str:
    """Return local directory for generated client profile files."""
    return _get_path("profiles")


def load_vpn_users() -> dict[str, dict[str, Any]]:
    """Load all registered VPN users from disk."""
    path = get_users_file_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log(f"Failed to load VPN users from {path}: {e}", "WARNING")
    return {}


def save_vpn_users(users: dict[str, dict[str, Any]]) -> bool:
    """Save registered VPN users dictionary to disk."""
    path = get_users_file_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2)
        return True
    except Exception as e:
        log(f"Failed to save VPN users to {path}: {e}", "ERROR")
        return False


def sync_vps_user(action: str, username: str, password: str = "") -> tuple[bool, str]:
    """Sync user creation/pause/resume/deletion with remote VPS strongSwan."""
    tmpl = _VPS_TEMPLATES.get(action)
    if not tmpl:
        return False, f"Unknown action '{action}'"

    ctx = Context.get()
    host, port, user = getattr(ctx, "get_remote_vps_target", get_remote_vps_target)()
    if not host:
        return False, "No remote VPS target configured"

    u_clean = re.sub(r"[^a-zA-Z0-9_-]", "", username)
    remote_cmd = tmpl.format(u=u_clean, p=password.replace('"', '\\"'))

    cmd = [
        "ssh",
        "-p",
        str(port),
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=5",
        "-o",
        "StrictHostKeyChecking=accept-new",
        f"{user}@{host}",
        remote_cmd,
    ]
    ok, out, err = getattr(ctx, "run_args", run_args)(cmd, timeout=12)
    return (True, "Synced") if ok else (False, err or out or "SSH failed")


def add_vpn_user(
    username: str, password: Optional[str] = None
) -> tuple[bool, str, dict[str, Any]]:
    """Add a new VPN user or update existing credentials."""
    u_clean = re.sub(r"[^a-zA-Z0-9_-]", "", username.strip())
    if not u_clean:
        return False, "Invalid username (letters, digits, underscores only)", {}

    final_pass = password.strip() if password else generate_secure_password()
    cfg = getattr(Context.get(), "CONFIG", CONFIG)
    server = cfg.get("vps_ssh_host") or "connect.hhk.my.id"

    xml = generate_mobileconfig(u_clean, final_pass, server=server)
    mc_path = os.path.join(get_profiles_dir(), f"{u_clean}.mobileconfig")
    try:
        with open(mc_path, "w", encoding="utf-8") as f:
            f.write(xml)
    except Exception as e:
        return False, f"Failed to write local mobileconfig: {e}", {}

    vps_ok, vps_msg = sync_vps_user("add", u_clean, final_pass)
    users = load_vpn_users()
    record = {
        "username": u_clean,
        "password": final_pass,
        "server": server,
        "status": "active",
        "mobileconfig_path": mc_path,
        "url": f"https://{server}/ios/{u_clean}.mobileconfig",
        "vps_synced": vps_ok,
    }
    users[u_clean] = record
    save_vpn_users(users)

    note = "" if vps_ok else f" (VPS sync: {vps_msg})"
    return True, f"User '{u_clean}' created successfully{note}", record


def _set_user_status(username: str, status: str, action: str) -> tuple[bool, str]:
    users = load_vpn_users()
    u = re.sub(r"[^a-zA-Z0-9_-]", "", username.strip())
    if u not in users:
        return False, f"User '{u}' not found"
    pwd = users[u].get("password", "") if action == "resume" else ""
    vps_ok, _ = sync_vps_user(action, u, pwd)
    users[u]["status"] = status
    users[u]["vps_synced"] = vps_ok
    save_vpn_users(users)
    return True, f"User '{u}' {status} successfully"


def pause_vpn_user(username: str) -> tuple[bool, str]:
    """Pause/disable an active VPN user."""
    return _set_user_status(username, "paused", "pause")


def resume_vpn_user(username: str) -> tuple[bool, str]:
    """Resume/enable a paused VPN user."""
    return _set_user_status(username, "active", "resume")


def delete_vpn_user(username: str) -> tuple[bool, str]:
    """Delete a VPN user and remove profile files."""
    users = load_vpn_users()
    u = re.sub(r"[^a-zA-Z0-9_-]", "", username.strip())
    if u not in users:
        return False, f"User '{u}' not found"

    sync_vps_user("delete", u)
    mc_path = users[u].get("mobileconfig_path")
    if mc_path and os.path.exists(mc_path):
        try:
            os.remove(mc_path)
        except Exception:
            pass
    del users[u]
    save_vpn_users(users)
    return True, f"User '{u}' deleted successfully"


def get_vpn_user(username: str) -> Optional[dict[str, Any]]:
    """Retrieve details of a specific VPN user."""
    users = load_vpn_users()
    return users.get(re.sub(r"[^a-zA-Z0-9_-]", "", username.strip()))


def list_vpn_users() -> list[dict[str, Any]]:
    """Return list of all registered VPN users."""
    return list(load_vpn_users().values())


def handle_users_cli(args: Any, ctx: Any, telegram_format: bool = False) -> bool:
    """Handle CLI user profile management commands."""
    if getattr(args, "users", False):
        users = list_vpn_users()
        if getattr(args, "json", False):
            print(json.dumps(users, indent=2))
        elif not users:
            print("No VPN users registered.")
        else:
            for u in users:
                b = "🟢" if u.get("status") == "active" else "⏸️"
                print(
                    f"{b} {u.get('username')} ({u.get('status')}) | {u.get('server')}"
                )
        return True

    if getattr(args, "user_add", None):
        parts = args.user_add
        uname, upass = parts[0], (parts[1] if len(parts) > 1 else None)
        ok, msg, rec = add_vpn_user(uname, upass)
        if getattr(args, "json", False):
            print(json.dumps({"success": ok, "message": msg, "user": rec}))
        else:
            print(f"{'✅' if ok else '❌'} {msg}")
            if ok and rec:
                print(f"Password: {rec.get('password')}\nURL: {rec.get('url')}")
        return ok

    for attr, fn in [
        ("user_pause", pause_vpn_user),
        ("user_resume", resume_vpn_user),
        ("user_del", delete_vpn_user),
    ]:
        val = getattr(args, attr, None)
        if val:
            ok, msg = fn(val)
            print(f"{'✅' if ok else '❌'} {msg}")
            return ok

    if getattr(args, "user_get", None):
        u = get_vpn_user(args.user_get)
        if not u:
            print(f"User '{args.user_get}' not found.")
            return False
        if getattr(args, "json", False):
            print(json.dumps(u, indent=2))
        else:
            print(
                f"User: {u.get('username')}\nStatus: {u.get('status')}\n"
                f"Password: {u.get('password')}\nServer: {u.get('server')}\nURL: {u.get('url')}"
            )
        return True

    return False
