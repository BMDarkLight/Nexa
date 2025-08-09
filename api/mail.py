import os
import resend
from dotenv import load_dotenv, find_dotenv

load_dotenv(dotenv_path=find_dotenv())

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