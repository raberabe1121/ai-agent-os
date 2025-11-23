"""LMTP handler that converts incoming email into envelopes."""

import os
import re
import time
from datetime import datetime, timezone
from email import message_from_bytes
from pathlib import Path

from ai_agent_hub import Envelope

try:  # pragma: no cover - import guard only
    from aiosmtpd.controller import Controller
    from aiosmtpd.smtp import LMTP

    HAS_AIOSMTPD = True
except Exception:  # pragma: no cover - exercised when dependency missing
    Controller = None  # type: ignore[assignment]
    LMTP = None  # type: ignore[assignment]
    HAS_AIOSMTPD = False

QUEUE_DIR = Path(os.environ.get("AI_AGENT_HUB_QUEUE_DIR", "./queue"))


_AGENT_ID_PATTERN = re.compile(r"(https?://[a-zA-Z0-9.\-]+/@[a-zA-Z0-9_.\-]+)")


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
    return _extract_agent_id(msg.get("From"))


def extract_recipient(msg):
    return _extract_agent_id(msg.get("To"))


def _extract_agent_id(raw_header: str | None) -> str:
    """Extract an ActivityPub-style agent ID from an email header."""

    if not raw_header:
        return "https://unknown/@unknown"

    sanitized = re.sub(r"[<>]", " ", raw_header)
    sanitized = re.sub(
        r"https?\s*:\s*//",
        lambda m: m.group(0).replace(" ", ""),
        sanitized,
    )
    match = _AGENT_ID_PATTERN.search(sanitized)
    if match:
        return match.group(1)

    return "https://unknown/@unknown"


def extract_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return part.get_payload(decode=True).decode(errors="replace")
        return ""
    payload = msg.get_payload(decode=True)
    return payload.decode(errors="replace") if isinstance(payload, (bytes, bytearray)) else str(payload)


def save_envelope(env: Envelope):
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = (
        env.created_at.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    )
    fname = f"{timestamp}_{env.id}.json"
    fpath = QUEUE_DIR / fname
    with fpath.open("w", encoding="utf-8") as f:
        f.write(env.to_json(indent=2))
    print(f"Saved envelope → {fpath}")


def _require_aiosmtpd() -> None:
    if not HAS_AIOSMTPD:
        raise RuntimeError(
            "aiosmtpd is required to run the LMTP server. Install with 'pip install aiosmtpd'."
        )


def main():
    _require_aiosmtpd()

    controller = Controller(
        LMTPHandler(),
        hostname="127.0.0.1",
        port=8024,
        decode_data=False,
        enable_SMTPUTF8=True,
        require_starttls=False,
        server_class=LMTP,
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