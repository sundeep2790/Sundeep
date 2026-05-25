import unittest
from datarescue.api.client import DataRescueClient

class TestDataRescueClientMock(unittest.TestCase):
    def setUp(self):
        self.email = "client@example.com"
        self.device_token = "client-token-xyz"
        # Instantiate in mock mode by passing api_base_url=None
        self.client = DataRescueClient(api_base_url=None, email=self.email, device_token=self.device_token)

    def test_mock_balance_and_deduction(self):
        # 1. Check initial balance
        self.assertEqual(self.client.get_balance(), 0)
        
        # 2. Confirm payment for mock starter (100 credits)
        res = self.client.confirm_payment("mock_starter_xyz")
        self.assertEqual(res["balance"], 100)
        self.assertEqual(self.client.get_balance(), 100)
        
        # 3. Deduct credits
        new_balance = self.client.deduct_credits(30)
        self.assertEqual(new_balance, 70)
        
        # 4. Deduct more than balance (should raise ValueError)
        with self.assertRaises(ValueError):
            self.client.deduct_credits(80)

    def test_mock_licence_and_appsumo(self):
        # 1. Licence is not valid initially
        lic = self.client.validate_licence()
        self.assertEqual(lic["valid"], False)
        
        # 2. Redeem AppSumo code
        res = self.client.redeem_appsumo("DRESC-SUMO99")
        self.assertEqual(res["valid"], True)
        self.assertEqual(res["balance"], 500)
        self.assertEqual(res["is_lifetime"], True)
        
        # 3. Licence is now valid
        lic = self.client.validate_licence()
        self.assertEqual(lic["valid"], True)
        
        # 4. Prevent double redemption
        with self.assertRaises(ValueError):
            self.client.redeem_appsumo("DRESC-SUMO99")
            
        # 5. Invalid format code
        with self.assertRaises(ValueError):
            self.client.redeem_appsumo("INVALID-CODE")

    def test_build_checkout_url(self):
        url = self.client.build_checkout_url("standard", self.email)
        self.assertIn("standard", url)
        self.assertIn(self.email, url)
        self.assertIn(self.device_token, url)

if __name__ == "__main__":
    unittest.main()
