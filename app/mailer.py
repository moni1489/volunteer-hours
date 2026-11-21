import json
import os
import smtplib
import ssl
import urllib.request
from email.message import EmailMessage

from flask import current_app

from app.i18n import lookup, session_lang

BREVO_URL = "https://api.brevo.com/v3/smtp/email"


def _message(code: str) -> tuple[str, str]:
    """Subject and body in the language of the current session (Russian when there is none)."""
    lang = session_lang()
    return lookup("mail.subject", lang), lookup("mail.body", lang).format(code=code)


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
    subject, body = _message(code)
    payload = {
        "sender": {"email": sender},
        "to": [{"email": to}],
        "subject": subject,
        "textContent": body,
    }
    req = urllib.request.Request(
        BREVO_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"api-key": api_key, "content-type": "application/json", "accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status not in (200, 201, 202):
                raise RuntimeError(f"Brevo API returned {resp.status}")
    except urllib.error.HTTPError as exc:
        # Include Brevo's own message in the log so the cause is visible on Render.
        detail = exc.read().decode("utf-8", "replace")[:300]
        raise RuntimeError(f"Brevo API error {exc.code}: {detail}") from None


def _send_via_smtp(cfg, to: str, code: str) -> None:
    subject, body = _message(code)
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg["SMTP_USER"]
    msg["To"] = to
    msg.set_content(body)

    with smtplib.SMTP(cfg["SMTP_HOST"], cfg["SMTP_PORT"], timeout=15) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        if cfg["SMTP_USER"]:
            smtp.login(cfg["SMTP_USER"], cfg["SMTP_PASSWORD"])
        smtp.send_message(msg)
