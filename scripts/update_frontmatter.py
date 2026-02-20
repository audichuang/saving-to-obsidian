#!/usr/bin/env python3
"""
update_frontmatter.py — 更新 Obsidian 筆記的 YAML frontmatter

透過 PATCH /api/note/frontmatter 直接修改 frontmatter 欄位，
不需要重新上傳整篇內容。

用法:
  doppler run -p storage -c dev -- python3 update_frontmatter.py \
    --path "collections/2026-02-18-標題.md" \
    --updates '{"category": "Tutorial", "tags": "python"}'
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error


def main():
    parser = argparse.ArgumentParser(description="更新筆記 frontmatter")
    parser.add_argument("--path", "-p", required=True, help="Vault 內的筆記路徑")
    parser.add_argument("--updates", "-u", required=True, help="要更新的欄位 (JSON 格式)")
    parser.add_argument("--vault", "-v", help="覆寫 Vault 名稱")
    args = parser.parse_args()

    base_url = os.environ.get("FAST_NOTE_URL")
    token = os.environ.get("FAST_NOTE_TOKEN")
    vault = args.vault or os.environ.get("FAST_NOTE_VAULT", "Obsidian")

    if not base_url or not token:
        print("錯誤: 需要設定 FAST_NOTE_URL 和 FAST_NOTE_TOKEN 環境變數", file=sys.stderr)
        sys.exit(1)

    try:
        updates = json.loads(args.updates)
    except json.JSONDecodeError as e:
        print(f"錯誤: --updates 必須是合法 JSON: {e}", file=sys.stderr)
        sys.exit(1)

    url = f"{base_url.rstrip('/')}/api/note/frontmatter"
    payload = json.dumps({
        "vault": vault,
        "path": args.path,
        "updates": updates,
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        method="PATCH",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )

    try:
        with urllib.request.urlopen(req) as resp:
            json.loads(resp.read().decode("utf-8"))
            print(json.dumps({
                "success": True,
                "path": args.path,
                "updates": updates,
            }))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(json.dumps({"success": False, "error": f"HTTP {e.code}: {body}"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
