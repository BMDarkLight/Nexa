import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv, find_dotenv

import os

load_dotenv(dotenv_path=find_dotenv())

def send_email(recipient: str, subject: str, body: str):
    msg = MIMEText(body, 'html')
    msg['Subject'] = subject
    msg['From'] = os.getenv("MAIL_FROM")
    msg['To'] = recipient

    with smtplib.SMTP(os.getenv("MAIL_SERVER"), int(os.getenv("MAIL_PORT", 587))) as server:
        server.starttls()
        server.login(os.getenv("MAIL_USERNAME"), os.getenv("MAIL_PASSWORD"))
        server.send_message(msg)