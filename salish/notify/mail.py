"""Email delivery for surf alerts.

Credentials come from EMAIL_USER and EMAIL_PASS, read from .env locally and
from repository secrets in CI. Recipients are set in config/pipeline.yaml.

Set SALISH_NO_EMAIL=1 to run the full pipeline (fetch, model, plot, report)
without delivering alerts - used for local test runs and CI dry runs.
"""

import os
import smtplib

from dotenv import load_dotenv

load_dotenv()

sender_email = os.getenv("EMAIL_USER")
password = os.getenv("EMAIL_PASS")

EMAIL_ENABLED = os.getenv("SALISH_NO_EMAIL", "").lower() not in ("1", "true", "yes")


def deliver(message, label, recipients):
    """Send one alert, unless email delivery is suppressed."""
    if not EMAIL_ENABLED:
        print(f"[SALISH_NO_EMAIL] {label} alert suppressed (would have sent):\n"
              f"{message.get_payload()[0].get_payload(decode=True).decode()}")
        return
    if not sender_email or not password:
        print(f"[warning] EMAIL_USER/EMAIL_PASS unset - {label} alert not sent")
        return
    message["From"] = sender_email
    message["To"] = ", ".join(recipients)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, password)
        server.send_message(message)
    print(f"{label} alert sent successfully!")
