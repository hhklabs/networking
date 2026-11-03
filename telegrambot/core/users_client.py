"""Client and runner helpers for VPN user profiles management."""

import asyncio
import json
import os
from typing import Any, Optional

from telegrambot.core.runner import run_hotspot_command


def resolve_mobileconfig_bytes(u: dict[str, Any]) -> tuple[bytes, str]:
    """Resolve raw bytes for .mobileconfig file with on-the-fly generation fallback."""
    uname = u.get("username", "user")
    filename = f"{uname}.mobileconfig"
    path = u.get("mobileconfig_path", "")

    for p in [path, f"/host{path}"]:
        if p and os.path.exists(p):
            try:
                with open(p, "rb") as f:
                    return f.read(), filename
            except Exception:
                pass

    from scripts.hotspot.mobileconfig import generate_mobileconfig

    xml = generate_mobileconfig(
        uname,
        u.get("password", ""),
        server=u.get("server", "connect.hhk.my.id"),
    )
    return xml.encode("utf-8"), filename


async def execute_users_cmd(args: list[str]) -> tuple[str, str, int]:
    """Execute host hotspot-manager with user management arguments."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, run_hotspot_command, args)


async def fetch_all_users() -> list[dict[str, Any]]:
    """Fetch list of all VPN users via JSON CLI output."""
    out, _, code = await execute_users_cmd(["--users", "--json"])
    if code == 0 and out.strip():
        try:
            return json.loads(out)
        except Exception:
            pass
    return []


async def fetch_user(username: str) -> Optional[dict[str, Any]]:
    """Fetch specific VPN user details via JSON CLI output."""
    out, _, code = await execute_users_cmd(["--user-get", username, "--json"])
    if code == 0 and out.strip():
        try:
            return json.loads(out)
        except Exception:
            pass
    return None
