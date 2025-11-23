"""Agent worker that processes queued envelopes and sends responses."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Optional

from ai_agent_hub import Envelope
from ai_agent_hub.lmtp_handler import QUEUE_DIR

PROCESSED_DIR = Path("./processed")
WORKER_AGENT_ID = "https://agent.local/@worker"


def _find_oldest_queue_file() -> Optional[Path]:
    if not QUEUE_DIR.exists():
        return None

    files = [p for p in QUEUE_DIR.iterdir() if p.is_file()]
    if not files:
        return None

    return sorted(files, key=lambda p: p.stat().st_mtime)[0]


def _load_envelope(file_path: Path) -> Envelope:
    raw = file_path.read_text(encoding="utf-8")
    return Envelope.from_json(raw)


def _extract_intent(env: Envelope) -> Optional[str]:
    payload = env.payload
    if isinstance(payload, dict):
        intent = payload.get("intent")
        if isinstance(intent, str):
            return intent

        meta = payload.get("meta")
        if isinstance(meta, dict):
            meta_intent = meta.get("intent")
            if isinstance(meta_intent, str):
                return meta_intent

    return None


def _summarize_payload(payload: Any) -> str:
    if isinstance(payload, dict):
        text_candidate = payload.get("text")
        if isinstance(text_candidate, str):
            text = text_candidate
        else:
            text = json.dumps(payload, ensure_ascii=False)
    else:
        text = payload if isinstance(payload, str) else str(payload)
    return text[:100]


def _build_reply(env: Envelope, result_payload: Any) -> Envelope:
    return Envelope.new(
        envelope_type="response",
        sender=WORKER_AGENT_ID,
        recipient=env.sender,
        payload=result_payload,
        context=env.context,
        in_reply_to=env.id,
    )


def _handle_envelope(env: Envelope) -> Optional[Envelope]:
    intent = _extract_intent(env)
    if not intent:
        print("No intent found; skipping envelope", env.id)
        return None

    if intent == "ping":
        reply_payload: Any = "pong"
    elif intent == "echo":
        reply_payload = env.payload
    elif intent == "summary":
        reply_payload = _summarize_payload(env.payload)
    else:
        print(f"Unsupported intent '{intent}'; skipping envelope {env.id}")
        return None

    return _build_reply(env, reply_payload)


def send_envelope_via_smtp(env: Envelope) -> None:
    """Placeholder SMTP sender to be implemented later."""

    print("Sending envelope via SMTP:")
    print(env.to_json(indent=2))


def process_next_envelope() -> bool:
    """Process the oldest envelope in the queue if present."""

    file_path = _find_oldest_queue_file()
    if not file_path:
        return False

    env = _load_envelope(file_path)
    reply = _handle_envelope(env)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    destination = PROCESSED_DIR / file_path.name
    file_path.rename(destination)

    if reply:
        send_envelope_via_smtp(reply)
    return True


def main(poll_interval: float = 1.0) -> None:
    """Continuously watch the queue directory and process envelopes."""

    while True:
        processed = process_next_envelope()
        if not processed:
            time.sleep(poll_interval)


if __name__ == "__main__":
    main()
