#!/usr/bin/env python3
"""
ensure_index.py — 確保 Dataview 索引頁面存在

在指定資料夾建立 _index.md，包含 Dataview 查詢表格。

用法:
  # 基本用法（預設欄位：date, title）
  doppler run -p storage -c dev -- python3 ensure_index.py --folder daily-log

  # 自訂標題
  doppler run -p storage -c dev -- python3 ensure_index.py --folder finviz-stock --title "Finviz Reports"

  # 自訂 Dataview 欄位（逗號分隔，格式：field 或 field:顯示名）
  doppler run -p storage -c dev -- python3 ensure_index.py --folder collections --columns "date:日期,category:分類,source:來源"
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error


def build_dataview_table(columns: str, folder: str) -> str:
    """解析 columns 字串，產生 Dataview TABLE 語句。"""
    parts = []
    for col in columns.split(","):
        col = col.strip()
        if ":" in col:
            field, alias = col.split(":", 1)
            parts.append(f'{field.strip()} AS "{alias.strip()}"')
        else:
            parts.append(col)
    cols_str = ", ".join(parts)
    return f'TABLE {cols_str}\nFROM "{folder}"\nWHERE type != "index"\nSORT date DESC'


TEMPLATE = """---
title: {title}
type: index
---

# 📚 {title}

```dataview
{dataview_query}
```
"""


def main():
    parser = argparse.ArgumentParser(description="建立/更新 Dataview 索引頁面")
    parser.add_argument("--folder", "-f", required=True, help="Vault 內的資料夾")
    parser.add_argument("--title", "-t", default=None, help="索引頁標題 (預設: 資料夾名稱 + Index)")
    parser.add_argument("--columns", "-c", default="date:日期,title:標題",
                        help="Dataview 欄位 (逗號分隔，格式：field 或 field:顯示名)")
    parser.add_argument("--vault", "-v", help="覆寫 Vault 名稱")
    args = parser.parse_args()

    base_url = os.environ.get("FAST_NOTE_URL")
    token = os.environ.get("FAST_NOTE_TOKEN")
    vault = args.vault or os.environ.get("FAST_NOTE_VAULT", "Obsidian")

    if not base_url or not token:
        print("錯誤: 需要設定 FAST_NOTE_URL 和 FAST_NOTE_TOKEN 環境變數", file=sys.stderr)
        sys.exit(1)

    title = args.title or f"{args.folder.replace('-', ' ').title()} Index"
    dataview_query = build_dataview_table(args.columns, args.folder)
    content = TEMPLATE.format(title=title, dataview_query=dataview_query).strip() + "\n"

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
