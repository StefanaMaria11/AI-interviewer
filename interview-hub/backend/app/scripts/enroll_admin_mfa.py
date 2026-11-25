from datetime import datetime, timezone
from getpass import getpass

from email_validator import EmailNotValidError
from email_validator import validate_email
from sqlalchemy import select

from app.database import SessionLocal
from app.models.admin import Admin
from app.services.admin_password_service import verify_admin_password
from app.services.admin_mfa_service import generate_totp_secret
from app.services.admin_mfa_service import encrypt_totp_secret
from app.services.admin_mfa_service import find_valid_totp_step

def main() -> int:
    raw_email = input("Administrator email: ").strip()

    try:
        email = validate_email(
            raw_email,
            check_deliverability=False,
        ).normalized.lower()
    except EmailNotValidError:
        print("Invalid email address.")
        return 1

    password = getpass("Administrator password: ")

    with SessionLocal() as db:
        admin = db.scalar(
            select(Admin).where(Admin.email == email)
        )

        if (
            admin is None
            or not admin.is_active
            or not verify_admin_password(
                password,
                admin.password_hash,
            )
        ):
            print("Invalid credentials or inactive account.")
            return 1

        if (
            admin.mfa_enabled_at is not None
            or admin.totp_secret_encrypted is not None
        ):
            print("MFA is already configured.")
            return 1

    secret = generate_totp_secret()

    print("\nAdd an account to your authenticator app.")
    print("Account type: Time-based (TOTP)")
    print("Issuer: InterviewHub")
    print(f"Account email: {email}")
    print(f"Setup key: {secret}")
    print("\nKeep this setup key private.")

    code = getpass("\nEnter the current 6-digit code: ")

    with SessionLocal() as db:
        admin = db.scalar(
            select(Admin)
            .where(Admin.email == email)
            .with_for_update()
        )

        if (
            admin is None
            or not admin.is_active
            or admin.mfa_enabled_at is not None
            or admin.totp_secret_encrypted is not None
        ):
            print("Administrator is not eligible for enrollment.")
            return 1

        accepted_step = find_valid_totp_step(
            secret,
            code,
        )

        if accepted_step is None:
            print("Invalid authenticator code. MFA was not enabled.")
            return 1

        admin.totp_secret_encrypted = encrypt_totp_secret(
            secret
        )
        admin.mfa_enabled_at = datetime.now(timezone.utc)
        admin.last_totp_step = accepted_step

        db.commit()

    print("Administrator MFA enabled successfully.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())