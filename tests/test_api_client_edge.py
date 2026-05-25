"""
test_api_client_edge.py — Edge-case tests for the DataRescueClient (api/client.py).
Covers: mock-mode behaviour, network error fallback, checkout URL generation,
all pack credit values, concurrent safety, invalid code formats.
"""
import unittest
from unittest.mock import patch, MagicMock
import requests

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datarescue.api.client import DataRescueClient


def _mock_client(**kwargs):
    """Return a client in pure mock mode (no HTTP calls)."""
    return DataRescueClient(api_base_url=None, email="test@example.com",
                            device_token="test-device-token", **kwargs)


def _real_client():
    """Return a client configured for a real URL (but network will be stubbed)."""
    return DataRescueClient(api_base_url="http://localhost:9999",
                            email="test@example.com",
                            device_token="test-device-token")


class TestMockModeInitialState(unittest.TestCase):
    def test_initial_balance_zero(self):
        c = _mock_client()
        self.assertEqual(c.get_balance(), 0)

    def test_initial_lifetime_false(self):
        c = _mock_client()
        result = c.validate_licence()
        self.assertFalse(result["is_lifetime"])

    def test_initial_licence_not_valid(self):
        c = _mock_client()
        result = c.validate_licence()
        self.assertFalse(result["valid"])

    def test_none_url_triggers_mock_mode(self):
        c = DataRescueClient(api_base_url=None, email="a@b.com", device_token="tok")
        self.assertTrue(c.is_mock_mode)


class TestMockModePackCredits(unittest.TestCase):
    """Each pack ID must add the documented number of credits."""

    def _confirm(self, client, session_id):
        return client.confirm_payment(session_id)

    def test_starter_pack_adds_100(self):
        c = _mock_client()
        r = self._confirm(c, "mock_starter_session")
        self.assertEqual(r["balance"], 100)

    def test_standard_pack_adds_250(self):
        c = _mock_client()
        r = self._confirm(c, "mock_standard_session")
        self.assertEqual(r["balance"], 250)

    def test_plus_pack_adds_500(self):
        c = _mock_client()
        r = self._confirm(c, "mock_plus_session")
        self.assertEqual(r["balance"], 500)

    def test_unlimited_pack_sets_lifetime(self):
        c = _mock_client()
        r = self._confirm(c, "mock_unlimited_session")
        self.assertTrue(r["is_lifetime"])

    def test_appsumo_pack_adds_500_and_lifetime(self):
        c = _mock_client()
        r = self._confirm(c, "mock_appsumo_session")
        self.assertEqual(r["balance"], 500)
        self.assertTrue(r["is_lifetime"])

    def test_unknown_pack_defaults_to_starter(self):
        c = _mock_client()
        r = self._confirm(c, "mock_mystery_session")
        self.assertEqual(r["balance"], 100)

    def test_multiple_purchases_accumulate(self):
        c = _mock_client()
        self._confirm(c, "mock_starter_s1")
        self._confirm(c, "mock_standard_s2")
        # 100 + 250 = 350
        self.assertEqual(c.get_balance(), 350)

    def test_duplicate_session_id_not_reprocessed(self):
        """Confirming the same session twice must not add credits twice."""
        c = _mock_client()
        self._confirm(c, "mock_starter_dupe_s1")
        with self.assertRaises(ValueError):
            self._confirm(c, "mock_starter_dupe_s1")


class TestMockModeDeduction(unittest.TestCase):
    def test_deduct_reduces_balance(self):
        c = _mock_client()
        c.confirm_payment("mock_standard_deduct1")  # 250 credits
        new_balance = c.deduct_credits(50)
        self.assertEqual(new_balance, 200)

    def test_deduct_full_balance_leaves_zero(self):
        c = _mock_client()
        c.confirm_payment("mock_starter_deduct2")  # 100 credits
        new_balance = c.deduct_credits(100)
        self.assertEqual(new_balance, 0)

    def test_deduct_more_than_balance_raises(self):
        c = _mock_client()
        c.confirm_payment("mock_starter_deduct3")  # 100 credits
        with self.assertRaises(ValueError):
            c.deduct_credits(101)

    def test_deduct_on_zero_balance_raises(self):
        c = _mock_client()
        with self.assertRaises(ValueError):
            c.deduct_credits(1)

    def test_lifetime_deduct_does_not_reduce_balance(self):
        """Lifetime users can deduct any amount without balance change."""
        c = _mock_client()
        c.confirm_payment("mock_unlimited_lifeded")  # lifetime
        original = c.get_balance()
        c.deduct_credits(9999)
        self.assertEqual(c.get_balance(), original)


class TestMockModeAppSumo(unittest.TestCase):
    def test_valid_code_grants_lifetime_and_credits(self):
        c = _mock_client()
        r = c.redeem_appsumo("DRESC-ABC123")
        self.assertTrue(r["valid"])
        self.assertTrue(r["is_lifetime"])
        self.assertEqual(r["balance"], 500)

    def test_invalid_format_raises(self):
        c = _mock_client()
        with self.assertRaises(ValueError):
            c.redeem_appsumo("INVALID-CODE")

    def test_wrong_prefix_raises(self):
        c = _mock_client()
        with self.assertRaises(ValueError):
            c.redeem_appsumo("WRONG-AB1234")

    def test_too_long_suffix_raises(self):
        c = _mock_client()
        with self.assertRaises(ValueError):
            c.redeem_appsumo("DRESC-TOOLONG1")

    def test_double_redemption_raises(self):
        c = _mock_client()
        c.redeem_appsumo("DRESC-ONCE11")
        with self.assertRaises(ValueError):
            c.redeem_appsumo("DRESC-ONCE11")

    def test_different_codes_both_accepted(self):
        c = _mock_client()
        c.redeem_appsumo("DRESC-CODE01")
        r2 = c.redeem_appsumo("DRESC-CODE02")
        # balance accumulates: 500 + 500
        self.assertEqual(r2["balance"], 1000)

    def test_lowercase_code_normalised(self):
        c = _mock_client()
        r = c.redeem_appsumo("dresc-abc456")
        self.assertTrue(r["valid"])


class TestNetworkFallbackToMock(unittest.TestCase):
    """When network calls fail, client must silently switch to mock mode."""

    def test_network_error_switches_to_mock(self):
        c = _real_client()
        self.assertFalse(c.is_mock_mode)
        # Simulate connection refused
        with patch("requests.request", side_effect=requests.exceptions.ConnectionError("refused")):
            balance = c.get_balance()
        # Should not raise; client should now be in mock mode
        self.assertTrue(c.is_mock_mode)
        self.assertEqual(balance, 0)

    def test_timeout_switches_to_mock(self):
        c = _real_client()
        with patch("requests.request", side_effect=requests.exceptions.Timeout("timed out")):
            balance = c.get_balance()
        self.assertTrue(c.is_mock_mode)

    def test_http_500_raises_and_switches_to_mock(self):
        c = _real_client()
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500")
        with patch("requests.request", return_value=mock_response):
            balance = c.get_balance()
        self.assertTrue(c.is_mock_mode)

    def test_after_fallback_subsequent_calls_use_mock(self):
        c = _real_client()
        with patch("requests.request", side_effect=requests.exceptions.ConnectionError("refused")):
            c.get_balance()
        # Now in mock mode — adding credits locally should work
        c.confirm_payment("mock_starter_after_fallback")
        self.assertEqual(c.get_balance(), 100)


class TestCheckoutURLGeneration(unittest.TestCase):
    def test_mock_url_contains_pack_and_email(self):
        c = _mock_client()
        url = c.build_checkout_url("standard", "user@example.com")
        self.assertIn("standard", url)
        self.assertIn("user@example.com", url)

    def test_mock_url_contains_device_token(self):
        c = _mock_client()
        url = c.build_checkout_url("plus", "user@example.com")
        self.assertIn(c.device_token, url)

    def test_real_mode_url_uses_base_url(self):
        c = _real_client()
        url = c.build_checkout_url("starter", "a@b.com")
        self.assertIn("localhost:9999", url)
        self.assertIn("starter", url)
        self.assertIn("a@b.com", url)

    def test_all_packs_produce_url(self):
        c = _mock_client()
        for pack in ["starter", "standard", "plus", "unlimited"]:
            url = c.build_checkout_url(pack, "a@b.com")
            self.assertIsInstance(url, str)
            self.assertGreater(len(url), 10)


class TestValidateLicenceAfterDepletion(unittest.TestCase):
    def test_valid_after_credits_added(self):
        c = _mock_client()
        c.confirm_payment("mock_starter_lic_check")
        r = c.validate_licence()
        self.assertTrue(r["valid"])

    def test_invalid_after_all_credits_spent(self):
        c = _mock_client()
        c.confirm_payment("mock_starter_spent")  # 100 credits
        c.deduct_credits(100)
        r = c.validate_licence()
        # 0 credits, not lifetime → invalid
        self.assertFalse(r["valid"])

    def test_lifetime_always_valid(self):
        c = _mock_client()
        c.confirm_payment("mock_unlimited_always")
        r = c.validate_licence()
        self.assertTrue(r["valid"])
        self.assertTrue(r["is_lifetime"])


if __name__ == "__main__":
    unittest.main()
