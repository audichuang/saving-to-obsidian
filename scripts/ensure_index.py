#!/usr/bin/env python3
"""
ensure_index.py — 確保 Dataview 索引頁面存在

在指定資料夾建立 _index.md，包含 Dataview 查詢表格。

用法:
  doppler run -p finviz -c dev -- python3 ensure_index.py --folder collections
  doppler run -p finviz -c dev -- python3 ensure_index.py --folder finviz-stock --title "Finviz Reports"
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error


DEFAULT_TEMPLATE = """---
title: {title}
type: index
---

# 📚 {title}

```dataview
TABLE date AS "日期", category AS "分類", source AS "來源"
FROM "{folder}"
WHERE type != "index"
SORT date DESC
```
"""


def main():
    parser = argparse.ArgumentParser(description="建立/更新 Dataview 索引頁面")
    parser.add_argument("--folder", "-f", default="collections", help="Vault 內的資料夾 (預設: collections)")
    parser.add_argument("--title", "-t", default=None, help="索引頁標題 (預設: Folder Index)")
    parser.add_argument("--vault", "-v", help="覆寫 Vault 名稱")
    args = parser.parse_args()

    base_url = os.environ.get("FAST_NOTE_URL")
    token = os.environ.get("FAST_NOTE_TOKEN")
    vault = args.vault or os.environ.get("FAST_NOTE_VAULT", "Obsidian")

    if not base_url or not token:
        print("錯誤: 需要設定 FAST_NOTE_URL 和 FAST_NOTE_TOKEN 環境變數", file=sys.stderr)
        sys.exit(1)

    title = args.title or f"{args.folder.replace('-', ' ').title()} Index"
    content = DEFAULT_TEMPLATE.format(title=title, folder=args.folder).strip() + "\n"

    url = f"{base_url.rstrip('/')}/api/note"
    payload = json.dumps({
        "vault": vault,
        "path": f"{args.folder}/_index.md",
        "content": content,
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
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
                "path": f"{args.folder}/_index.md",
            }))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(json.dumps({"success": False, "error": f"HTTP {e.code}: {body}"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
