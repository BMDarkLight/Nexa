import os
import resend
from dotenv import load_dotenv, find_dotenv

load_dotenv(dotenv_path=find_dotenv())

resend.api_key = os.getenv("RESEND_API_KEY")

def send_email(recipient: str, subject: str, body: str):
    params: resend.Emails.SendParams = {
        "from": "Acme <onboarding@resend.dev>",
        "to": [recipient],
        "subject": subject,
        "html": body,
    }
    
    email = resend.Emails.send(params)

    return email