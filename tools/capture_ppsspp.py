#!/usr/bin/env python3
"""Capture PPSSPP's current framebuffer through its WebSocket debugger."""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
import time

import websocket


def receive_until(ws: websocket.WebSocket, predicate, timeout: float) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        ws.settimeout(max(0.1, deadline - time.monotonic()))
        message = json.loads(ws.recv())
        if message.get("event") == "error":
            raise RuntimeError(json.dumps(message, ensure_ascii=False))
        if predicate(message):
            return message
    raise TimeoutError("Timed out waiting for PPSSPP debugger response")


def send(ws: websocket.WebSocket, event: str, ticket: int, **params: object) -> None:
    ws.send(json.dumps({"event": event, "ticket": ticket, **params}))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--url", default="ws://127.0.0.1:2324/debugger")
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()

    ws = websocket.create_connection(
        args.url,
        subprotocols=["debugger.ppsspp.org"],
        timeout=args.timeout,
        http_proxy_host=None,
        http_proxy_port=None,
    )
    paused = False
    try:
        send(ws, "version", 1, name="gundam-kr-patch-capture", version="1.0")
        version = receive_until(ws, lambda msg: msg.get("ticket") == 1, args.timeout)

        # GPU buffer reads require PPSSPP to be in stepping state.
        send(ws, "cpu.stepping", 2)
        receive_until(ws, lambda msg: msg.get("event") == "cpu.stepping", args.timeout)
        paused = True

        shot = None
        errors = []
        for ticket, event in ((3, "gpu.buffer.screenshot"), (4, "gpu.buffer.renderColor")):
            ws.send(json.dumps({"event": event, "ticket": ticket, "type": "uri"}))
            try:
                shot = receive_until(
                    ws,
                    lambda msg, ticket=ticket: msg.get("ticket") == ticket,
                    args.timeout,
                )
                break
            except RuntimeError as exc:
                errors.append(str(exc))
        if shot is None:
            raise RuntimeError("; ".join(errors))
        uri = shot["uri"]
        prefix = "data:image/png;base64,"
        if not uri.startswith(prefix):
            raise RuntimeError("PPSSPP returned an unexpected screenshot URI")

        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(base64.b64decode(uri[len(prefix) :]))
        print(
            json.dumps(
                {
                    "output": str(args.output.resolve()),
                    "width": shot.get("width"),
                    "height": shot.get("height"),
                    "pid": version.get("pid"),
                    "path": version.get("path"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        if paused:
            ws.send(json.dumps({"event": "cpu.resume"}))
        ws.close()


if __name__ == "__main__":
    main()
