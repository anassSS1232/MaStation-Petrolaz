# ==================================================
# FICHIER : .\security.py
# ==================================================

import os
import json
import time
import hmac
import hashlib
import base64

SECRET_KEY = os.getenv("PETROLAZ_SECRET_KEY", "station_petrolaz_secret_key_secure_2026").encode("utf-8")
SESSION_DURATION_SECONDS = 86400 * 7  # 7 jours

def signer_session(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = int(time.time()) + SESSION_DURATION_SECONDS
    json_bytes = json.dumps(payload).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(json_bytes).decode("utf-8")
    signature = hmac.new(SECRET_KEY, payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{signature}"

def verifier_session(cookie_str: str) -> dict | None:
    if not cookie_str or "." not in cookie_str:
        return None
    try:
        payload_b64, signature = cookie_str.rsplit(".", 1)
        expected_sig = hmac.new(SECRET_KEY, payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return None
        json_bytes = base64.urlsafe_b64decode(payload_b64.encode("utf-8"))
        data = json.loads(json_bytes.decode("utf-8"))
        if data.get("exp", 0) < int(time.time()):
            return None
        return data
    except Exception:
        return None