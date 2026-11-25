from datetime import datetime, timezone
from getpass import getpass

from sqlalchemy import select, update

from app.database import SessionLocal
from app.models.admin import Admin
from app.models.admin_session import AdminSession
from app.services.admin_password_service import verify_admin_password
from app.services.admin_mfa_service import verify_admin_totp
from app.services.admin_mfa_service import generate_totp_secret
from app.services.admin_mfa_service import encrypt_totp_secret
from app.services.admin_mfa_service import find_valid_totp_step

def main() -> int:
    email = input("Administrator email: ").strip().lower()
    password = getpass("Administrator password: ")
    old_code = getpass("Current authenticator code: ")

    with SessionLocal.begin() as db:
        admin = db.scalar(
            select(Admin)
            .where(Admin.email == email)
            .with_for_update()
        )

        if (
            admin is None
            or not admin.is_active
            or not verify_admin_password(password, admin.password_hash)
            or not verify_admin_totp(admin, old_code)
        ):
            print("Administrator authentication failed.")
            return 1

        admin_id = admin.id
        previous_secret = admin.totp_secret_encrypted

    new_secret = generate_totp_secret()

    print("\nAdd a NEW InterviewHub account to your authenticator.")
    print("Type: Time-based (TOTP)")
    print(f"Setup key: {new_secret}")
    print("\nDo not share this key.")

    new_code = getpass("New authenticator code: ")
    accepted_step = find_valid_totp_step(new_secret, new_code)

    if accepted_step is None:
        print("Invalid code. The old MFA configuration remains active.")
        return 1

    with SessionLocal.begin() as db:
        admin = db.scalar(
            select(Admin)
            .where(Admin.id == admin_id)
            .with_for_update()
        )

        if (
            admin is None
            or not admin.is_active
            or admin.totp_secret_encrypted != previous_secret
        ):
            print("MFA configuration changed. Rotation cancelled.")
            return 1

        now = datetime.now(timezone.utc)

        admin.totp_secret_encrypted = encrypt_totp_secret(new_secret)
        admin.mfa_enabled_at = now
        admin.last_totp_step = accepted_step

        db.execute(
            update(AdminSession)
            .where(AdminSession.admin_id == admin.id)
            .where(AdminSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )

    print("Administrator MFA rotated successfully.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())