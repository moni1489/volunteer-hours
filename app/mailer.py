import json
import os
import smtplib
import ssl
import urllib.request
from email.message import EmailMessage

from flask import current_app

SUBJECT = "Код входа на сайт учёта волонтёрских часов"
BODY = (
    "Ваш код для входа: {code}\n\n"
    "Код действует 10 минут. Если вы не запрашивали код, просто проигнорируйте это письмо.\n"
)
BREVO_URL = "https://api.brevo.com/v3/smtp/email"


def send_code_email(to: str, code: str) -> None:
    cfg = current_app.config
    api_key = os.environ.get("BREVO_API_KEY", "")
    if api_key:
        _send_via_brevo(api_key, to, code)
        return
    if not cfg["SMTP_HOST"]:
        # Local testing only: print the code instead of emailing it.
        # Requires an explicit DEV_PRINT_CODES=1 so codes never reach logs in production.
        if os.environ.get("DEV_PRINT_CODES") == "1":
            print(f"[DEV] login code for {to}: {code}", flush=True)
            return
        raise RuntimeError("Neither BREVO_API_KEY nor SMTP_HOST is configured")
    _send_via_smtp(cfg, to, code)


def _send_via_brevo(api_key: str, to: str, code: str) -> None:
    sender = os.environ.get("BREVO_SENDER") or "volunteer.ukk2026@gmail.com"
    payload = {
        "sender": {"email": sender},
        "to": [{"email": to}],
        "subject": SUBJECT,
        "textContent": BODY.format(code=code),
    }
    req = urllib.request.Request(
        BREVO_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"api-key": api_key, "content-type": "application/json", "accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        if resp.status not in (200, 201, 202):
            raise RuntimeError(f"Brevo API returned {resp.status}")


def _send_via_smtp(cfg, to: str, code: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = SUBJECT
    msg["From"] = cfg["SMTP_USER"]
    msg["To"] = to
    msg.set_content(BODY.format(code=code))

    with smtplib.SMTP(cfg["SMTP_HOST"], cfg["SMTP_PORT"], timeout=15) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        if cfg["SMTP_USER"]:
            smtp.login(cfg["SMTP_USER"], cfg["SMTP_PASSWORD"])
        smtp.send_message(msg)
