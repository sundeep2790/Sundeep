import re
import requests
import logging

logger = logging.getLogger("datarescue-client")

class DataRescueClient:
    def __init__(self, api_base_url: str = None, email: str = None, device_token: str = None):
        self.api_base_url = api_base_url
        self.email = email
        self.device_token = device_token
        
        # Local mock state when offline / in mock mode
        self.is_mock_mode = (api_base_url is None)
        self.mock_balance = 0
        self.mock_is_lifetime = False
        self.mock_redeemed_codes = set()
        self.mock_used_session_ids = set()

    def _should_mock(self) -> bool:
        return self.is_mock_mode

    def _request(self, method: str, endpoint: str, headers: dict = None, json_data: dict = None) -> dict:
        if self._should_mock():
            return None
            
        url = f"{self.api_base_url.rstrip('/')}{endpoint}"
        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                json=json_data,
                timeout=5.0
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.warning(
                f"DataRescue backend is unreachable ({e}). "
                "Switching to offline/mock client mode."
            )
            self.is_mock_mode = True
            return None

    def get_balance(self) -> int:
        headers = {
            "X-Device-Token": self.device_token,
            "X-User-Email": self.email
        }
        res = self._request("GET", "/api/credits/balance", headers=headers)
        if res is not None:
            self.mock_balance = res.get("balance", 0)
            self.mock_is_lifetime = res.get("is_lifetime", False)
            return self.mock_balance
            
        logger.info(
            f"[Mock Mode] get_balance() for {self.email} -> {self.mock_balance} credits "
            f"(Lifetime: {self.mock_is_lifetime})"
        )
        return self.mock_balance

    def deduct_credits(self, amount: int) -> int:
        json_data = {
            "device_token": self.device_token,
            "email": self.email,
            "amount": amount
        }
        res = self._request("POST", "/api/credits/deduct", json_data=json_data)
        if res is not None:
            self.mock_balance = res.get("balance", 0)
            self.mock_is_lifetime = res.get("is_lifetime", False)
            return self.mock_balance
            
        logger.info(f"[Mock Mode] deduct_credits({amount}) for {self.email}")
        if not self.mock_is_lifetime:
            if self.mock_balance < amount:
                raise ValueError("Insufficient credits in mock mode")
            self.mock_balance -= amount
        return self.mock_balance

    def confirm_payment(self, stripe_session_id: str) -> dict:
        json_data = {
            "stripe_session_id": stripe_session_id,
            "device_token": self.device_token,
            "email": self.email
        }
        res = self._request("POST", "/api/credits/confirm", json_data=json_data)
        if res is not None:
            self.mock_balance = res.get("balance", 0)
            self.mock_is_lifetime = res.get("is_lifetime", False)
            return res
            
        logger.info(f"[Mock Mode] confirm_payment({stripe_session_id})")
        if stripe_session_id in self.mock_used_session_ids:
            raise ValueError("Stripe session already processed in mock mode")
            
        self.mock_used_session_ids.add(stripe_session_id)
        
        # Parse pack_id from mock stripe session id
        session_lower = stripe_session_id.lower()
        pack_id = "starter"
        if "starter" in session_lower:
            pack_id = "starter"
        elif "standard" in session_lower:
            pack_id = "standard"
        elif "plus" in session_lower:
            pack_id = "plus"
        elif "unlimited" in session_lower:
            pack_id = "unlimited"
        elif "appsumo" in session_lower:
            pack_id = "appsumo"
            
        credits_to_add = 0
        if pack_id == "starter":
            credits_to_add = 100
        elif pack_id == "standard":
            credits_to_add = 250
        elif pack_id == "plus":
            credits_to_add = 500
        elif pack_id == "unlimited":
            credits_to_add = 0
            self.mock_is_lifetime = True
        elif pack_id == "appsumo":
            credits_to_add = 500
            self.mock_is_lifetime = True
            
        self.mock_balance += credits_to_add
        
        return {
            "balance": self.mock_balance,
            "is_lifetime": self.mock_is_lifetime,
            "email": self.email
        }

    def validate_licence(self) -> dict:
        json_data = {
            "device_token": self.device_token,
            "email": self.email
        }
        res = self._request("POST", "/api/licence/validate", json_data=json_data)
        if res is not None:
            self.mock_balance = res.get("balance", 0)
            self.mock_is_lifetime = res.get("is_lifetime", False)
            return res
            
        logger.info(f"[Mock Mode] validate_licence() for {self.email}")
        valid = self.mock_is_lifetime or self.mock_balance > 0
        return {
            "valid": valid,
            "balance": self.mock_balance,
            "is_lifetime": self.mock_is_lifetime
        }

    def redeem_appsumo(self, code: str) -> dict:
        json_data = {
            "code": code,
            "device_token": self.device_token,
            "email": self.email
        }
        res = self._request("POST", "/api/licence/appsumo", json_data=json_data)
        if res is not None:
            self.mock_balance = res.get("balance", 0)
            self.mock_is_lifetime = res.get("is_lifetime", False)
            return res
            
        logger.info(f"[Mock Mode] redeem_appsumo({code})")
        code_upper = code.upper().strip()
        if not re.match(r"^DRESC-[A-Z0-9]{6}$", code_upper):
            raise ValueError("Invalid AppSumo code format in mock mode")
            
        if code_upper in self.mock_redeemed_codes:
            raise ValueError("AppSumo code already redeemed in mock mode")
            
        self.mock_redeemed_codes.add(code_upper)
        self.mock_is_lifetime = True
        self.mock_balance += 500
        
        return {
            "valid": True,
            "balance": self.mock_balance,
            "is_lifetime": self.mock_is_lifetime,
            "code": code_upper
        }

    def build_checkout_url(self, pack_id: str, email: str) -> str:
        if self._should_mock():
            return f"http://mock-checkout.local/checkout?pack_id={pack_id}&email={email}&device_token={self.device_token}"
            
        return f"{self.api_base_url.rstrip('/')}/api/credits/checkout?pack_id={pack_id}&email={email}"
