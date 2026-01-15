import json
import requests
from datetime import datetime, timedelta
from odoo import api, models
from odoo.exceptions import UserError
from ..services.crypto_utils import sign_eims_request
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

# Token cache (same as before)
_TOKEN_CACHE = {
    "access_token": None,
    "expiry": None,
    "encryption_key": None
}


class EimsAuth(models.AbstractModel):
    _name = "eims.auth"
    _description = "EIMS Authentication Handler"

    @api.model
    def get_eims_http_session(self):
        """Returns a requests Session configured with EIMS retry logic."""
        retry_strategy = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST", "GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session = requests.Session()
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    @api.model
    def get_eims_credentials(self):
        """
        Read credentials securely from Odoo System Parameters.
        Only Admins can modify them.
        """
        ICP = self.env['ir.config_parameter'].sudo()

        client_id = ICP.get_param("eims.client_id")
        client_secret = ICP.get_param("eims.client_secret")
        api_key = ICP.get_param("eims.api_key")
        tin = ICP.get_param("eims.tin")
        login_url = ICP.get_param("eims.login_url") or "https://core.mor.gov.et/auth/login"

        missing = []
        if not client_id: missing.append("eims.client_id")
        if not client_secret: missing.append("eims.client_secret")
        if not api_key: missing.append("eims.api_key")
        if not tin: missing.append("eims.tin")

        if missing:
            raise UserError(
                "Missing EIMS credentials:\n- " + "\n- ".join(missing) +
                "\n\nGo to: Settings → Technical → System Parameters"
            )

        return client_id, client_secret, api_key, tin, login_url

    @api.model
    def get_eims_token(self):
        """
        Returns a valid EIMS token.
        Loads credentials from Odoo System Parameters (secure),
        caches token for 55 minutes.
        """
        global _TOKEN_CACHE

        # Return cached token if still valid
        if _TOKEN_CACHE["access_token"] and _TOKEN_CACHE["expiry"]:
            if datetime.utcnow() < _TOKEN_CACHE["expiry"]:
                return (
                    _TOKEN_CACHE["access_token"],
                    _TOKEN_CACHE["encryption_key"]
                )

        # Load secure credentials
        client_id, client_secret, api_key, tin, login_url = self.get_eims_credentials()

        # Prepare payload
        payload = {
            "clientId": client_id,
            "clientSecret": client_secret,
            "apikey": api_key,
            "tin": tin
        }

        headers = {"Content-Type": "application/json"}

        # Call EIMS login API
        signed_payload = sign_eims_request(payload)
        response = requests.post(login_url, json=signed_payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        token = data["data"]["accessToken"]
        encryption_key = data["data"].get("encryptionKey")
        expiry = datetime.utcnow() + timedelta(minutes=55)

        # Cache token
        _TOKEN_CACHE.update({
            "access_token": token,
            "expiry": expiry,
            "encryption_key": encryption_key
        })

        return token, encryption_key
