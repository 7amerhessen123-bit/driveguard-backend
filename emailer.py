import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()


def send_reset_email(to: str, link: str):
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_APP_PASSWORD")

    if not user or not password:
        print("RESET LINK (email not configured):", link)
        return

    msg = EmailMessage()
    msg["Subject"] = "Reset your Drive Guard password"
    msg["From"] = user
    msg["To"] = to
    msg.set_content(f"Use this link to set a new password:\n{link}\n\nIt expires in 1 hour.")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(user, password)
        server.send_message(msg)