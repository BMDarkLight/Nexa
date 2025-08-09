import os
import resend
from dotenv import load_dotenv, find_dotenv

load_dotenv(dotenv_path=find_dotenv())

use_smtp = os.getenv("USE_SMTP", "false").lower() == "true"

if use_smtp:
    import smtplib
    from email.mime.text import MIMEText

    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.example.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "admin")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "password")

    def send_email(recipient: str, subject: str, body: str):
        msg = MIMEText(body, "html")
        msg["Subject"] = subject
        msg["From"] = os.getenv("SMTP_SENDER_EMAIL", "organizational@example.com")
        msg["To"] = recipient

        try:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.sendmail(msg["From"], [recipient], msg.as_string())
        except Exception as e:
            print(f"Failed to send email to {recipient}: {e}")
            raise
else:
    resend.api_key = os.getenv("RESEND_API_KEY")

    def send_email(recipient: str, subject: str, body: str):
        params = {
            "from": os.getenv("RESEND_SENDER_EMAIL", "Organizational AI <organizational@example.com>"),
            "to": [recipient],
            "subject": subject,
            "html": body,
        }
        try:
            email = resend.Emails.send(params)
            return email
        except Exception as e:
            print(f"Failed to send email to {recipient}: {e}")
            raise