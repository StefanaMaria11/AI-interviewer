from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
)


_password_hasher = PasswordHasher()

MIN_ADMIN_PASSWORD_LENGTH = 15


def hash_admin_password(password: str) -> str:
    if len(password) < MIN_ADMIN_PASSWORD_LENGTH:
        raise ValueError(
            "Administrator passwords must contain "
            "at least 15 characters"
        )

    return _password_hasher.hash(password)

def verify_admin_password(
    password: str,
    stored_hash: str,
) -> bool:
    try:
        return _password_hasher.verify(
            stored_hash,
            password,
        )
    except (VerificationError, InvalidHashError):
        return False

def admin_password_needs_rehash(
    stored_hash: str,
) -> bool:
    return _password_hasher.check_needs_rehash(
        stored_hash
    )