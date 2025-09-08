import os
import smtplib
import logging
import socket
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv, find_dotenv

# --- Setup ---
load_dotenv(dotenv_path=find_dotenv())
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

use_smtp = os.getenv("USE_SMTP", "false").lower() == "true"

if use_smtp:
    # --- SMTP Configuration ---
    SMTP_SERVER = os.getenv("SMTP_SERVER")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    SMTP_SENDER = os.getenv("SMTP_SENDER")

    if not all([SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_SENDER]):
        raise ConnectionError(
            "SMTP is enabled, but one or more required environment variables are missing: "
            "SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_SENDER"
        )

    def send_email(to_email: str, subject: str, html_body: str):
        try:
            msg = MIMEMultipart()
            msg["From"] = SMTP_SENDER
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(html_body, "html"))

            # --- FIX: Added a timeout to prevent hanging ---
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
                server.starttls()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.sendmail(SMTP_SENDER, to_email, msg.as_string())
                logger.info(f"SMTP email sent to {to_email} successfully!")
        
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP Authentication failed. Please check credentials. Error: {e}")
            raise
        except socket.gaierror as e:
            logger.error(f"SMTP DNS resolution failed. Check the SMTP_SERVER address. Error: {e}")
            raise
        except TimeoutError:
            logger.error("SMTP connection timed out after 10 seconds. Check server and port.")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred while sending SMTP email: {e}")
            raise

else:
    # --- Resend Configuration ---
    import resend

    RESEND_API_KEY = os.getenv("RESEND_API_KEY")
    RESEND_SENDER = os.getenv("RESEND_SENDER", "Nexa <onboarding@resend.dev>")
    
    if not RESEND_API_KEY:
         raise ConnectionError("USE_SMTP is false, but RESEND_API_KEY is not set.")

    resend.api_key = RESEND_API_KEY

    def send_email(to_email: str, subject: str, html_body: str):
        try:
            params: resend.Emails.SendParams = {
                "from": RESEND_SENDER,
                "to": [to_email],
                "subject": subject,
                "html": html_body,
            }
            email = resend.Emails.send(params)
            logger.info(f"Resend email sent to {to_email} successfully! ID: {email.get('id')}")
            return email
        except Exception as e:
            logger.error(f"Failed to send email to {to_email} via Resend: {e}")
            raise
