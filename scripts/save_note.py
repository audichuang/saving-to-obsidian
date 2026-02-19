#!/usr/bin/env python3
"""
save_note.py — 通用 Obsidian 筆記寫入工具 (Fast Note Sync API)

環境變數（由 doppler 注入）:
  FAST_NOTE_URL    — 伺服器 URL (e.g. https://note.example.com)
  FAST_NOTE_TOKEN  — API Token
  FAST_NOTE_VAULT  — Vault 名稱 (e.g. Obsidian)

用法:
  # 上傳檔案
  doppler run -p finviz -c dev -- python3 save_note.py report.md

  # 指定 Vault 內路徑
  doppler run -p finviz -c dev -- python3 save_note.py report.md --path "folder/report.md"

  # 從 stdin 讀取
  echo "# content" | doppler run -p finviz -c dev -- python3 save_note.py --stdin --path "folder/note.md"

  # 直接傳入內容字串
  doppler run -p finviz -c dev -- python3 save_note.py --content "# Hello" --path "folder/note.md"
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error


def api_request(method: str, endpoint: str, data: dict, base_url: str, token: str) -> dict:
    """呼叫 Fast Note Sync REST API"""
    url = f"{base_url.rstrip('/')}/api{endpoint}"
    payload = json.dumps(data).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        method=method,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )

    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(json.dumps({"success": False, "error": f"HTTP {e.code}: {body}"}))
        sys.exit(1)


def get_env():
    """讀取並驗證環境變數"""
    base_url = os.environ.get("FAST_NOTE_URL")
    token = os.environ.get("FAST_NOTE_TOKEN")
    vault = os.environ.get("FAST_NOTE_VAULT", "Obsidian")

    if not base_url or not token:
        print("錯誤: 需要設定 FAST_NOTE_URL 和 FAST_NOTE_TOKEN 環境變數", file=sys.stderr)
        print("請確認已用 doppler: doppler run -p finviz -c dev -- ...", file=sys.stderr)
        sys.exit(1)

    return base_url, token, vault


def main():
    parser = argparse.ArgumentParser(description="上傳/更新筆記到 Obsidian via Fast Note Sync")
    parser.add_argument("file", nargs="?", help="要上傳的 markdown 檔案")
    parser.add_argument("--stdin", action="store_true", help="從 stdin 讀取內容")
    parser.add_argument("--content", help="直接傳入內容字串")
    parser.add_argument("--path", "-p", help="Vault 內的筆記路徑 (必須指定，除非上傳檔案)")
    parser.add_argument("--vault", "-v", help="覆寫 Vault 名稱 (預設用環境變數)")
    args = parser.parse_args()

    base_url, token, vault = get_env()
    if args.vault:
        vault = args.vault

    # 決定內容來源（優先順序：--stdin > --content > file）
    if args.stdin:
        content = sys.stdin.read()
        if not args.path:
            print("錯誤: 使用 --stdin 時必須指定 --path", file=sys.stderr)
            sys.exit(1)
        note_path = args.path
    elif args.content:
        content = args.content
        if not args.path:
            print("錯誤: 使用 --content 時必須指定 --path", file=sys.stderr)
            sys.exit(1)
        note_path = args.path
    elif args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            content = f.read()
        note_path = args.path or os.path.basename(args.file)
    else:
        parser.print_help()
        sys.exit(1)

    result = api_request("POST", "/note", {
        "vault": vault,
        "path": note_path,
        "content": content,
    }, base_url, token)

    data = result.get("data", {})
    print(json.dumps({
        "success": True,
        "note_path": note_path,
        "version": data.get("version", "?"),
        "id": data.get("id", "?"),
    }))


if __name__ == "__main__":
    main()
