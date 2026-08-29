"""
Generates a mindset recommendation via the Claude API and delivers it via
Email and WhatsApp (Twilio). Run by GitHub Actions on a cron schedule —
one invocation per alarm slot. Logs every send to log.json in the repo.

Required environment variables (set as GitHub Actions secrets):
  ANTHROPIC_API_KEY
  EMAIL_HOST            e.g. smtp.gmail.com
  EMAIL_PORT            e.g. 587
  EMAIL_USER            sender address
  EMAIL_PASS            app password (not your real password)
  EMAIL_TO              your email address
  TWILIO_ACCOUNT_SID
  TWILIO_AUTH_TOKEN
  TWILIO_WHATSAPP_FROM  e.g. "whatsapp:+14155238886" (Twilio sandbox number)
  WHATSAPP_TO           e.g. "whatsapp:+919820626387"
  SLOT_ID               which slot (1-5) this run corresponds to — passed
                         in per-cron-trigger from the workflow file
"""

import json
import os
import smtplib
import sys
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"
LOG_PATH = ROOT / "log.json"

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
ANTHROPIC_MODEL = "claude-sonnet-4-6"


def load_json(path, default):
    if path.exists():
        return json.loads(path.read_text())
    return default


def get_slot(config, slot_id):
    for slot in config["slots"]:
        if str(slot["id"]) == str(slot_id):
            return slot
    raise ValueError(f"No slot with id {slot_id} in config.json")


def recent_messages(log, limit=15):
    return [entry["content"] for entry in log[-limit:]]


def generate_message(config, avoid):
    avoid_block = ""
    if avoid:
        bullet_list = "\n".join(f"- {m}" for m in avoid)
        avoid_block = f"\n\nAVOID REPEATING any of these:\n{bullet_list}"

    payload = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": 200,
        "system": config["system_prompt"],
        "messages": [
            {
                "role": "user",
                "content": f"Context: {config['context']}{avoid_block}\n\nWrite today's message.",
            }
        ],
    }
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return "".join(block["text"] for block in data["content"] if block["type"] == "text").strip()


def send_email(message, slot_label):
    host = os.environ["EMAIL_HOST"]
    port = int(os.environ["EMAIL_PORT"])
    user = os.environ["EMAIL_USER"]
    password = os.environ["EMAIL_PASS"]
    to_addr = os.environ["EMAIL_TO"]

    msg = MIMEText(message)
    msg["Subject"] = f"[Mindset — {slot_label}]"
    msg["From"] = user
    msg["To"] = to_addr

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.sendmail(user, [to_addr], msg.as_string())


def send_whatsapp(message):
    account_sid = os.environ["TWILIO_ACCOUNT_SID"]
    auth_token = os.environ["TWILIO_AUTH_TOKEN"]
    from_number = os.environ["TWILIO_WHATSAPP_FROM"]
    to_number = os.environ["WHATSAPP_TO"]

    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    resp = requests.post(
        url,
        auth=(account_sid, auth_token),
        data={"From": from_number, "To": to_number, "Body": message},
        timeout=30,
    )
    resp.raise_for_status()


def main():
    slot_id = os.environ.get("SLOT_ID") or (sys.argv[1] if len(sys.argv) > 1 else None)
    if not slot_id:
        raise SystemExit("SLOT_ID env var or CLI arg required")

    config = load_json(CONFIG_PATH, {})
    log = load_json(LOG_PATH, [])

    slot = get_slot(config, slot_id)
    message = generate_message(config, recent_messages(log))

    errors = []
    try:
        send_email(message, slot["label"])
    except Exception as e:
        errors.append(f"email: {e}")

    try:
        send_whatsapp(message)
    except Exception as e:
        errors.append(f"whatsapp: {e}")

    log.append(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "slot_id": slot["id"],
            "slot_label": slot["label"],
            "content": message,
            "errors": errors,
        }
    )
    LOG_PATH.write_text(json.dumps(log, indent=2))

    if errors:
        print("Completed with errors:", errors)
    else:
        print(f"Sent slot {slot['id']} ({slot['label']}): {message}")


if __name__ == "__main__":
    main()
