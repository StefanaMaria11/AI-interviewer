from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pyotp
import pytest
from cryptography.fernet import Fernet

from app.services.admin_mfa_service import generate_totp_secret
from app.services.admin_mfa_service import encrypt_totp_secret
from app.services.admin_mfa_service import decrypt_totp_secret
from app.services.admin_mfa_service import find_valid_totp_step
from app.services.admin_mfa_service import verify_admin_totp

TEST_TIME = datetime(
    2026, 11, 25, 18, 0, 15,
    tzinfo=timezone.utc,
)

@pytest.fixture(autouse=True)
def configure_mfa_key(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("ADMIN_MFA_ENCRYPTION_KEY", key)

def make_admin(secret, enabled=True, active=True):
    return SimpleNamespace(
        is_active=active,
        mfa_enabled_at=TEST_TIME if enabled else None,
        totp_secret_encrypted=encrypt_totp_secret(secret),
        last_totp_step=None,
    )

def test_generate_totp_secret():
    first = generate_totp_secret()
    second = generate_totp_secret()

    assert first != second
    assert len(first) >= 32

def test_encrypt_and_decrypt_secret():
    secret = generate_totp_secret()
    encrypted = encrypt_totp_secret(secret)

    assert encrypted != secret
    assert decrypt_totp_secret(encrypted) == secret

def test_accept_valid_totp_code():
    secret = generate_totp_secret()
    code = pyotp.TOTP(secret).at(TEST_TIME)

    step = find_valid_totp_step(
        secret,
        code,
        now=TEST_TIME,
    )

    assert step == int(TEST_TIME.timestamp()) // 30

def test_accept_previous_time_step():
    secret = generate_totp_secret()
    previous = TEST_TIME - timedelta(seconds=30)
    code = pyotp.TOTP(secret).at(previous)

    assert find_valid_totp_step(
        secret,
        code,
        now=TEST_TIME,
    ) is not None

def test_reject_future_time_step():
    secret = generate_totp_secret()
    future = TEST_TIME + timedelta(seconds=30)
    code = pyotp.TOTP(secret).at(future)

    assert find_valid_totp_step(
        secret,
        code,
        now=TEST_TIME,
    ) is None

def test_reject_invalid_code():
    secret = generate_totp_secret()

    assert find_valid_totp_step(
        secret,
        "abc123",
        now=TEST_TIME,
    ) is None

def test_reject_reused_code():
    secret = generate_totp_secret()
    code = pyotp.TOTP(secret).at(TEST_TIME)
    last_step = int(TEST_TIME.timestamp()) // 30

    assert find_valid_totp_step(
        secret,
        code,
        last_used_step=last_step,
        now=TEST_TIME,
    ) is None

def test_verify_admin_totp():
    secret = generate_totp_secret()
    admin = make_admin(secret)
    code = pyotp.TOTP(secret).at(TEST_TIME)

    assert verify_admin_totp(
        admin,
        code,
        now=TEST_TIME,
    )

    assert admin.last_totp_step is not None

    assert not verify_admin_totp(
        admin,
        code,
        now=TEST_TIME,
    )

def test_reject_admin_without_mfa():
    secret = generate_totp_secret()
    admin = make_admin(secret, enabled=False)
    code = pyotp.TOTP(secret).at(TEST_TIME)

    assert not verify_admin_totp(
        admin,
        code,
        now=TEST_TIME,
    )

def test_reject_inactive_admin():
    secret = generate_totp_secret()
    admin = make_admin(secret, active=False)
    code = pyotp.TOTP(secret).at(TEST_TIME)

    assert not verify_admin_totp(
        admin,
        code,
        now=TEST_TIME,
    )