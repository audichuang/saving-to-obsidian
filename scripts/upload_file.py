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
import urllib.request
import urllib.error

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


def verify_file_via_rest(base_url: str, token: str, vault: str, remote_path: str, expected_hash: str) -> bool:
    """透過 REST API 驗證檔案是否已成功上傳到伺服器。"""
    url = f"{base_url.rstrip('/')}/api/file/info?vault={urllib.request.quote(vault)}&path={urllib.request.quote(remote_path)}"
    req = urllib.request.Request(url, headers={"token": token})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read())
            if body.get("code") == 1 and body.get("data"):
                server_hash = body["data"].get("contentHash", "")
                return server_hash == expected_hash
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
        pass
    return False


def upload_one(file_path: str, remote_path: str, vault: str, ws_url: str, base_url: str, token: str) -> dict:
    """透過 WebSocket 上傳單個檔案，回傳結果 dict。

    策略：送完所有 binary chunks 後，透過 REST API 驗證上傳結果。
    不依賴伺服器的 WebSocket 完成回應（因 is-return-sussess=false 時不會發送）。
    """

    file_size = os.path.getsize(file_path)
    file_mtime = int(os.path.getmtime(file_path) * 1000)
    file_ctime = int(os.path.getctime(file_path) * 1000)
    path_hash = java_hash(remote_path)
    content_hash = hash_file_bytes(file_path)

    # 狀態：chunks_sent 表示所有分塊已發送完畢（但伺服器可能還在處理）
    state = {"done": False, "error": None, "chunks_sent": False, "no_update": False}
    done_event = threading.Event()

    def on_open(ws):
        ws.send(f"Authorization|{token}")

    def on_message(ws, raw):
        idx = raw.find("|")
        if idx == -1:
            # 無 action prefix 的回應（可能是 is-return-sussess=true 時的 Success 回應）
            try:
                body = json.loads(raw)
                if body.get("code") in (1, 6) and state.get("chunks_sent"):
                    state["done"] = True
                    done_event.set()
                    ws.close()
            except json.JSONDecodeError:
                pass
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
            # code == 6 (SuccessNoUpdate) 表示伺服器已有相同內容
            if body.get("code") == 6:
                state["done"] = True
                state["no_update"] = True
                done_event.set()
                ws.close()
                return

            sid = data.get("sessionId")
            chunk_size = data.get("chunkSize", 524288)
            if not sid:
                state["error"] = f"缺少 sessionId: {body}"
                done_event.set()
                ws.close()
                return

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

            # 所有 chunks 已發送
            state["chunks_sent"] = True

            # 等一下伺服器處理，然後主動關閉連線
            # 伺服器可能不會回傳 Success（is-return-sussess=false），所以不依賴回應
            time.sleep(2)
            done_event.set()
            ws.close()
            return

        # 兜底：任何帶 action 且 code=1 的回應（is-return-sussess=true 時可能出現）
        if body.get("code") == 1 and state.get("chunks_sent"):
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

    # 確保 WebSocket 連線完全關閉
    ws.close()
    t.join(timeout=5)

    basename = os.path.basename(file_path)

    if state["error"]:
        return {"file": basename, "path": remote_path, "success": False, "error": state["error"]}

    # 如果伺服器回應了完成（is-return-sussess=true）或無需更新
    if state["done"] and (state["no_update"] or not state["chunks_sent"]):
        return {"file": basename, "path": remote_path, "success": True}

    # 送完 chunks 後，用 REST API 驗證檔案是否已到伺服器
    if state["chunks_sent"]:
        # 最多重試 3 次，每次間隔 2 秒（給伺服器時間處理）
        for attempt in range(3):
            if verify_file_via_rest(base_url, token, vault, remote_path, content_hash):
                return {"file": basename, "path": remote_path, "success": True}
            time.sleep(2)
        return {"file": basename, "path": remote_path, "success": False, "error": "chunks sent but verify failed"}

    return {"file": basename, "path": remote_path, "success": False, "error": "timeout"}


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

        result = upload_one(fp, remote_path, vault, ws_url, base_url, token)
        status = "✅" if result["success"] else "❌"
        print(f"{status} {result['path']}", file=sys.stderr)
        results.append(result)

    print(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    main()
