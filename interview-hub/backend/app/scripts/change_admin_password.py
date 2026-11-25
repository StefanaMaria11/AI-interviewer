from datetime import datetime, timezone
from getpass import getpass

from sqlalchemy import select, update

from app.database import SessionLocal
from app.models.admin import Admin
from app.models.admin_session import AdminSession
from app.services.admin_password_service import hash_admin_password
from app.services.admin_password_service import verify_admin_password
from app.services.admin_mfa_service import verify_admin_totp

def main() -> int:
    email = input("Administrator email: ").strip().lower()
    old_password = getpass("Current password: ")
    code = getpass("Current authenticator code: ")
    new_password = getpass("New password: ")
    confirmation = getpass("Confirm new password: ")

    if new_password != confirmation:
        print("New passwords do not match.")
        return 1

    if new_password == old_password:
        print("New password must differ from the old password.")
        return 1

    try:
        new_hash = hash_admin_password(new_password)
    except ValueError as exc:
        print(exc)
        return 1

    with SessionLocal.begin() as db:
        admin = db.scalar(
            select(Admin)
            .where(Admin.email == email)
            .with_for_update()
        )

        if (
            admin is None
            or not admin.is_active
            or not verify_admin_password(
                old_password,
                admin.password_hash,
            )
            or not verify_admin_totp(admin, code)
        ):
            print("Administrator authentication failed.")
            return 1

        admin.password_hash = new_hash

        db.execute(
            update(AdminSession)
            .where(AdminSession.admin_id == admin.id)
            .where(AdminSession.revoked_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc))
        )

    print("Password changed. Existing sessions revoked.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())