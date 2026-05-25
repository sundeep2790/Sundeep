import os
import unittest
from fastapi.testclient import TestClient

# Use an absolute writable path for the test database so the lifespan
# CREATE TABLE call does not fail with a disk I/O error on restricted CWDs.
import tempfile
_DB_FILE = "/tmp/test_datarescue.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB_FILE}"

from datarescue.backend.main import app

# Each test uses `with TestClient(app) as client:` which triggers the FastAPI lifespan
# startup event (Base.metadata.create_all) — the officially supported FastAPI test pattern.
# Tests use distinct email addresses so there is no cross-test data conflict.

class TestDataRescueAPI(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        # Remove the test DB file after the full class is done
        if os.path.exists(_DB_FILE):
            try:
                os.remove(_DB_FILE)
            except Exception:
                pass

    def test_health(self):
        with TestClient(app) as client:
            response = client.get("/health")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["status"], "healthy")

    def test_credits_flow(self):
        email = "credits_test@example.com"
        device_token = "credits-device-token-1234"

        with TestClient(app) as client:
            # 1. Get balance (upsert creates user with 0 credits)
            headers = {
                "X-Device-Token": device_token,
                "X-User-Email": email
            }
            response = client.get("/api/credits/balance", headers=headers)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["balance"], 0)
            self.assertEqual(data["is_lifetime"], False)

            # 2. Confirm a mock payment (starter pack)
            confirm_data = {
                "stripe_session_id": "mock_starter_credits_test",
                "device_token": device_token,
                "email": email
            }
            response = client.post("/api/credits/confirm", json=confirm_data)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["balance"], 100)

            # 3. Deduct credits
            deduct_data = {
                "device_token": device_token,
                "email": email,
                "amount": 30
            }
            response = client.post("/api/credits/deduct", json=deduct_data)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["balance"], 70)

            # 4. Deduct more than balance (should fail with 400)
            deduct_data["amount"] = 80
            response = client.post("/api/credits/deduct", json=deduct_data)
            self.assertEqual(response.status_code, 400)

    def test_licence_validation(self):
        val_email = "licence_test@example.com"
        val_token = "licence-token-999"

        with TestClient(app) as client:
            val_data = {
                "device_token": val_token,
                "email": val_email
            }

            # 1. New user — licence not valid (0 credits, not lifetime)
            response = client.post("/api/licence/validate", json=val_data)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["valid"], False)

            # 2. Redeem AppSumo code (DRESC-XXXXXX format)
            appsumo_data = {
                "code": "DRESC-SUMO12",
                "device_token": val_token,
                "email": val_email
            }
            response = client.post("/api/licence/appsumo", json=appsumo_data)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["valid"], True)
            self.assertEqual(data["balance"], 500)
            self.assertEqual(data["is_lifetime"], True)

            # 3. Licence is now valid
            response = client.post("/api/licence/validate", json=val_data)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["valid"], True)
            self.assertEqual(response.json()["balance"], 500)

            # 4. Prevent double redemption
            response = client.post("/api/licence/appsumo", json=appsumo_data)
            self.assertEqual(response.status_code, 400)

    def test_stripe_webhook_mock(self):
        webhook_email = "webhook_test@example.com"

        with TestClient(app) as client:
            # Trigger mock webhook (no Stripe key set → mock mode)
            payload = {
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "id": "mock_plus_session_webhook_test",
                        "customer_email": webhook_email,
                        "metadata": {
                            "pack_id": "plus"
                        }
                    }
                }
            }
            response = client.post("/api/webhooks/stripe", json=payload)
            self.assertEqual(response.status_code, 200)

            # Verify credits were added — balance endpoint will upsert the pending token
            headers = {
                "X-Device-Token": "real-device-token-for-webhook-user",
                "X-User-Email": webhook_email
            }
            response = client.get("/api/credits/balance", headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["balance"], 500)

if __name__ == "__main__":
    unittest.main()
