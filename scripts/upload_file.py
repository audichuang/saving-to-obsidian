#!/usr/bin/env python3
"""
upload_file.py — 透過 WebSocket 上傳附件到 Fast Note Sync Service

環境變數（由 doppler 注入）:
  FAST_NOTE_URL    — 伺服器 URL (e.g. http://192.168.31.105:4000)
  FAST_NOTE_TOKEN  — API Token
  FAST_NOTE_VAULT  — Vault 名稱 (e.g. Obsidian)

用法:
  # 上傳單張圖片（預設以檔名存到 vault 根目錄）
  doppler run -p storage -c dev -- python3 upload_file.py image.png

  # 上傳到指定子目錄
  doppler run -p storage -c dev -- python3 upload_file.py img1.webp img2.webp --prefix assets/xhs

  # 指定 vault
  doppler run -p storage -c dev -- python3 upload_file.py photo.jpg --vault MyVault
"""

import argparse
import ctypes
import json
import os
import struct
import sys
import threading
import time

try:
    import websocket
except ImportError:
    print("請先安裝: pip install websocket-client", file=sys.stderr)
    sys.exit(1)


def java_hash(s: str) -> str:
    """Java-style hashCode，與 Obsidian 插件一致。"""
    h = 0
    for ch in s:
        h = ctypes.c_int32((h << 5) - h + ord(ch)).value
    return str(h)


def hash_file_bytes(file_path: str) -> str:
    """計算檔案位元組的 hashCode。"""
    with open(file_path, "rb") as f:
        data = f.read()
    h = 0
    for b in data:
        h = ctypes.c_int32((h << 5) - h + b).value
    return str(h)


def get_env():
    """讀取並驗證環境變數。"""
    base_url = os.environ.get("FAST_NOTE_URL", "")
    token = os.environ.get("FAST_NOTE_TOKEN", "")
    vault = os.environ.get("FAST_NOTE_VAULT", "Obsidian")

    if not base_url or not token:
        print("錯誤: 需要設定 FAST_NOTE_URL 和 FAST_NOTE_TOKEN", file=sys.stderr)
        sys.exit(1)

    return base_url, token, vault


def build_ws_url(base_url: str) -> str:
    """將 http(s) URL 轉為 ws(s) URL。"""
    ws_url = base_url.rstrip("/")
    ws_url = ws_url.replace("https://", "wss://").replace("http://", "ws://")
    return ws_url + "/api/user/sync"


def upload_one(file_path: str, remote_path: str, vault: str, ws_url: str, token: str) -> dict:
    """透過 WebSocket 上傳單個檔案，回傳結果 dict。"""

    file_size = os.path.getsize(file_path)
    file_mtime = int(os.path.getmtime(file_path) * 1000)
    file_ctime = int(os.path.getctime(file_path) * 1000)
    path_hash = java_hash(remote_path)
    content_hash = hash_file_bytes(file_path)

    state = {"done": False, "error": None, "session_id": None}
    done_event = threading.Event()

    def on_open(ws):
        ws.send(f"Authorization|{token}")

    def on_message(ws, raw):
        idx = raw.find("|")
        if idx == -1:
            return
        action, body = raw[:idx], json.loads(raw[idx + 1:])

        if action == "Authorization":
            if body.get("status"):
                ws.send("ClientInfo|" + json.dumps({
                    "name": "UploadScript", "version": "1.0.0",
                    "type": "desktop", "offlineSyncStrategy": "newTimeMerge",
                }))
            else:
                state["error"] = f"認證失敗: {body.get('message')}"
                done_event.set()
                ws.close()
            return

        if action == "ClientInfo":
            ws.send("FileUploadCheck|" + json.dumps({
                "vault": vault, "path": remote_path,
                "pathHash": path_hash, "contentHash": content_hash,
                "size": file_size, "ctime": file_ctime, "mtime": file_mtime,
            }))
            return

        if action == "FileUpload":
            data = body.get("data", {})
            sid = data.get("sessionId")
            chunk_size = data.get("chunkSize", 524288)
            if not sid:
                state["error"] = f"缺少 sessionId: {body}"
                done_event.set()
                ws.close()
                return

            state["session_id"] = sid
            # Send binary chunks
            with open(file_path, "rb") as f:
                i = 0
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    payload = b"00" + sid.encode("ascii") + struct.pack(">I", i) + chunk
                    ws.send(payload, opcode=websocket.ABNF.OPCODE_BINARY)
                    i += 1
            return

        # Upload complete or no-update
        if body.get("code") in (1, 2) and (state.get("session_id") or body.get("code") == 2):
            state["done"] = True
            done_event.set()
            ws.close()

    def on_error(ws, error):
        state["error"] = str(error)
        done_event.set()

    def on_close(ws, *_):
        done_event.set()

    ws = websocket.WebSocketApp(ws_url, on_open=on_open, on_message=on_message,
                                 on_error=on_error, on_close=on_close)
    t = threading.Thread(target=ws.run_forever, kwargs={"ping_interval": 25})
    t.daemon = True
    t.start()
    done_event.wait(timeout=60)

    if state["error"]:
        return {"file": os.path.basename(file_path), "path": remote_path, "success": False, "error": state["error"]}
    if state["done"]:
        return {"file": os.path.basename(file_path), "path": remote_path, "success": True}
    return {"file": os.path.basename(file_path), "path": remote_path, "success": False, "error": "timeout"}


def main():
    parser = argparse.ArgumentParser(description="上傳附件到 Obsidian via Fast Note Sync WebSocket")
    parser.add_argument("files", nargs="+", help="要上傳的檔案")
    parser.add_argument("--prefix", default="", help="Vault 內的子目錄路徑 (e.g. assets/xhs)")
    parser.add_argument("--vault", "-v", help="覆寫 Vault 名稱")
    args = parser.parse_args()

    base_url, token, vault = get_env()
    if args.vault:
        vault = args.vault
    ws_url = build_ws_url(base_url)

    results = []
    for fp in args.files:
        if not os.path.isfile(fp):
            results.append({"file": fp, "success": False, "error": "file not found"})
            continue

        basename = os.path.basename(fp)
        remote_path = f"{args.prefix.strip('/')}/{basename}" if args.prefix else basename

        result = upload_one(fp, remote_path, vault, ws_url, token)
        status = "✅" if result["success"] else "❌"
        print(f"{status} {result['path']}", file=sys.stderr)
        results.append(result)

    print(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    main()
