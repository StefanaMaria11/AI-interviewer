import pytest

from app.services.admin_password_service import hash_admin_password,verify_admin_password, admin_password_needs_rehash


TEST_PASSWORD = "Correct-Horse-Battery-2026"


def test_hash_admin_password():
    password_hash = hash_admin_password(TEST_PASSWORD)

    assert password_hash.startswith("$argon2id$")
    assert password_hash != TEST_PASSWORD

def test_verify_correct_password():
    password_hash = hash_admin_password(TEST_PASSWORD)

    assert verify_admin_password(
        TEST_PASSWORD,
        password_hash,
    )

def test_reject_incorrect_password():
    password_hash = hash_admin_password(TEST_PASSWORD)

    assert not verify_admin_password(
        "Incorrect-Password-2026",
        password_hash,
    )

def test_reject_invalid_hash():
    assert not verify_admin_password(
        TEST_PASSWORD,
        "invalid-hash",
    )

def test_reject_short_password():
    with pytest.raises(ValueError):
        hash_admin_password("short")

def test_hashes_use_unique_salts():
    first = hash_admin_password(TEST_PASSWORD)
    second = hash_admin_password(TEST_PASSWORD)

    assert first != second

def test_current_hash_does_not_need_rehash():
    password_hash = hash_admin_password(TEST_PASSWORD)

    assert not admin_password_needs_rehash(
        password_hash
    )