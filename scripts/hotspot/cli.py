#!/usr/bin/env python3
"""Command Line Interface parser and dispatcher for Hotspot Manager."""

import json
import os
import sys

from .cli_parser import create_parser
from .constants import CONFIG
from .context import Context
from .detection import get_connected_clients
from .runner import check_docker_container

try:
    import fcntl
except ImportError:
    fcntl = None


def _acquire_cli_lock():
    if fcntl is None:
        return None
    lock_file = "/run/lock/hotspot-manager-cli.lock"
    try:
        os.makedirs(os.path.dirname(lock_file), exist_ok=True)
    except Exception:
        lock_file = "/tmp/hotspot-manager-cli.lock"
    try:
        import time

        fd = open(lock_file, "a+")
        start = time.time()
        while time.time() - start < 15:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                fd.seek(0)
                fd.truncate()
                fd.write(f"PID={os.getpid()} CMD={' '.join(sys.argv)}\n")
                fd.flush()
                return fd
            except (BlockingIOError, OSError):
                time.sleep(0.5)
        fd.seek(0)
        return fd.read().strip() or False
    except Exception:
        return None


def main() -> None:
    ctx = Context.get()
    cfg = getattr(ctx, "CONFIG", CONFIG)

    parser = create_parser()
    args = parser.parse_args()
    telegram_format = bool(args.telegram or args.html)

    if len(sys.argv) == 1:
        args.status = True

    mutating = any(
        [
            args.restart,
            args.restart_vpn,
            args.fix,
            args.switch_vpn,
            args.reality_server,
            args.unlimited_country,
            args.rotate_ip,
            args.set_ipv6,
            args.set_adguard,
            args.refresh_routes,
            args.watchdog,
            args.watchdog_vpn,
            args.watchdog_dns,
            (args.wan_target and args.wan_target != "status"),
            args.user_add,
            args.user_pause,
            args.user_resume,
            args.user_del,
        ]
    )
    if mutating:
        lock_fd = _acquire_cli_lock()
        if lock_fd is False or isinstance(lock_fd, str):
            detail = f" ({lock_fd})" if isinstance(lock_fd, str) and lock_fd else ""
            print(f"Notice: Another hotspot task is in progress{detail}. Please retry.")
            sys.exit(1)

    if any(
        [
            args.users,
            args.user_add,
            args.user_pause,
            args.user_resume,
            args.user_del,
            args.user_get,
        ]
    ):
        from .users import handle_users_cli

        sys.exit(
            0 if handle_users_cli(args, ctx, telegram_format=telegram_format) else 1
        )

    if args.refresh_routes:
        getattr(ctx, "refresh_routes", getattr(ctx, "refresh_github_routes"))()
        print("Routes refreshed successfully.")
        sys.exit(0)

    if args.watchdog_vpn:
        ok, state = getattr(ctx, "ensure_vpn_resilience")()
        print(f"VPN Watchdog: {state}")
        sys.exit(0 if ok else 1)

    if args.watchdog:
        wan_fn = getattr(ctx, "ensure_wan_resilience", None)
        wan_ok, wan_state = wan_fn() if wan_fn else (True, "wan_ok")
        if not wan_ok:
            print(
                f"Watchdog: WAN={wan_state}, "
                "VPN=wan_offline_skipped, DNS=wan_offline_skipped"
            )
            sys.exit(1)
        vpn_ok, vpn_state = getattr(ctx, "ensure_vpn_resilience")()
        dns_ok, dns_state = getattr(ctx, "ensure_adguard_resilience")()
        print(f"Watchdog: WAN={wan_state}, VPN={vpn_state}, DNS={dns_state}")
        sys.exit(0 if (wan_ok and vpn_ok and dns_ok) else 1)

    if args.watchdog_dns:
        ok, state = getattr(ctx, "ensure_adguard_resilience")()
        print(f"DNS Watchdog: {state}")
        sys.exit(0 if ok else 1)

    if args.list_countries:
        profs = getattr(ctx, "get_country_profiles")()
        if args.json:
            print(json.dumps(profs))
        else:
            for cc, p in profs.items():
                print(
                    f"{p['flag']} {cc.upper()}: {p['country_name']} ({p['filename']})"
                )
        sys.exit(0)

    def _exit_status(success: bool = True):
        output = getattr(ctx, "print_status")(
            getattr(ctx, "get_status")(), telegram_format=telegram_format
        )
        print(output)
        sys.exit(0 if success else 1)

    if args.unlimited_country:
        _exit_status(getattr(ctx, "switch_unlimited_country")(args.unlimited_country))

    if args.rotate_ip:
        _exit_status(getattr(ctx, "rotate_unlimited_country_ip")())

    if args.reality_server:
        num = "1" if args.reality_server in ["1", "server-1"] else "2"
        _exit_status(getattr(ctx, "switch_reality_server")(num))

    if args.switch_vpn:
        _exit_status(getattr(ctx, "switch_vpn")(args.switch_vpn))

    if args.set_ipv6:
        _exit_status(getattr(ctx, "set_ipv6_mode")(args.set_ipv6))

    if args.set_adguard:
        success = False
        set_adg_fn = getattr(ctx, "set_adguard_state")
        if args.set_adguard in ["on", "enable"]:
            success = set_adg_fn(True)
        elif args.set_adguard in ["off", "disable"]:
            success = set_adg_fn(False)
        elif args.set_adguard == "restart":
            set_adg_fn(False)
            success = set_adg_fn(True)
        elif args.set_adguard == "status":
            enabled = getattr(ctx, "get_adguard_enabled")()
            chk_c = getattr(ctx, "check_docker_container", check_docker_container)
            st = chk_c(cfg.get("adguard_container", "adguardhome"))
            s_str = "Running" if st else "Stopped"
            c_str = "Enabled" if enabled else "Disabled"
            print(f"AdGuard Config: {c_str} | Container: {s_str}")
            sys.exit(0)
        _exit_status(success)

    if args.wan_target:
        if args.wan_target == "status":
            cur = getattr(ctx, "get_current_default_wan", lambda: "eth0")()
            mode = getattr(ctx, "get_wan_mode", lambda: "auto")()
            chk = getattr(ctx, "check_wan_reachability", lambda _: False)
            e_st = "ONLINE" if chk("eth0") else "OFFLINE"
            u_st = "ONLINE" if chk("usb0") else "OFFLINE"
            m_tag = f" ({mode})" if mode else ""
            print(
                f"Active WAN: {cur}{m_tag} | eth0 (Fiber): {e_st} | usb0 (USB): {u_st}"
            )
            sys.exit(0)
        sw_fn = getattr(ctx, "switch_wan_uplink", None)
        mode = "auto" if args.wan_target == "auto" else "manual"
        ok = sw_fn(args.wan_target, mode=mode) if sw_fn else False
        sys.exit(0 if ok else 1)

    if args.status:
        _exit_status(True)

    if args.clients:
        from .clients import format_clients

        connected = getattr(ctx, "get_connected_clients", get_connected_clients)()
        fmt_fn = getattr(ctx, "format_clients", format_clients)
        print(fmt_fn(connected or [], telegram_format=telegram_format))

    if args.restart_vpn:
        if not getattr(ctx, "restart_vpn")():
            sys.exit(1)

    if args.fix or args.restart:
        if not getattr(ctx, "fix_hotspot")():
            sys.exit(1)
        if args.fix:
            _exit_status(True)


if __name__ == "__main__":
    main()
