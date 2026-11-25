from unittest.mock import patch

from app.services.email_service import send_verification_email, send_login_email


def test_send_verification_email():
    with patch(
        "app.services.email_service.smtplib.SMTP"
    ) as smtp_mock:
        send_verification_email(
            "elena.popescu@example.com",
            "test-verification-token"
        )

    smtp = smtp_mock.return_value.__enter__.return_value
    smtp.send_message.assert_called_once()

    message = smtp.send_message.call_args.args[0]

    assert message["To"] == "elena.popescu@example.com"
    assert message["Subject"] == (
        "Verify your InterviewHub email"
    )
    assert "test-verification-token" in message.get_content()

def test_send_login_email():
    with patch(
        "app.services.email_service.smtplib.SMTP"
    ) as smtp_mock:
        send_login_email(
            "elena.popescu@example.com",
            "test-login-token",
        )

    smtp = smtp_mock.return_value.__enter__.return_value
    smtp.send_message.assert_called_once()

    message = smtp.send_message.call_args.args[0]

    assert message["To"] == "elena.popescu@example.com"
    assert message["Subject"] == "Sign in to InterviewHub"
    assert "test-login-token" in message.get_content()