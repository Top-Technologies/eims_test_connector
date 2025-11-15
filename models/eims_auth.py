import json
import requests
from datetime import datetime, timedelta

# --- Hardcoded credentials ---
CLIENT_ID = "fa39eee3-dfd7-4d7d-b62f-26e474a0c8c1"
CLIENT_SECRET = "a33a3e32-566c-482f-960f-8fe230ea74cf"
API_KEY = "0702d840-e684-455e-9147-6ce8f9cd6b5a"
TIN = "0054835018"
LOGIN_URL = "http://core.mor.gov.et/auth/login"

# --- Cache token globally ---
_TOKEN_CACHE = {
    "access_token": None,
    "expiry": None,
    "encryption_key": None
}


def get_eims_token():
    """
    Returns a valid EIMS token. Automatically refreshes if expired.
    """
    global _TOKEN_CACHE

    # If token exists and is not expired, return it
    if _TOKEN_CACHE["access_token"] and _TOKEN_CACHE["expiry"]:
        if datetime.utcnow() < _TOKEN_CACHE["expiry"]:
            return _TOKEN_CACHE["access_token"], _TOKEN_CACHE["encryption_key"]

    # Otherwise, request a new token
    payload = {
        "clientId": CLIENT_ID,
        "clientSecret": CLIENT_SECRET,
        "apikey": API_KEY,
        "tin": TIN
    }
    headers = {"Content-Type": "application/json"}

    response = requests.post(LOGIN_URL, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()

    token = data["data"]["accessToken"]
    encryption_key = data["data"].get("encryptionKey")

    # EIMS tokens usually expire in 1 hour — adjust if needed
    expiry = datetime.utcnow() + timedelta(minutes=55)

    # Cache the token
    _TOKEN_CACHE.update({
        "access_token": token,
        "expiry": expiry,
        "encryption_key": encryption_key
    })

    return token, encryption_key
