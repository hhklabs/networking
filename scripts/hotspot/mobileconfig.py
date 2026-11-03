#!/usr/bin/env python3
"""MobileConfig XML and strongSwan JSON profile generator for Apple iOS and Android."""

import re
import uuid
from typing import Any


def generate_mobileconfig(
    username: str,
    password: str,
    server: str = "connect.hhk.my.id",
    org_name: str = "GoodWifi Network",
) -> str:
    """Generate Apple iOS Native IKEv2 .mobileconfig XML."""
    user_clean = re.sub(r"[^a-zA-Z0-9_-]", "", username)
    user_lower = user_clean.lower()
    payload_uuid = str(uuid.uuid4()).upper()
    sub_uuid = str(uuid.uuid4()).upper()

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>PayloadDisplayName</key>
    <string>{user_clean} - VPN</string>
    <key>PayloadDescription</key>
    <string>Native iOS IKEv2 VPN Profile for {user_clean} (Direct US VPS)</string>
    <key>PayloadIdentifier</key>
    <string>com.hhk.vpn.{user_lower}</string>
    <key>PayloadOrganization</key>
    <string>{org_name}</string>
    <key>PayloadType</key>
    <string>Configuration</string>
    <key>PayloadUUID</key>
    <string>{payload_uuid}</string>
    <key>PayloadVersion</key>
    <integer>1</integer>
    <key>PayloadContent</key>
    <array>
        <dict>
            <key>PayloadType</key>
            <string>com.apple.vpn.managed</string>
            <key>PayloadVersion</key>
            <integer>1</integer>
            <key>PayloadIdentifier</key>
            <string>com.hhk.vpn.{user_lower}.ikev2</string>
            <key>PayloadUUID</key>
            <string>{sub_uuid}</string>
            <key>PayloadDisplayName</key>
            <string>{user_clean} (Direct US)</string>
            <key>PayloadDescription</key>
            <string>iOS Native IKEv2 VPN</string>
            <key>UserDefinedName</key>
            <string>{user_clean} (Direct US)</string>
            <key>VPNType</key>
            <string>IKEv2</string>
            <key>IKEv2</key>
            <dict>
                <key>RemoteAddress</key>
                <string>{server}</string>
                <key>RemoteIdentifier</key>
                <string>{server}</string>
                <key>LocalIdentifier</key>
                <string>{user_clean}</string>
                <key>AuthenticationMethod</key>
                <string>None</string>
                <key>ExtendedAuthEnabled</key>
                <integer>1</integer>
                <key>AuthName</key>
                <string>{user_clean}</string>
                <key>AuthPassword</key>
                <string>{password}</string>
                <key>DeadPeerDetectionRate</key>
                <string>Medium</string>
                <key>DisableMOBIKE</key>
                <integer>0</integer>
                <key>DisableRedirect</key>
                <integer>0</integer>
                <key>EnablePFS</key>
                <integer>0</integer>
                <key>EnableCertificateRevocationCheck</key>
                <integer>0</integer>
                <key>IPv4</key>
                <dict>
                    <key>OverridePrimary</key>
                    <integer>1</integer>
                </dict>
            </dict>
        </dict>
    </array>
</dict>
</plist>
"""


def generate_sswan_config(
    username: str, password: str, server: str = "connect.hhk.my.id"
) -> dict[str, Any]:
    """Generate strongSwan Android app .sswan profile dictionary."""
    return {
        "uuid": str(uuid.uuid4()),
        "name": f"{username} ({server})",
        "type": "ikev2-eap",
        "remote": {"address": server},
        "user": {"name": username, "password": password},
    }
