***

name: saving-to-obsidian
description: "Save or update markdown notes to Obsidian vault via Fast Note Sync API. Use when any skill or workflow needs to write content to Obsidian. Trigger keywords: save to obsidian, upload note, 存入Obsidian, 寫入筆記, 上傳筆記."
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# Saving to Obsidian — 筆記寫入原子技能

透過 Fast Note Sync API 對 Obsidian Vault 進行筆記的新增、更新、frontmatter 修改。

> **這是原子技能**：只負責「寫入 Obsidian」這個動作，不包含任何內容分析或格式化邏輯。

## 環境設定

> **Doppler 配置**: `doppler run -p finviz -c dev --`

| 環境變數 | 說明 |
|----------|------|
| `FAST_NOTE_URL` | Fast Note Sync 伺服器 URL |
| `FAST_NOTE_TOKEN` | API Token |
| `FAST_NOTE_VAULT` | Vault 名稱 |

## 腳本

### save\_note.py — 新增/更新筆記

```bash
# 上傳檔案
doppler run -p finviz -c dev -- python3 ~/skills/saving-to-obsidian/scripts/save_note.py report.md --path "folder/report.md"

# 從 stdin
echo "# content" | doppler run -p finviz -c dev -- python3 ~/skills/saving-to-obsidian/scripts/save_note.py --stdin --path "folder/note.md"

# 直接傳入內容
doppler run -p finviz -c dev -- python3 ~/skills/saving-to-obsidian/scripts/save_note.py --content "# Hello" --path "folder/note.md"
```

輸出 JSON: `{"success": true, "note_path": "...", "version": "...", "id": "..."}`

### update\_frontmatter.py — 修改 YAML frontmatter

```bash
doppler run -p finviz -c dev -- python3 ~/skills/saving-to-obsidian/scripts/update_frontmatter.py \
  --path "collections/2026-02-18-標題.md" \
  --updates '{"category": "Tutorial", "tags": "python"}'
```

### ensure\_index.py — 建立 Dataview 索引頁

```bash
doppler run -p finviz -c dev -- python3 ~/skills/saving-to-obsidian/scripts/ensure_index.py --folder collections
doppler run -p finviz -c dev -- python3 ~/skills/saving-to-obsidian/scripts/ensure_index.py --folder finviz-stock --title "Finviz Reports"
```
