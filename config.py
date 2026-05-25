import os
import sys
import json
import uuid
from datetime import datetime, timedelta, timezone
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

# Resolve appropriate OS App Data directory
if sys.platform == "win32":
    app_data_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~\\AppData\\Roaming")), "DataRescue")
elif sys.platform == "darwin":
    app_data_dir = os.path.join(os.path.expanduser("~/Library/Application Support"), "DataRescue")
else:
    app_data_dir = os.path.join(os.path.expanduser("~/.config"), "DataRescue")

CONFIG_PATH = os.path.join(app_data_dir, "config.enc")

def get_fernet_key(device_token: str) -> bytes:
    """
    Derive a 32-byte Fernet key from the device token.
    Key derived from: PBKDF2HMAC(SHA256, salt=device_token first 16 bytes, iterations=100000)
    """
    salt = device_token[:16].encode("utf-8")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000
    )
    derived = kdf.derive(device_token.encode("utf-8"))
    return base64.urlsafe_b64encode(derived)

def get_default_config() -> dict:
    """
    Return a default config structure with generated device_token.
    """
    return {
        "email": "",
        "device_token": str(uuid.uuid4()),
        "credits": 0,
        "credits_cached_at": datetime.now(timezone.utc).isoformat(),
        "is_lifetime": False
    }

def load_config() -> dict:
    """
    Load, decrypt, and parse the encrypted configuration.
    If the file does not exist or fails to decrypt, creates and returns a default configuration.
    """
    if not os.path.exists(CONFIG_PATH):
        default_config = get_default_config()
        save_config(default_config)
        return default_config
    
    try:
        with open(CONFIG_PATH, "rb") as f:
            data = f.read()
            
        # The first 36 bytes are the plaintext device_token (UUID string)
        if len(data) < 36:
            raise ValueError("Config file too short.")
            
        device_token = data[:36].decode("utf-8")
        encrypted_content = data[36:]
        
        key = get_fernet_key(device_token)
        fernet = Fernet(key)
        decrypted_content = fernet.decrypt(encrypted_content)
        
        config = json.loads(decrypted_content.decode("utf-8"))
        return config
    except Exception:
        # Gracefully fall back to default config if decryption fails
        default_config = get_default_config()
        save_config(default_config)
        return default_config

def save_config(config_data: dict) -> None:
    """
    Encrypt and save configuration data to the app data directory.
    Prefixes the file with the plaintext device_token for key derivation on load.
    """
    device_token = config_data.get("device_token")
    if not device_token:
        device_token = str(uuid.uuid4())
        config_data["device_token"] = device_token
        
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    
    key = get_fernet_key(device_token)
    fernet = Fernet(key)
    
    serialized = json.dumps(config_data).encode("utf-8")
    encrypted = fernet.encrypt(serialized)
    
    # Store device_token as prefix (36 bytes) + encrypted content
    payload = device_token.encode("utf-8") + encrypted
    
    with open(CONFIG_PATH, "wb") as f:
        f.write(payload)

def is_credits_cache_valid(config_data: dict) -> bool:
    """
    Verify if the cached credits are within the 72-hour grace period.
    """
    cached_at_str = config_data.get("credits_cached_at")
    if not cached_at_str:
        return False
    try:
        cached_at = datetime.fromisoformat(cached_at_str)
        # Check if last cached time was within 72 hours
        return datetime.now(timezone.utc) - cached_at <= timedelta(hours=72)
    except Exception:
        return False

def get_credits() -> int:
    """
    Get credits from local config if within the 72-hour offline grace period.
    """
    config = load_config()
    if config.get("is_lifetime", False):
        return 999999  # Unlimited representation
        
    if is_credits_cache_valid(config):
        return config.get("credits", 0)
        
    return 0

def set_credits(n: int) -> None:
    """
    Set credits in local config and update the cached time.
    """
    config = load_config()
    config["credits"] = n
    config["credits_cached_at"] = datetime.now(timezone.utc).isoformat()
    save_config(config)

def set_email(email: str) -> None:
    """
    Set the user's email in the configuration.
    """
    config = load_config()
    config["email"] = email
    save_config(config)

def set_lifetime(is_lifetime: bool) -> None:
    """
    Set lifetime status in the configuration.
    """
    config = load_config()
    config["is_lifetime"] = is_lifetime
    save_config(config)
