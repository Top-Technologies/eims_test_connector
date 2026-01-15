import base64
from .crypto_utils import sign_eims_request


def build_eims_request(payload: dict, cert_path: str, private_key_path: str) -> dict:
    """
    Builds final MoR compliant request
    """

    signature = sign_eims_request(payload, private_key_path)

    with open(cert_path, "rb") as cert_file:
        certificate_base64 = base64.b64encode(cert_file.read()).decode("utf-8")

    return {
        "request": payload,
        "signature": signature,
        "certificate": certificate_base64
    }