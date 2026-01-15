import json
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from odoo.modules.module import get_module_resource
from odoo.exceptions import UserError

def sign_eims_request(request_payload: dict) -> dict:
    """
    Sign ONLY the inner request payload using SHA512withRSA
    """

    try:
        private_key_path = get_module_resource(
            "eims_test_connector_12", "static", "certs", "private_key.key"
        )
        cert_path = get_module_resource(
            "eims_test_connector_12", "static", "certs", "0054835018-3142D2B84A.pem"
        )

        if not private_key_path or not cert_path:
            raise UserError("EIMS certificate files not found.")

        # 1️⃣ Canonical JSON (NO pretty print, NO spaces)
        serialized = json.dumps(
            request_payload,
            separators=(",", ":"),
            ensure_ascii=False
        ).encode("utf-8")

        # 2️⃣ Load private key
        with open(private_key_path, "rb") as f:
            private_key = serialization.load_pem_private_key(
                f.read(),
                password=None
            )

        # 3️⃣ Sign
        signature = private_key.sign(
            serialized,
            padding.PKCS1v15(),
            hashes.SHA512()
        )

        # 4️⃣ Base64 encode
        signature_b64 = base64.b64encode(signature).decode()

        # 5️⃣ Certificate MUST be base64 (NOT raw PEM)
        with open(cert_path, "rb") as f:
            cert_b64 = base64.b64encode(f.read()).decode()

        return {
            "request": request_payload,
            "signature": signature_b64,
            "certificate": cert_b64
        }

    except Exception as e:
        raise UserError(f"EIMS Signing Failed: {str(e)}")