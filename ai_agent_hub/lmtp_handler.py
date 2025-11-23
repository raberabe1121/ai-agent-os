import os
import re
import time
from datetime import datetime, timezone
from email import message_from_bytes

from aiosmtpd.controller import Controller

from ai_agent_hub import Envelope

QUEUE_DIR = "./queue"


class LMTPHandler:
    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        """Accept all recipients for MVP."""
        return "250 OK"

    async def handle_DATA(self, server, session, envelope_data):
        raw_bytes = envelope_data.original_content
        msg = message_from_bytes(raw_bytes)

        sender = extract_sender(msg)
        recipient = extract_recipient(msg)
        payload = extract_body(msg)

        env = Envelope.new(
            envelope_type="email",
            sender=sender,
            recipient=recipient,
            payload=payload,
            created_at=datetime.now(timezone.utc),
        )

        save_envelope(env)
        return "250 Message accepted for delivery"


def extract_sender(msg):
    header = msg.get("From")
    match = re.search(r"https?://[^> ]+", header or "")
    return match.group(0) if match else "https://unknown/@unknown"


def extract_recipient(msg):
    header = msg.get("To")
    match = re.search(r"https?://[^> ]+", header or "")
    return match.group(0) if match else "https://unknown/@unknown"


def extract_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return part.get_payload(decode=True).decode(errors="replace")
        return ""
    payload = msg.get_payload(decode=True)
    return payload.decode(errors="replace") if isinstance(payload, (bytes, bytearray)) else str(payload)


def save_envelope(env: Envelope):
    os.makedirs(QUEUE_DIR, exist_ok=True)
    fname = f"{env.created_at.timestamp()}-{env.id}.json"
    fpath = os.path.join(QUEUE_DIR, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(env.to_json(indent=2))
    print(f"Saved envelope → {fpath}")


def main():
    controller = Controller(
        LMTPHandler(),
        hostname="127.0.0.1",
        port=8024,
        decode_data=False,
        enable_SMTPUTF8=True,
        require_starttls=False,
    )
    controller.start()
    print("AI Agent Hub LMTP Handler running at lmtp://127.0.0.1:8024")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        controller.stop()


if __name__ == "__main__":
    main()
