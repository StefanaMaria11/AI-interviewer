from getpass import getpass

from email_validator import EmailNotValidError, validate_email
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models.admin import Admin
from app.services.admin_password_service import hash_admin_password


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
    confirmation = getpass("Confirm password: ")

    if password != confirmation:
        print("Passwords do not match.")
        return 1

    try:
        password_hash = hash_admin_password(password)
    except ValueError as exc:
        print(exc)
        return 1

    with SessionLocal() as db:
        existing_admin = db.scalar(
            select(Admin.id).where(
                Admin.email == email
            )
        )

        if existing_admin is not None:
            print("Administrator already exists.")
            return 1

        admin = Admin(
            email=email,
            password_hash=password_hash,
            is_active=True,
        )

        db.add(admin)

        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            print("Administrator already exists.")
            return 1

    print("Administrator created successfully.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
