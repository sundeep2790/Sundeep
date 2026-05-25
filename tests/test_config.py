"""
test_config.py — Unit tests for the config module (config.py).
Covers: key derivation, save/load round-trip, tamper detection, cache validity,
get_credits, set_credits, set_email, set_lifetime helpers.

config.py lives at the project root and is imported as bare `import config`.
We patch `config.CONFIG_PATH` per-test to redirect all file I/O to /tmp.
"""
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

# Ensure project root is on sys.path so bare `import config` resolves
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import config as config_mod   # bare import — config.py is at project root

# Use /tmp for all test config files (the mounted filesystem is SQLite-hostile)
_TEMP_DIR = "/tmp/datarescue_test_config"
os.makedirs(_TEMP_DIR, exist_ok=True)
_TEMP_CONFIG_PATH = os.path.join(_TEMP_DIR, "config.enc")


def _patch_path():
    """Return a patch context that redirects CONFIG_PATH to /tmp."""
    return patch.object(config_mod, "CONFIG_PATH", _TEMP_CONFIG_PATH)


def _clean():
    """Remove the temp config file between tests."""
    if os.path.exists(_TEMP_CONFIG_PATH):
        try:
            os.remove(_TEMP_CONFIG_PATH)
        except Exception:
            pass


class TestGetFernetKey(unittest.TestCase):
    def test_deterministic(self):
        k1 = config_mod.get_fernet_key("test-token-1234-5678")
        k2 = config_mod.get_fernet_key("test-token-1234-5678")
        self.assertEqual(k1, k2)

    def test_different_tokens_different_keys(self):
        k1 = config_mod.get_fernet_key("token-aaa")
        k2 = config_mod.get_fernet_key("token-bbb")
        self.assertNotEqual(k1, k2)

    def test_key_usable_with_fernet(self):
        from cryptography.fernet import Fernet
        key = config_mod.get_fernet_key("some-device-token-here")
        f = Fernet(key)
        data = f.encrypt(b"hello world")
        self.assertEqual(f.decrypt(data), b"hello world")

    def test_short_token_still_works(self):
        # Token shorter than 16 chars — salt padding must not crash
        key = config_mod.get_fernet_key("short")
        self.assertIsNotNone(key)


class TestGetDefaultConfig(unittest.TestCase):
    def test_has_required_keys(self):
        cfg = config_mod.get_default_config()
        for key in ("email", "device_token", "credits", "credits_cached_at", "is_lifetime"):
            self.assertIn(key, cfg)

    def test_email_is_empty(self):
        self.assertEqual(config_mod.get_default_config()["email"], "")

    def test_credits_zero(self):
        self.assertEqual(config_mod.get_default_config()["credits"], 0)

    def test_is_lifetime_false(self):
        self.assertFalse(config_mod.get_default_config()["is_lifetime"])

    def test_device_token_is_uuid_format(self):
        import uuid
        cfg = config_mod.get_default_config()
        uuid.UUID(cfg["device_token"])   # raises if not valid UUID

    def test_each_call_unique_token(self):
        t1 = config_mod.get_default_config()["device_token"]
        t2 = config_mod.get_default_config()["device_token"]
        self.assertNotEqual(t1, t2)

    def test_cached_at_is_valid_iso(self):
        ts = config_mod.get_default_config()["credits_cached_at"]
        dt = datetime.fromisoformat(ts)   # raises if invalid
        self.assertIsNotNone(dt)


class TestSaveLoadRoundTrip(unittest.TestCase):
    def setUp(self):
        _clean()

    def tearDown(self):
        _clean()

    def test_basic_round_trip(self):
        cfg = {
            "email": "round@trip.com",
            "device_token": "abcd1234-abcd-abcd-abcd-abcd12345678",
            "credits": 42,
            "credits_cached_at": datetime.now(timezone.utc).isoformat(),
            "is_lifetime": False,
        }
        with _patch_path():
            config_mod.save_config(cfg.copy())
            loaded = config_mod.load_config()
        self.assertEqual(loaded["email"], "round@trip.com")
        self.assertEqual(loaded["credits"], 42)
        self.assertFalse(loaded["is_lifetime"])

    def test_lifetime_flag_persists(self):
        cfg = config_mod.get_default_config()
        cfg["is_lifetime"] = True
        cfg["credits"] = 500
        with _patch_path():
            config_mod.save_config(cfg)
            loaded = config_mod.load_config()
        self.assertTrue(loaded["is_lifetime"])
        self.assertEqual(loaded["credits"], 500)

    def test_email_update_persists(self):
        cfg = config_mod.get_default_config()
        cfg["email"] = "updated@example.com"
        with _patch_path():
            config_mod.save_config(cfg)
            loaded = config_mod.load_config()
        self.assertEqual(loaded["email"], "updated@example.com")

    def test_corrupt_file_falls_back_to_default(self):
        os.makedirs(_TEMP_DIR, exist_ok=True)
        with open(_TEMP_CONFIG_PATH, "wb") as f:
            f.write(b"not-valid-config-data-at-all!!!")
        with _patch_path():
            loaded = config_mod.load_config()
        self.assertIn("device_token", loaded)
        self.assertEqual(loaded["credits"], 0)

    def test_too_short_file_falls_back(self):
        os.makedirs(_TEMP_DIR, exist_ok=True)
        with open(_TEMP_CONFIG_PATH, "wb") as f:
            f.write(b"tooshort")
        with _patch_path():
            loaded = config_mod.load_config()
        self.assertIn("device_token", loaded)

    def test_missing_file_creates_default(self):
        alt_path = os.path.join(_TEMP_DIR, "does_not_exist.enc")
        with patch.object(config_mod, "CONFIG_PATH", alt_path):
            loaded = config_mod.load_config()
        self.assertIn("device_token", loaded)
        self.assertEqual(loaded["credits"], 0)
        self.assertTrue(os.path.exists(alt_path))
        os.remove(alt_path)

    def test_device_token_prefix_in_file(self):
        """Saved file should start with the 36-byte UUID prefix."""
        cfg = config_mod.get_default_config()
        with _patch_path():
            config_mod.save_config(cfg)
            with open(_TEMP_CONFIG_PATH, "rb") as f:
                raw = f.read()
        prefix = raw[:36].decode("utf-8")
        self.assertEqual(prefix, cfg["device_token"])


class TestIsCreditsCacheValid(unittest.TestCase):
    def test_fresh_cache_valid(self):
        ts = datetime.now(timezone.utc).isoformat()
        self.assertTrue(config_mod.is_credits_cache_valid({"credits_cached_at": ts}))

    def test_exactly_72h_still_valid(self):
        ts = (datetime.now(timezone.utc) - timedelta(hours=71, minutes=59)).isoformat()
        self.assertTrue(config_mod.is_credits_cache_valid({"credits_cached_at": ts}))

    def test_73h_expired(self):
        ts = (datetime.now(timezone.utc) - timedelta(hours=73)).isoformat()
        self.assertFalse(config_mod.is_credits_cache_valid({"credits_cached_at": ts}))

    def test_missing_key_invalid(self):
        self.assertFalse(config_mod.is_credits_cache_valid({}))

    def test_none_value_invalid(self):
        self.assertFalse(config_mod.is_credits_cache_valid({"credits_cached_at": None}))

    def test_malformed_string_invalid(self):
        self.assertFalse(config_mod.is_credits_cache_valid({"credits_cached_at": "not-a-date"}))

    def test_future_timestamp_valid(self):
        ts = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        self.assertTrue(config_mod.is_credits_cache_valid({"credits_cached_at": ts}))


class TestGetCredits(unittest.TestCase):
    def setUp(self):
        _clean()

    def tearDown(self):
        _clean()

    def _save(self, cfg):
        with _patch_path():
            config_mod.save_config(cfg)

    def test_lifetime_returns_large_number(self):
        cfg = config_mod.get_default_config()
        cfg["is_lifetime"] = True
        cfg["credits"] = 0
        self._save(cfg)
        with _patch_path():
            result = config_mod.get_credits()
        self.assertGreater(result, 1000)

    def test_valid_cache_returns_credits(self):
        cfg = config_mod.get_default_config()
        cfg["credits"] = 77
        cfg["credits_cached_at"] = datetime.now(timezone.utc).isoformat()
        self._save(cfg)
        with _patch_path():
            result = config_mod.get_credits()
        self.assertEqual(result, 77)

    def test_expired_cache_returns_zero(self):
        cfg = config_mod.get_default_config()
        cfg["credits"] = 50
        cfg["credits_cached_at"] = (datetime.now(timezone.utc) - timedelta(hours=80)).isoformat()
        self._save(cfg)
        with _patch_path():
            result = config_mod.get_credits()
        self.assertEqual(result, 0)

    def test_zero_credits_fresh_cache(self):
        cfg = config_mod.get_default_config()
        cfg["credits"] = 0
        self._save(cfg)
        with _patch_path():
            result = config_mod.get_credits()
        self.assertEqual(result, 0)


class TestSetHelpers(unittest.TestCase):
    def setUp(self):
        _clean()
        base = config_mod.get_default_config()
        with _patch_path():
            config_mod.save_config(base)

    def tearDown(self):
        _clean()

    def test_set_credits(self):
        with _patch_path():
            config_mod.set_credits(123)
            loaded = config_mod.load_config()
        self.assertEqual(loaded["credits"], 123)

    def test_set_credits_updates_cached_at(self):
        with _patch_path():
            config_mod.set_credits(55)
            loaded = config_mod.load_config()
        self.assertIsNotNone(loaded.get("credits_cached_at"))

    def test_set_credits_zero(self):
        with _patch_path():
            config_mod.set_credits(100)
            config_mod.set_credits(0)
            loaded = config_mod.load_config()
        self.assertEqual(loaded["credits"], 0)

    def test_set_email(self):
        with _patch_path():
            config_mod.set_email("new@email.com")
            loaded = config_mod.load_config()
        self.assertEqual(loaded["email"], "new@email.com")

    def test_set_email_empty(self):
        with _patch_path():
            config_mod.set_email("")
            loaded = config_mod.load_config()
        self.assertEqual(loaded["email"], "")

    def test_set_lifetime_true(self):
        with _patch_path():
            config_mod.set_lifetime(True)
            loaded = config_mod.load_config()
        self.assertTrue(loaded["is_lifetime"])

    def test_set_lifetime_false(self):
        with _patch_path():
            config_mod.set_lifetime(True)
            config_mod.set_lifetime(False)
            loaded = config_mod.load_config()
        self.assertFalse(loaded["is_lifetime"])

    def test_multiple_set_helpers_accumulate(self):
        with _patch_path():
            config_mod.set_email("a@b.com")
            config_mod.set_credits(99)
            config_mod.set_lifetime(True)
            loaded = config_mod.load_config()
        self.assertEqual(loaded["email"], "a@b.com")
        self.assertEqual(loaded["credits"], 99)
        self.assertTrue(loaded["is_lifetime"])


class TestNoDeviceToken(unittest.TestCase):
    def setUp(self):
        _clean()

    def tearDown(self):
        _clean()

    def test_save_without_token_auto_generates_one(self):
        cfg = {"email": "test@example.com", "credits": 0, "is_lifetime": False}
        with _patch_path():
            config_mod.save_config(cfg)
            loaded = config_mod.load_config()
        self.assertIn("device_token", loaded)
        self.assertGreater(len(loaded["device_token"]), 10)

    def test_generated_token_is_consistent(self):
        """Auto-generated token must survive a save/load cycle."""
        cfg = {"email": "", "credits": 0, "is_lifetime": False}
        with _patch_path():
            config_mod.save_config(cfg)
            first = config_mod.load_config()
            second = config_mod.load_config()
        self.assertEqual(first["device_token"], second["device_token"])


if __name__ == "__main__":
    unittest.main()
