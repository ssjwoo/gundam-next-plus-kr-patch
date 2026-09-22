#!/usr/bin/env python3
"""Send one request to PPSSPP's WebSocket debugger and print its response."""

from __future__ import annotations

import argparse
import base64
import json

import websocket


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("event")
    parser.add_argument("--params-json", default="{}")
    parser.add_argument("--url", default="ws://127.0.0.1:2324/debugger")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--decode-base64", action="store_true")
    args = parser.parse_args()

    params = json.loads(args.params_json)
    if not isinstance(params, dict):
        parser.error("--params-json must decode to an object")
    request = {"event": args.event, "ticket": 1, **params}

    ws = websocket.create_connection(
        args.url,
        subprotocols=["debugger.ppsspp.org"],
        timeout=args.timeout,
        http_proxy_host=None,
        http_proxy_port=None,
    )
    try:
        ws.send(json.dumps(request))
        while True:
            response = json.loads(ws.recv())
            if response.get("ticket") != 1:
                continue
            if response.get("event") == "error":
                raise RuntimeError(json.dumps(response, ensure_ascii=False))
            if args.decode_base64 and "base64" in response:
                raw = base64.b64decode(response["base64"])
                response["decoded_hex"] = raw.hex(" ")
            print(json.dumps(response, ensure_ascii=True, indent=2))
            return
    finally:
        ws.close()


if __name__ == "__main__":
    main()
