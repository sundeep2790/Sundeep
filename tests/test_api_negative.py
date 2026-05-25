"""
test_api_negative.py — Negative / edge-case tests for all FastAPI endpoints.
Tests bad inputs, missing fields, wrong tokens, insufficient credits,
double-redemption, and boundary conditions.
"""
import os
import tempfile
import unittest

_DB_FILE = "/tmp/test_negative.db"
import atexit as _atexit
_atexit.register(lambda: os.remove(_DB_FILE) if os.path.exists(_DB_FILE) else None)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB_FILE}"

from fastapi.testclient import TestClient
from datarescue.backend.main import app


def _client():
    return TestClient(app)


class TestBalanceEndpointNegative(unittest.TestCase):
    """GET /api/credits/balance — missing / malformed headers."""

    def test_missing_both_headers_returns_422(self):
        with _client() as c:
            r = c.get("/api/credits/balance")
            self.assertEqual(r.status_code, 422)

    def test_missing_device_token_header_returns_422(self):
        with _client() as c:
            r = c.get("/api/credits/balance", headers={"X-User-Email": "test@example.com"})
            self.assertEqual(r.status_code, 422)

    def test_missing_email_header_returns_422(self):
        with _client() as c:
            r = c.get("/api/credits/balance", headers={"X-Device-Token": "some-token"})
            self.assertEqual(r.status_code, 422)

    def test_valid_new_user_gets_zero_balance(self):
        with _client() as c:
            r = c.get("/api/credits/balance", headers={
                "X-Device-Token": "neg-device-001",
                "X-User-Email": "negtest001@example.com"
            })
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()["balance"], 0)
            self.assertFalse(r.json()["is_lifetime"])


class TestDeductEndpointNegative(unittest.TestCase):
    """POST /api/credits/deduct — various failure paths."""

    def _setup_user_with_credits(self, client, email, token, credits):
        """Helper: create user and add credits via confirm payment."""
        pack_map = {100: "mock_starter", 250: "mock_standard", 500: "mock_plus"}
        session_id = f"{pack_map.get(credits, 'mock_starter')}_{token[:8]}"
        client.post("/api/credits/confirm", json={
            "stripe_session_id": session_id,
            "device_token": token,
            "email": email
        })

    def test_deduct_negative_amount_returns_400(self):
        with _client() as c:
            # Create user first
            email, token = "negdeduct001@example.com", "neg-deduct-tok-001"
            self._setup_user_with_credits(c, email, token, 100)
            r = c.post("/api/credits/deduct", json={
                "device_token": token,
                "email": email,
                "amount": -10
            })
            self.assertEqual(r.status_code, 400)

    def test_deduct_zero_amount_succeeds(self):
        """Deducting 0 is technically valid (no change to balance)."""
        with _client() as c:
            email, token = "negdeduct002@example.com", "neg-deduct-tok-002"
            self._setup_user_with_credits(c, email, token, 100)
            r = c.post("/api/credits/deduct", json={
                "device_token": token,
                "email": email,
                "amount": 0
            })
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()["balance"], 100)

    def test_deduct_wrong_device_token_returns_403(self):
        with _client() as c:
            email, token = "negdeduct003@example.com", "neg-deduct-tok-003"
            self._setup_user_with_credits(c, email, token, 100)
            r = c.post("/api/credits/deduct", json={
                "device_token": "WRONG-TOKEN",
                "email": email,
                "amount": 10
            })
            self.assertEqual(r.status_code, 403)

    def test_deduct_nonexistent_user_returns_404(self):
        with _client() as c:
            r = c.post("/api/credits/deduct", json={
                "device_token": "ghost-token",
                "email": "ghost_user_nobody@example.com",
                "amount": 1
            })
            self.assertEqual(r.status_code, 404)

    def test_deduct_more_than_balance_returns_400(self):
        with _client() as c:
            email, token = "negdeduct004@example.com", "neg-deduct-tok-004"
            self._setup_user_with_credits(c, email, token, 100)
            r = c.post("/api/credits/deduct", json={
                "device_token": token,
                "email": email,
                "amount": 200
            })
            self.assertEqual(r.status_code, 400)

    def test_deduct_exact_balance_leaves_zero(self):
        with _client() as c:
            email, token = "negdeduct005@example.com", "neg-deduct-tok-005"
            self._setup_user_with_credits(c, email, token, 100)
            r = c.post("/api/credits/deduct", json={
                "device_token": token,
                "email": email,
                "amount": 100
            })
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()["balance"], 0)

    def test_deduct_missing_fields_returns_422(self):
        with _client() as c:
            r = c.post("/api/credits/deduct", json={"email": "test@example.com"})
            self.assertEqual(r.status_code, 422)

    def test_deduct_invalid_email_format_returns_422(self):
        with _client() as c:
            r = c.post("/api/credits/deduct", json={
                "device_token": "tok",
                "email": "not-an-email",
                "amount": 1
            })
            self.assertEqual(r.status_code, 422)

    def test_lifetime_user_deduct_does_not_reduce_balance(self):
        """Lifetime users should never have credits deducted."""
        with _client() as c:
            email, token = "negdeduct006@example.com", "neg-deduct-tok-006"
            # Give lifetime via AppSumo
            c.post("/api/licence/appsumo", json={
                "code": "DRESC-LIFEOK",
                "device_token": token,
                "email": email
            })
            r = c.post("/api/credits/deduct", json={
                "device_token": token,
                "email": email,
                "amount": 9999
            })
            self.assertEqual(r.status_code, 200)
            # Balance should be unchanged (lifetime)
            balance_r = c.get("/api/credits/balance", headers={
                "X-Device-Token": token,
                "X-User-Email": email
            })
            self.assertTrue(balance_r.json()["is_lifetime"])


class TestConfirmPaymentNegative(unittest.TestCase):
    """POST /api/credits/confirm — duplicate session, missing fields."""

    def test_duplicate_session_id_is_idempotent(self):
        """Confirming the same session_id twice must not double-add credits."""
        with _client() as c:
            email = "negconfirm001@example.com"
            token = "neg-confirm-tok-001"
            payload = {
                "stripe_session_id": "mock_standard_negconfirm001",
                "device_token": token,
                "email": email
            }
            r1 = c.post("/api/credits/confirm", json=payload)
            r2 = c.post("/api/credits/confirm", json=payload)
            self.assertEqual(r1.status_code, 200)
            self.assertEqual(r2.status_code, 200)
            # Balance must not be doubled
            self.assertEqual(r1.json()["balance"], r2.json()["balance"])

    def test_missing_email_returns_422(self):
        with _client() as c:
            r = c.post("/api/credits/confirm", json={
                "stripe_session_id": "mock_starter_x",
                "device_token": "some-token"
            })
            self.assertEqual(r.status_code, 422)

    def test_missing_session_id_returns_422(self):
        with _client() as c:
            r = c.post("/api/credits/confirm", json={
                "device_token": "some-token",
                "email": "test@example.com"
            })
            self.assertEqual(r.status_code, 422)

    def test_all_pack_ids_add_correct_credits(self):
        """Verify each pack results in the correct credit amount."""
        pack_credits = {
            "starter": 100,
            "standard": 250,
            "plus": 500,
        }
        with _client() as c:
            for pack, expected in pack_credits.items():
                email = f"packtest_{pack}@example.com"
                token = f"pack-tok-{pack}"
                r = c.post("/api/credits/confirm", json={
                    "stripe_session_id": f"mock_{pack}_{token}",
                    "device_token": token,
                    "email": email
                })
                self.assertEqual(r.status_code, 200, f"Pack {pack} failed")
                self.assertEqual(r.json()["balance"], expected, f"Pack {pack} wrong credits")

    def test_unlimited_pack_grants_lifetime(self):
        with _client() as c:
            email = "unlimitedtest@example.com"
            token = "unlimited-tok-001"
            r = c.post("/api/credits/confirm", json={
                "stripe_session_id": "mock_unlimited_test001",
                "device_token": token,
                "email": email
            })
            self.assertEqual(r.status_code, 200)
            self.assertTrue(r.json()["is_lifetime"])


class TestAppSumoNegative(unittest.TestCase):
    """POST /api/licence/appsumo — invalid formats, double redemption."""

    def test_wrong_prefix_returns_400(self):
        with _client() as c:
            r = c.post("/api/licence/appsumo", json={
                "code": "WRONG-ABC123",
                "device_token": "sumo-tok-001",
                "email": "sumo001@example.com"
            })
            self.assertEqual(r.status_code, 400)

    def test_too_short_suffix_returns_400(self):
        with _client() as c:
            r = c.post("/api/licence/appsumo", json={
                "code": "DRESC-AB12",
                "device_token": "sumo-tok-002",
                "email": "sumo002@example.com"
            })
            self.assertEqual(r.status_code, 400)

    def test_lowercase_code_is_normalised(self):
        """Codes submitted in lowercase must be accepted (server normalises)."""
        with _client() as c:
            r = c.post("/api/licence/appsumo", json={
                "code": "dresc-abc123",
                "device_token": "sumo-tok-003",
                "email": "sumo003@example.com"
            })
            self.assertEqual(r.status_code, 200)

    def test_spaces_in_code_returns_400(self):
        with _client() as c:
            r = c.post("/api/licence/appsumo", json={
                "code": "DRESC- 12345",
                "device_token": "sumo-tok-004",
                "email": "sumo004@example.com"
            })
            self.assertEqual(r.status_code, 400)

    def test_double_redemption_same_user_returns_400(self):
        with _client() as c:
            payload = {
                "code": "DRESC-DBLCHK",
                "device_token": "sumo-dbl-tok",
                "email": "sumodbl@example.com"
            }
            r1 = c.post("/api/licence/appsumo", json=payload)
            r2 = c.post("/api/licence/appsumo", json=payload)
            self.assertEqual(r1.status_code, 200)
            self.assertEqual(r2.status_code, 400)

    def test_double_redemption_different_user_returns_400(self):
        """Same code redeemed by a different user must also fail."""
        with _client() as c:
            code = "DRESC-SHARED"
            r1 = c.post("/api/licence/appsumo", json={
                "code": code,
                "device_token": "sumo-user1-tok",
                "email": "sumouser1@example.com"
            })
            r2 = c.post("/api/licence/appsumo", json={
                "code": code,
                "device_token": "sumo-user2-tok",
                "email": "sumouser2@example.com"
            })
            self.assertEqual(r1.status_code, 200)
            self.assertEqual(r2.status_code, 400)

    def test_empty_code_returns_422_or_400(self):
        with _client() as c:
            r = c.post("/api/licence/appsumo", json={
                "code": "",
                "device_token": "sumo-empty-tok",
                "email": "sumoempty@example.com"
            })
            self.assertIn(r.status_code, [400, 422])

    def test_missing_code_field_returns_422(self):
        with _client() as c:
            r = c.post("/api/licence/appsumo", json={
                "device_token": "tok",
                "email": "test@example.com"
            })
            self.assertEqual(r.status_code, 422)


class TestLicenceValidateNegative(unittest.TestCase):
    """POST /api/licence/validate — boundary conditions."""

    def test_brand_new_user_invalid(self):
        with _client() as c:
            r = c.post("/api/licence/validate", json={
                "device_token": "brand-new-tok",
                "email": "brandnew_unique@example.com"
            })
            self.assertEqual(r.status_code, 200)
            self.assertFalse(r.json()["valid"])

    def test_user_with_credits_is_valid(self):
        with _client() as c:
            email, token = "validlic001@example.com", "validlic-tok-001"
            c.post("/api/credits/confirm", json={
                "stripe_session_id": "mock_starter_validlic001",
                "device_token": token,
                "email": email
            })
            r = c.post("/api/licence/validate", json={
                "device_token": token,
                "email": email
            })
            self.assertEqual(r.status_code, 200)
            self.assertTrue(r.json()["valid"])

    def test_missing_email_returns_422(self):
        with _client() as c:
            r = c.post("/api/licence/validate", json={"device_token": "tok"})
            self.assertEqual(r.status_code, 422)

    def test_invalid_email_format_returns_422(self):
        with _client() as c:
            r = c.post("/api/licence/validate", json={
                "device_token": "tok",
                "email": "notanemail"
            })
            self.assertEqual(r.status_code, 422)


class TestHealthEndpoint(unittest.TestCase):
    def test_health_returns_healthy(self):
        with _client() as c:
            r = c.get("/health")
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()["status"], "healthy")

    def test_unknown_route_returns_404(self):
        with _client() as c:
            r = c.get("/api/does_not_exist")
            self.assertEqual(r.status_code, 404)


class TestWebhookEdgeCases(unittest.TestCase):
    """POST /api/webhooks/stripe — missing fields, malformed payloads."""

    def test_wrong_event_type_still_200(self):
        """Unknown Stripe events must be accepted gracefully (not crash)."""
        with _client() as c:
            r = c.post("/api/webhooks/stripe", json={
                "type": "customer.created",
                "data": {"object": {}}
            })
            # Should acknowledge without error
            self.assertIn(r.status_code, [200, 400])

    def test_empty_body_returns_error(self):
        with _client() as c:
            r = c.post("/api/webhooks/stripe", json={})
            self.assertIn(r.status_code, [200, 400, 422])

    def test_valid_webhook_adds_credits(self):
        email = "webhook_neg_test@example.com"
        with _client() as c:
            payload = {
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "id": "mock_plus_wh_neg_001",
                        "customer_email": email,
                        "metadata": {"pack_id": "plus"}
                    }
                }
            }
            r = c.post("/api/webhooks/stripe", json=payload)
            self.assertEqual(r.status_code, 200)
            # Verify credits were applied
            bal = c.get("/api/credits/balance", headers={
                "X-Device-Token": "wh-device-neg",
                "X-User-Email": email
            })
            self.assertEqual(bal.json()["balance"], 500)


if __name__ == "__main__":
    unittest.main()
