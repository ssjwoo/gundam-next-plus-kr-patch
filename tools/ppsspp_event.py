#!/usr/bin/env python3
"""Send one JSON event to a running PPSSPP WebSocket debugger."""

from __future__ import annotations

import argparse
import json
import time

import websocket


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("event")
    parser.add_argument("--url", default="ws://127.0.0.1:2324/debugger")
    parser.add_argument("--wait", type=float, default=0.0)
    args = parser.parse_args()

    ws = websocket.create_connection(
        args.url,
        subprotocols=["debugger.ppsspp.org"],
        timeout=10.0,
        http_proxy_host=None,
        http_proxy_port=None,
    )
    try:
        ws.send(json.dumps({"event": args.event}))
        if args.wait:
            time.sleep(args.wait)
    finally:
        ws.close()


if __name__ == "__main__":
    main()
