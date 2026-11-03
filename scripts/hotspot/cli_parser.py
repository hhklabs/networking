#!/usr/bin/env python3
"""Command-line argument parser for Hotspot Manager."""

import argparse


def create_parser() -> argparse.ArgumentParser:
    """Build and return argument parser for hotspot-manager CLI."""
    parser = argparse.ArgumentParser(
        description="Raspberry Pi Hotspot Manager - Smart Monitoring"
    )
    parser.add_argument("-s", "--status", action="store_true")
    parser.add_argument("-r", "--restart", action="store_true")
    parser.add_argument("-rv", "--restart-vpn", action="store_true")
    parser.add_argument("-f", "--fix", action="store_true")
    parser.add_argument(
        "--switch-vpn",
        dest="switch_vpn",
        choices=["sing0", "awg0", "tun0", "wg0", "auto"],
        help="Switch active VPN backend",
    )
    parser.add_argument(
        "--reality-server",
        dest="reality_server",
        choices=["1", "2", "server-1", "server-2"],
        help="Switch primary Reality server (1: server-1, 2: server-2)",
    )
    parser.add_argument(
        "--unlimited-country",
        dest="unlimited_country",
        help="Switch VPN Unlimited exit country (e.g. sg, jp, direct)",
    )
    parser.add_argument(
        "--rotate-ip",
        action="store_true",
        help="Rotate to next candidate IP endpoint for active country exit",
    )
    parser.add_argument(
        "--list-countries",
        action="store_true",
        help="List available VPN Unlimited country profiles",
    )
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument(
        "--set-ipv6",
        "--ipv6",
        dest="set_ipv6",
        choices=["drop", "reject", "off"],
        help="Set IPv6 leak protection mode (drop, reject, off)",
    )
    parser.add_argument(
        "--adguard",
        dest="set_adguard",
        choices=["on", "off", "enable", "disable", "status", "restart"],
        help="Manage AdGuard Home service (on, off, status, restart)",
    )
    parser.add_argument("--clients", action="store_true")
    parser.add_argument(
        "--refresh-routes",
        action="store_true",
        help="Recompile and apply modular routes to AdGuard Home and ipsets",
    )
    parser.add_argument(
        "--watchdog-vpn",
        action="store_true",
        help="Check VPN health and auto-rotate candidate IP or restart if down",
    )
    parser.add_argument(
        "--watchdog",
        action="store_true",
        help="Run comprehensive health watchdog for both VPN and DNS resilience",
    )
    parser.add_argument(
        "--watchdog-dns",
        action="store_true",
        help="Check AdGuard container health and auto-failover to fallback DNS if down",
    )
    parser.add_argument(
        "--wan",
        dest="wan_target",
        choices=["eth0", "usb0", "auto", "status"],
        help="Switch active WAN uplink (eth0, usb0, auto) or query status",
    )
    parser.add_argument(
        "--telegram", action="store_true", help="Output in HTML format for Telegram"
    )
    parser.add_argument(
        "--html", action="store_true", help="Output formatted as HTML for Telegram"
    )
    parser.add_argument(
        "--users", action="store_true", help="List registered VPN users"
    )
    parser.add_argument(
        "--user-add", nargs="+", metavar=("U", "P"), help="Add VPN user"
    )
    parser.add_argument("--user-pause", metavar="U", help="Pause a VPN user")
    parser.add_argument("--user-resume", metavar="U", help="Resume a VPN user")
    parser.add_argument("--user-del", metavar="U", help="Delete a VPN user")
    parser.add_argument("--user-get", metavar="U", help="Get VPN user details")

    return parser
