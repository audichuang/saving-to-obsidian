#!/usr/bin/env python3
"""
list_vault.py — 查詢 Obsidian Vault 目錄結構 (Fast Note Sync API)

環境變數（由 doppler 注入）:
  FAST_NOTE_URL    — 伺服器 URL
  FAST_NOTE_TOKEN  — API Token
  FAST_NOTE_VAULT  — Vault 名稱

用法:
  # 查看整個 vault 結構（人類可讀樹狀輸出）
  doppler run -p storage -c dev -- python3 list_vault.py

  # 限制深度
  doppler run -p storage -c dev -- python3 list_vault.py --depth 2

  # JSON 輸出（方便程式處理）
  doppler run -p storage -c dev -- python3 list_vault.py --json

  # 指定 vault
  doppler run -p storage -c dev -- python3 list_vault.py --vault MyVault
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error


def get_env():
    """讀取並驗證環境變數。"""
    base_url = os.environ.get("FAST_NOTE_URL", "")
    token = os.environ.get("FAST_NOTE_TOKEN", "")
    vault = os.environ.get("FAST_NOTE_VAULT", "Obsidian")

    if not base_url or not token:
        print("錯誤: 需要設定 FAST_NOTE_URL 和 FAST_NOTE_TOKEN", file=sys.stderr)
        print("請確認已用 doppler: doppler run -p storage -c dev -- ...", file=sys.stderr)
        sys.exit(1)

    return base_url, token, vault


def fetch_tree(base_url: str, token: str, vault: str, depth: int | None = None) -> dict:
    """呼叫 GET /api/folder/tree 取得目錄樹。"""
    params = f"vault={urllib.request.quote(vault)}"
    if depth is not None:
        params += f"&depth={depth}"

    url = f"{base_url.rstrip('/')}/api/folder/tree?{params}"
    req = urllib.request.Request(url, headers={"token": token})

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            if body.get("code") == 1 and body.get("data"):
                return body["data"]
            print(f"API 錯誤: {body.get('message', 'unknown')}", file=sys.stderr)
            sys.exit(1)
    except urllib.error.HTTPError as e:
        print(f"HTTP 錯誤 {e.code}: {e.read().decode('utf-8', errors='replace')}", file=sys.stderr)
        sys.exit(1)


def count_label(note_count: int, file_count: int) -> str:
    """產生計數標籤。"""
    parts = []
    if note_count:
        parts.append(f"{note_count} note{'s' if note_count > 1 else ''}")
    if file_count:
        parts.append(f"{file_count} file{'s' if file_count > 1 else ''}")
    return f" ({', '.join(parts)})" if parts else ""


def print_tree(nodes: list[dict], prefix: str = "", is_last_list: list[bool] | None = None):
    """遞迴印出樹狀結構。"""
    if is_last_list is None:
        is_last_list = []

    for i, node in enumerate(nodes):
        is_last = (i == len(nodes) - 1)
        connector = "└── " if is_last else "├── "

        name = node.get("name", "?")
        note_count = node.get("noteCount", 0)
        file_count = node.get("fileCount", 0)
        children = node.get("children", [])
        has_children = bool(children)

        label = count_label(note_count, file_count)
        suffix = "/" if has_children else ""

        print(f"{prefix}{connector}{name}{suffix}{label}")

        if has_children:
            child_prefix = prefix + ("    " if is_last else "│   ")
            print_tree(children, child_prefix, is_last_list + [is_last])


def main():
    parser = argparse.ArgumentParser(description="查詢 Obsidian Vault 目錄結構")
    parser.add_argument("--depth", "-d", type=int, default=None, help="目錄樹深度限制")
    parser.add_argument("--json", "-j", action="store_true", help="輸出 JSON 格式")
    parser.add_argument("--vault", "-v", help="覆寫 Vault 名稱")
    args = parser.parse_args()

    base_url, token, vault = get_env()
    if args.vault:
        vault = args.vault

    data = fetch_tree(base_url, token, vault, args.depth)

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    # 人類可讀的樹狀輸出
    root_notes = data.get("rootNoteCount", 0)
    root_files = data.get("rootFileCount", 0)
    root_label = count_label(root_notes, root_files)
    print(f"{vault}{root_label}")

    folders = data.get("folders", [])
    if folders:
        print_tree(folders)
    else:
        print("  (empty vault)")


if __name__ == "__main__":
    main()
