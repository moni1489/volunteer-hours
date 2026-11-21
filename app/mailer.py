import os
import smtplib
import ssl
from email.message import EmailMessage

from flask import current_app


def send_code_email(to: str, code: str) -> None:
    cfg = current_app.config
    if not cfg["SMTP_HOST"]:
        # Local testing only: print the code instead of emailing it.
        # Requires an explicit DEV_PRINT_CODES=1 so codes never reach logs in production.
        if os.environ.get("DEV_PRINT_CODES") == "1":
            print(f"[DEV] login code for {to}: {code}", flush=True)
            return
        raise RuntimeError("SMTP_HOST is not configured")

    msg = EmailMessage()
    msg["Subject"] = "Код входа на сайт учёта волонтёрских часов"
    msg["From"] = cfg["SMTP_USER"]
    msg["To"] = to
    msg.set_content(
        f"Ваш код для входа: {code}\n\n"
        "Код действует 10 минут. Если вы не запрашивали код, просто проигнорируйте это письмо.\n"
    )

    with smtplib.SMTP(cfg["SMTP_HOST"], cfg["SMTP_PORT"], timeout=15) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        if cfg["SMTP_USER"]:
            smtp.login(cfg["SMTP_USER"], cfg["SMTP_PASSWORD"])
        smtp.send_message(msg)
