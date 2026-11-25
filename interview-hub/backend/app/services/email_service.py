
import os
import smtplib

from email.message import EmailMessage


def send_verification_email(recipient_email: str, token: str) -> None:
    message = EmailMessage()

    message["Subject"] = "Verify your InterviewHub email"
    message["From"] = os.getenv(
        "MAIL_FROM",
        "no-reply@interviewhub.local"
    )
    message["To"] = recipient_email

    message.set_content(
        f"""Welcome to InterviewHub!

Please verify your email address.

Verification token:
{token}

This token expires in 30 minutes and can only be used once.

During local development, open:
http://localhost:8001/docs

Use POST /auth/verify-email with your token.

If you did not register, you can ignore this email.
"""
    )

    smtp_host = os.getenv("SMTP_HOST", "127.0.0.1")
    smtp_port = int(os.getenv("SMTP_PORT", "1025"))

    with smtplib.SMTP(
        smtp_host,
        smtp_port,
        timeout=10
    ) as smtp:
        smtp.send_message(message)

def send_login_email(
    recipient_email: str,
    token: str,
) -> None:
    message = EmailMessage()

    message["Subject"] = "Sign in to InterviewHub"
    message["From"] = os.getenv(
        "MAIL_FROM",
        "no-reply@interviewhub.local",
    )
    message["To"] = recipient_email

    message.set_content(
        f"""Hello!

You requested to sign in to InterviewHub.

Your login token:
{token}

This token expires in 15 minutes and can only be used once.

During local development, open:
http://localhost:8001/docs

Use POST /auth/complete-login with your token.

If you did not request this login, ignore this email.
"""
    )

    smtp_host = os.getenv("SMTP_HOST", "127.0.0.1")
    smtp_port = int(os.getenv("SMTP_PORT", "1025"))

    with smtplib.SMTP(
        smtp_host,
        smtp_port,
        timeout=10,
    ) as smtp:
        smtp.send_message(message)