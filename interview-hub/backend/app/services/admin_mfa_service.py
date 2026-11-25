import os
import re
import secrets
from datetime import datetime, timezone

import pyotp
from cryptography.fernet import Fernet

from app.models.admin import Admin

TOTP_INTERVAL_SECONDS = 30

def get_mfa_cipher() -> Fernet:
    key = os.getenv("ADMIN_MFA_ENCRYPTION_KEY")

    if not key:
        raise RuntimeError(
            "ADMIN_MFA_ENCRYPTION_KEY is not configured"
        )

    return Fernet(key.encode("utf-8"))

def generate_totp_secret() -> str:
    return pyotp.random_base32()

def encrypt_totp_secret(secret: str) -> str:
    encrypted = get_mfa_cipher().encrypt(
        secret.encode("utf-8")
    )
    return encrypted.decode("utf-8")

def decrypt_totp_secret(encrypted_secret: str) -> str:
    decrypted = get_mfa_cipher().decrypt(
        encrypted_secret.encode("utf-8")
    )
    return decrypted.decode("utf-8")

def find_valid_totp_step(
    secret: str,
    code: str,
    last_used_step: int | None = None,
    now: datetime | None = None,
) -> int | None:
    if not isinstance(code, str):
        return None

    if re.fullmatch(r"[0-9]{6}", code) is None:
        return None

    current_time = now or datetime.now(timezone.utc)
    current_step = (
        int(current_time.timestamp())
        // TOTP_INTERVAL_SECONDS
    )

    totp = pyotp.TOTP(
        secret,
        interval=TOTP_INTERVAL_SECONDS,
    )

    # Accept the current or immediately previous time step.
    for step in [current_step, current_step - 1]:
        if last_used_step is not None and step <= last_used_step:
            continue

        expected_code = totp.at(
            step * TOTP_INTERVAL_SECONDS
        )

        if secrets.compare_digest(expected_code, code):
            return step

    return None

def verify_admin_totp(
    admin: Admin,
    code: str,
    now: datetime | None = None,
) -> bool:
    if not admin.is_active:
        return False

    if (
        admin.mfa_enabled_at is None
        or admin.totp_secret_encrypted is None
    ):
        return False

    secret = decrypt_totp_secret(
        admin.totp_secret_encrypted
    )

    accepted_step = find_valid_totp_step(
        secret,
        code,
        last_used_step=admin.last_totp_step,
        now=now,
    )

    if accepted_step is None:
        return False

    admin.last_totp_step = accepted_step

    # The caller must commit this update atomically.
    return True