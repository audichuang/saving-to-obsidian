---
name: saving-to-obsidian
description: "Save/update markdown notes and upload attachments (images, files) to Obsidian vault via Fast Note Sync API. Use when any skill or workflow needs to write content or upload files to Obsidian. Trigger keywords: save to obsidian, upload note, upload file, upload image, 存入Obsidian, 寫入筆記, 上傳筆記, 上傳圖片, 上傳附件."
---

# Saving to Obsidian — 筆記寫入與附件上傳原子技能

透過 Fast Note Sync API 對 Obsidian Vault 進行筆記新增/更新、附件上傳、frontmatter 修改。

> **這是原子技能**：只負責「寫入 Obsidian」和「上傳附件」，不包含任何內容分析或格式化邏輯。

## 環境設定

> **Doppler 配置**: `doppler run -p storage -c dev --`

| 環境變數 | 說明 |
|----------|------|
| `FAST_NOTE_URL` | Fast Note Sync 伺服器 URL |
| `FAST_NOTE_TOKEN` | API Token |
| `FAST_NOTE_VAULT` | Vault 名稱 |

## 腳本

### upload\_file.py — 上傳附件（圖片/檔案）

透過 WebSocket 分塊協議上傳，與 Obsidian 插件使用相同的同步通道。

```bash
# 上傳單張圖片
doppler run -p storage -c dev -- python3 ~/skills/saving-to-obsidian/scripts/upload_file.py image.png

# 上傳多張 + 指定 vault 內子目錄
doppler run -p storage -c dev -- python3 ~/skills/saving-to-obsidian/scripts/upload_file.py \
  img1.webp img2.webp img3.webp --prefix "assets/xiaohongshu/2026-02-28"

# 指定 vault
doppler run -p storage -c dev -- python3 ~/skills/saving-to-obsidian/scripts/upload_file.py \
  photo.jpg --vault MyVault --prefix assets
```

輸出 JSON（stdout）:

```json
[
  {"file": "img1.webp", "path": "assets/xiaohongshu/2026-02-28/img1.webp", "success": true},
  {"file": "img2.webp", "path": "assets/xiaohongshu/2026-02-28/img2.webp", "success": true}
]
```

> 進度訊息輸出到 stderr，JSON 結果輸出到 stdout，方便管道處理。

上傳後的檔案可在 Obsidian 中用 `![[path]]` 語法引用。

### save\_note.py — 新增/更新筆記

```bash
# 上傳檔案
doppler run -p storage -c dev -- python3 ~/skills/saving-to-obsidian/scripts/save_note.py report.md --path "folder/report.md"

# 從 stdin
echo "# content" | doppler run -p storage -c dev -- python3 ~/skills/saving-to-obsidian/scripts/save_note.py --stdin --path "folder/note.md"

# 直接傳入內容
doppler run -p storage -c dev -- python3 ~/skills/saving-to-obsidian/scripts/save_note.py --content "# Hello" --path "folder/note.md"
```

輸出 JSON: `{"success": true, "note_path": "...", "version": "...", "id": "..."}`

### update\_frontmatter.py — 修改 YAML frontmatter

```bash
doppler run -p storage -c dev -- python3 ~/skills/saving-to-obsidian/scripts/update_frontmatter.py \
  --path "collections/2026-02-18-標題.md" \
  --updates '{"category": "Tutorial", "tags": "python"}'
```

### ensure\_index.py — 建立 Dataview 索引頁

```bash
doppler run -p storage -c dev -- python3 ~/skills/saving-to-obsidian/scripts/ensure_index.py --folder collections
doppler run -p storage -c dev -- python3 ~/skills/saving-to-obsidian/scripts/ensure_index.py --folder finviz-stock --title "Finviz Reports"
```

## 依賴

`upload_file.py` 需要 `websocket-client`：

```bash
pip install websocket-client
```
