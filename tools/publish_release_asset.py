#!/usr/bin/env python3
"""Publish a release asset with the GitHub REST API.

`gh` is not installed in this project, but git already stores a credential for
github.com, so the release can be updated without the web UI.  The token is read
at run time and never written to disk.

Examples
--------
    # replace the asset on an existing release and refresh its notes
    python tools/publish_release_asset.py \
        --repo ssjwoo/gundam-next-plus-kr-patch --tag dev-2026-09-26 \
        --asset build/next_plus_development_v19_2026-09-26.xdelta \
        --body docs/RELEASE_2026-09-26.md \
        --name "개발 릴리스 2026-09-26 - 자유 폰트·숫자 테이블 수정 (v19)"

    # also drop a superseded asset from the same release
    python tools/publish_release_asset.py ... --replace next_plus_development_v11_2026-09-26.xdelta
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.github.com"


def credential() -> str:
    out = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        capture_output=True, text=True, check=True,
    ).stdout
    for line in out.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1]
    raise SystemExit("git has no stored credential for github.com")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", required=True, help="owner/name")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--asset", type=Path, required=True)
    parser.add_argument("--body", type=Path, help="release notes; skip to leave them alone")
    parser.add_argument("--name", help="release title")
    parser.add_argument("--replace", action="append", default=[],
                        help="asset name on the same release to delete (repeatable)")
    args = parser.parse_args()

    headers = {"Authorization": f"Bearer {credential()}",
               "Accept": "application/vnd.github+json", "User-Agent": "hanpatch-release"}

    def api(method: str, url: str, payload=None, raw: bytes | None = None,
            ctype: str = "application/json"):
        data = raw if raw is not None else (json.dumps(payload).encode() if payload is not None else None)
        request = urllib.request.Request(url, data=data, method=method,
                                         headers={**headers, "Content-Type": ctype})
        try:
            with urllib.request.urlopen(request, timeout=600) as response:
                text = response.read()
                return response.status, (json.loads(text) if text else {})
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read() or b"{}")

    status, release = api("GET", f"{API}/repos/{args.repo}/releases/tags/{args.tag}")
    if status != 200:
        raise SystemExit(f"{args.tag}: {status} {release.get('message')}")
    release_id = release["id"]

    changes = {}
    if args.name:
        changes["name"] = args.name
    if args.body:
        changes["body"] = args.body.read_text(encoding="utf-8")
    if changes:
        status, _ = api("PATCH", f"{API}/repos/{args.repo}/releases/{release_id}", changes)
        if status != 200:
            raise SystemExit(f"release update failed: {status}")
        print(f"release {args.tag}: updated {sorted(changes)}")

    for asset in release["assets"]:
        if asset["name"] == args.asset.name:
            api("DELETE", f"{API}/repos/{args.repo}/releases/assets/{asset['id']}")
            print(f"  replaced existing {args.asset.name}")

    data = args.asset.read_bytes()
    upload = release["upload_url"].split("{")[0]
    status, out = api("POST", f"{upload}?name={args.asset.name}", raw=data,
                      ctype="application/octet-stream")
    if status not in (200, 201):
        raise SystemExit(f"upload failed: {status} {out.get('message')}")
    print(f"  uploaded {args.asset.name} ({out.get('size')} bytes, state={out.get('state')})")

    for asset in release["assets"]:
        if asset["name"] in args.replace:
            code, _ = api("DELETE", f"{API}/repos/{args.repo}/releases/assets/{asset['id']}")
            print(f"  deleted superseded {asset['name']} ({code})")

    status, release = api("GET", f"{API}/repos/{args.repo}/releases/{release_id}")
    print(f"release {args.tag} now holds: "
          + ", ".join(f"{a['name']} ({a['size']} bytes)" for a in release["assets"]))
    print(release["html_url"])


if __name__ == "__main__":
    sys.exit(main())
