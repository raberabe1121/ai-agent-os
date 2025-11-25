"""Asyncio-based LMTP server for AI Agent Hub."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from email import message_from_bytes
from typing import Awaitable, Callable

from ai_agent_hub import Envelope
from ai_agent_hub.lmtp_handler import extract_body, extract_recipient, extract_sender, save_envelope

ResponseWriter = Callable[[str], Awaitable[None]]


class LMTPServer:
    """Minimal LMTP server using asyncio streams.

    The server accepts a single message at a time and converts it into an
    Envelope saved to the queue directory. Designed for compatibility with
    Postfix using ``lmtp:inet:localhost:8024``.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8024) -> None:
        self.host = host
        self.port = port
        self._server: asyncio.AbstractServer | None = None

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle_client, self.host, self.port)
        addr = ", ".join(str(sock.getsockname()) for sock in self._server.sockets or [])
        print(f"AI Agent Hub asyncio LMTP server listening on {addr}")

    async def serve_forever(self) -> None:
        if self._server is None:
            await self.start()
        assert self._server is not None
        async with self._server:
            await self._server.serve_forever()

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        async def write_response(line: str) -> None:
            writer.write((line + "\r\n").encode())
            await writer.drain()

        await write_response("220 AI-Agent-Hub LMTP server ready")

        mail_from: str | None = None
        recipients: list[str] = []
        in_data_mode = False
        data_lines: list[bytes] = []

        while not reader.at_eof():
            raw_line = await reader.readline()
            if raw_line == b"":
                break
            if in_data_mode:
                if raw_line in {b".\r\n", b".\n", b"."}:
                    await self._process_message(data_lines, mail_from, recipients, write_response)
                    in_data_mode = False
                    data_lines = []
                    mail_from = None
                    recipients = []
                    continue
                if raw_line.startswith(b".."):
                    raw_line = raw_line[1:]
                data_lines.append(raw_line)
                continue

            line = raw_line.decode(errors="replace").strip()
            upper = line.upper()

            if upper.startswith("LHLO"):
                await write_response("250 OK")
            elif upper.startswith("MAIL FROM:"):
                mail_from = line[10:].strip()
                await write_response("250 OK")
            elif upper.startswith("RCPT TO:"):
                recipients.append(line[8:].strip())
                await write_response("250 OK")
            elif upper == "DATA":
                in_data_mode = True
                data_lines = []
                await write_response("354 Start mail input; end with <CRLF>.<CRLF>")
            elif upper == "QUIT":
                await write_response("221 Bye")
                break
            else:
                await write_response("500 Unknown command")

        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass

    async def _process_message(
        self,
        data_lines: list[bytes],
        mail_from: str | None,
        recipients: list[str],
        write_response: ResponseWriter,
    ) -> None:
        message_id = str(uuid.uuid4())
        raw_bytes = b"".join(data_lines)
        try:
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
            await write_response(f"250 OK queued as {message_id}")
        except Exception as exc:  # pragma: no cover - error path
            await write_response("451 Requested action aborted: processing error")
            print(f"Failed to process message: {exc}")


def main() -> None:
    server = LMTPServer()
    asyncio.run(server.serve_forever())


if __name__ == "__main__":
    main()
