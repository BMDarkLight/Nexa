import os
from dotenv import load_dotenv, find_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ssl import create_default_context

load_dotenv(dotenv_path=find_dotenv())

use_smtp = os.getenv("USE_SMTP", "false").lower() == "true"

if use_smtp:
    import smtplib
    from email.mime.text import MIMEText

    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.example.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "admin")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "password")

def send_email(to_address, subject, body):
     try:
        # Enforce TLS
        context = create_default_context()

        # Connect to the server
        with smtplib.SMTP_SSL(
            os.getenv("MAIL_HOST"), os.getenv("MAIL_PORT"), context=context
        ) as server:
            server.login(os.getenv("MAIL_USER"), os.getenv("MAIL_PASSWORD"))

            # Prepare the email
            msg = MIMEMultipart()
            msg["From"] = f"<{os.getenv("MAIL_FROM_ADDRESS")}>"
            msg["To"] = to_address
            msg["Subject"] = subject
            # msg.add_header('x-liara-tag', 'test-tag')  # Add custom header
            msg.attach(MIMEText(body, "html"))

            # Send the email
            server.sendmail(os.getenv("MAIL_FROM_ADDRESS"), to_address, msg.as_string())
            print(f"Email sent to {to_address} successfully!")
     except Exception as e:
        print(f"Failed to send email: {e}")