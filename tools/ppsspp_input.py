#!/usr/bin/env python3
"""Press PSP buttons through PPSSPP's WebSocket debugger."""

from __future__ import annotations

import argparse
import json

import websocket


BUTTONS = {
    "cross",
    "circle",
    "triangle",
    "square",
    "up",
    "down",
    "left",
    "right",
    "start",
    "select",
    "ltrigger",
    "rtrigger",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("buttons", nargs="+", choices=sorted(BUTTONS))
    parser.add_argument("--duration", type=int, default=2)
    parser.add_argument("--url", default="ws://127.0.0.1:2324/debugger")
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()

    if args.duration < 1:
        parser.error("--duration must be at least 1 frame")

    ws = websocket.create_connection(
        args.url,
        subprotocols=["debugger.ppsspp.org"],
        timeout=args.timeout,
        http_proxy_host=None,
        http_proxy_port=None,
    )
    try:
        for ticket, button in enumerate(args.buttons, start=1):
            ws.send(
                json.dumps(
                    {
                        "event": "input.buttons.press",
                        "ticket": ticket,
                        "button": button,
                        "duration": args.duration,
                    }
                )
            )
            while True:
                response = json.loads(ws.recv())
                if response.get("event") == "error" and response.get("ticket") == ticket:
                    raise RuntimeError(json.dumps(response, ensure_ascii=False))
                if response.get("event") == "input.buttons.press" and response.get("ticket") == ticket:
                    break
        print(json.dumps({"pressed": args.buttons, "duration": args.duration}))
    finally:
        ws.close()


if __name__ == "__main__":
    main()
