---
name: saving-to-obsidian
description: "Obsidian vault 讀寫原子技能：查詢目錄結構、寫入/更新筆記、上傳附件、修改 frontmatter、建立索引頁。透過 Fast Note Sync API 操作 Obsidian Vault。觸發關鍵字：save to obsidian, upload note, upload file, upload image, 存入Obsidian, 寫入筆記, 上傳筆記, 上傳圖片, 上傳附件, vault 結構, 目錄結構."
---

# Obsidian Vault — 筆記讀寫與附件管理原子技能

透過 Fast Note Sync API 對 Obsidian Vault 進行目錄查詢、筆記讀寫、附件上傳、frontmatter 修改。

> **這是原子技能**：只負責 Obsidian Vault 的讀寫操作，不包含任何內容分析、分類或格式化邏輯。

## 環境設定

> **Doppler 配置**: `doppler run -p storage -c dev --`

| 環境變數 | 說明 |
|----------|------|
| `FAST_NOTE_URL` | Fast Note Sync 伺服器 URL |
| `FAST_NOTE_TOKEN` | API Token |
| `FAST_NOTE_VAULT` | Vault 名稱 |

## 腳本

### list\_vault.py — 查詢 Vault 目錄結構

> **推薦第一步**：寫入筆記或上傳附件前，先查目錄結構了解現有配置，再決定存放路徑。

```bash
# 查看整個 vault 結構
doppler run -p storage -c dev -- python3 ~/skills/saving-to-obsidian/scripts/list_vault.py

# 限制深度（只看第一層）
doppler run -p storage -c dev -- python3 ~/skills/saving-to-obsidian/scripts/list_vault.py --depth 1

# JSON 輸出（方便程式處理）
doppler run -p storage -c dev -- python3 ~/skills/saving-to-obsidian/scripts/list_vault.py --json
```

樹狀輸出範例：

```
Obsidian (2 notes, 7 files)
├── collections/ (15 notes)
│   ├── Article/ (25 notes)
│   ├── Tutorial/ (9 notes)
│   └── ...
├── daily-log/ (3 notes)
├── finviz-stock/ (4 notes)
└── assets/
    └── xiaohongshu/ ...
```

### upload\_file.py — 上傳附件（圖片/檔案）

透過 WebSocket 分塊協議上傳，與 Obsidian 插件使用相同的同步通道。

```bash
# 上傳單張圖片
doppler run -p storage -c dev -- python3 ~/skills/saving-to-obsidian/scripts/upload_file.py image.png

# 上傳多張 + 指定 vault 內子目錄
doppler run -p storage -c dev -- python3 ~/skills/saving-to-obsidian/scripts/upload_file.py \
  img1.webp img2.webp img3.webp --prefix "assets/2026-02-28"

# 指定 vault
doppler run -p storage -c dev -- python3 ~/skills/saving-to-obsidian/scripts/upload_file.py \
  photo.jpg --vault MyVault --prefix assets
```

輸出 JSON（stdout）:

```json
[
  {"file": "img1.webp", "path": "assets/2026-02-28/img1.webp", "success": true},
  {"file": "img2.webp", "path": "assets/2026-02-28/img2.webp", "success": true}
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
  --path "folder/note.md" \
  --updates '{"category": "Tutorial", "tags": "python"}'
```

### ensure\_index.py — 建立 Dataview 索引頁

```bash
# 基本用法（預設欄位：date, title）
doppler run -p storage -c dev -- python3 ~/skills/saving-to-obsidian/scripts/ensure_index.py --folder daily-log

# 自訂標題
doppler run -p storage -c dev -- python3 ~/skills/saving-to-obsidian/scripts/ensure_index.py --folder finviz-stock --title "Finviz Reports"

# 自訂 Dataview 欄位
doppler run -p storage -c dev -- python3 ~/skills/saving-to-obsidian/scripts/ensure_index.py \
  --folder collections --columns "date:日期,category:分類,source:來源"
```

## 依賴

`upload_file.py` 需要 `websocket-client`：

```bash
pip install websocket-client
```
