#!/usr/bin/env python3
"""Unit tests for VPN client users manager and profile generator."""

import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from scripts.hotspot.mobileconfig import generate_mobileconfig, generate_sswan_config
from scripts.hotspot.users import (
    add_vpn_user,
    delete_vpn_user,
    generate_secure_password,
    get_vpn_user,
    handle_users_cli,
    list_vpn_users,
    pause_vpn_user,
    resume_vpn_user,
)


class TestVpnUsersManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.users_file = os.path.join(self.test_dir, "vpn_users.json")
        self.profiles_dir = os.path.join(self.test_dir, "profiles")
        os.makedirs(self.profiles_dir, exist_ok=True)

        self.patch_path = patch(
            "scripts.hotspot.users.get_users_file_path", return_value=self.users_file
        )
        self.patch_prof = patch(
            "scripts.hotspot.users.get_profiles_dir", return_value=self.profiles_dir
        )
        self.patch_sync = patch(
            "scripts.hotspot.users.sync_vps_user", return_value=(True, "Synced")
        )

        self.patch_path.start()
        self.patch_prof.start()
        self.patch_sync.start()

    def tearDown(self):
        self.patch_path.stop()
        self.patch_prof.stop()
        self.patch_sync.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_generate_secure_password(self):
        pwd = generate_secure_password()
        self.assertTrue(pwd.startswith("Good@"))
        self.assertEqual(len(pwd), 9)

    def test_generate_mobileconfig(self):
        xml = generate_mobileconfig(
            "TestUser", "Pass123", server="connect.test.id", org_name="TestOrg"
        )
        self.assertIn("<string>TestUser - VPN</string>", xml)
        self.assertIn("<string>connect.test.id</string>", xml)
        self.assertIn("<string>TestUser</string>", xml)
        self.assertIn("<string>Pass123</string>", xml)
        self.assertIn("PayloadUUID", xml)

    def test_generate_sswan_config(self):
        cfg = generate_sswan_config("TestUser", "Pass123", server="connect.test.id")
        self.assertEqual(cfg["user"]["name"], "TestUser")
        self.assertEqual(cfg["user"]["password"], "Pass123")
        self.assertEqual(cfg["remote"]["address"], "connect.test.id")
        self.assertEqual(cfg["type"], "ikev2-eap")

    def test_add_and_get_vpn_user(self):
        ok, msg, record = add_vpn_user("KyawKyaw", "Secret@2026")
        self.assertTrue(ok)
        self.assertIn("KyawKyaw", msg)
        self.assertEqual(record["username"], "KyawKyaw")
        self.assertEqual(record["password"], "Secret@2026")
        self.assertTrue(os.path.exists(record["mobileconfig_path"]))

        user = get_vpn_user("KyawKyaw")
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], "KyawKyaw")
        self.assertEqual(user["status"], "active")

    def test_pause_and_resume_vpn_user(self):
        add_vpn_user("User1", "Pass1")
        ok_pause, msg_pause = pause_vpn_user("User1")
        self.assertTrue(ok_pause)
        self.assertEqual(get_vpn_user("User1")["status"], "paused")

        ok_resume, msg_resume = resume_vpn_user("User1")
        self.assertTrue(ok_resume)
        self.assertEqual(get_vpn_user("User1")["status"], "active")

    def test_delete_vpn_user(self):
        add_vpn_user("UserToDelete", "Pass1")
        path = get_vpn_user("UserToDelete")["mobileconfig_path"]
        self.assertTrue(os.path.exists(path))

        ok, msg = delete_vpn_user("UserToDelete")
        self.assertTrue(ok)
        self.assertIsNone(get_vpn_user("UserToDelete"))
        self.assertFalse(os.path.exists(path))

    def test_list_vpn_users(self):
        add_vpn_user("U1", "P1")
        add_vpn_user("U2", "P2")
        users = list_vpn_users()
        self.assertEqual(len(users), 2)

    def test_handle_users_cli_list(self):
        add_vpn_user("Alice", "PassA")
        args = MagicMock()
        args.users = True
        args.json = True
        args.user_add = None
        args.user_pause = None
        args.user_resume = None
        args.user_del = None
        args.user_get = None
        self.assertTrue(handle_users_cli(args, None))

    def test_handle_users_cli_add_and_del(self):
        args = MagicMock()
        args.users = False
        args.json = False
        args.user_add = ["Bob", "BobPass@123"]
        args.user_pause = None
        args.user_resume = None
        args.user_del = None
        args.user_get = None
        self.assertTrue(handle_users_cli(args, None))
        self.assertIsNotNone(get_vpn_user("Bob"))

        del_args = MagicMock()
        del_args.users = False
        del_args.json = False
        del_args.user_add = None
        del_args.user_pause = None
        del_args.user_resume = None
        del_args.user_del = "Bob"
        del_args.user_get = None
        self.assertTrue(handle_users_cli(del_args, None))
        self.assertIsNone(get_vpn_user("Bob"))


if __name__ == "__main__":
    unittest.main()
