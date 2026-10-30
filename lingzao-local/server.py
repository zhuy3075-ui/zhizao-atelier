"""织造本地后端 HTTP 服务（标准库，无依赖）。

    python server.py --port 8787

然后让织造 CLI 指向它：

    set LINGZAO_BASE_URL=http://127.0.0.1:8787
    set LINGZAO_API_KEY=lgz_local
    lingzao doctor

实现你自己的采集逻辑：继承 backend.Backend，参考 backend.py 顶部说明。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from backend import MOCK_PNG, Backend, load_backend

# 客户端命令名（连字符） -> Backend 方法名（下划线）
ROUTES: Dict[str, str] = {
    "search-notes": "search_notes",
    "search-users": "search_users",
    "get-user-info": "user_info",
    "get-user-posted-notes": "user_posted_notes",
    "analyze-user-profile": "analyze_user_profile",
    "get-note-detail": "note_detail",
    "get-note-comments": "note_comments",
    "get-article-detail": "article_detail",
    "get-article-stats": "article_stats",
    "get-related-articles": "related_articles",
    "extract-video-copy": "extract_video_copy",
    "generate-image": "generate_image",
}

BACKEND: Backend = None  # type: ignore[assignment]


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "lingzao-local/1.0"

    # ---- 基础工具 ----

    def _send(self, status: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _fail(self, status: int, code: str, message: str) -> None:
        self._send(status, {"ok": False, "error": {"code": code, "message": message}})

    def _read_body(self) -> tuple[Optional[Dict[str, Any]], bool]:
        """返回 (json_body, 是否 multipart)。multipart 只做识别，不解析文件。"""
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        ctype = (self.headers.get("Content-Type") or "").lower()
        if "multipart/form-data" in ctype:
            return None, True
        if not raw:
            return {}, False
        try:
            parsed = json.loads(raw.decode("utf-8"))
            return (parsed if isinstance(parsed, dict) else {}), False
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {}, False

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
        sys.stderr.write("[lingzao-local] " + (fmt % args) + "\n")

    # ---- 路由 ----

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path.rstrip("/")
        started = time.time()
        try:
            if path == "/api/v1/me":
                self._send(200, {"ok": True, "data": None, **BACKEND.me()})
                return
            # 生图批次轮询：本地实现通常同步完成，这里直接复用最近一次结果
            if "/generate-image/batches/" in path:
                payload = BACKEND.generate_image({})
                self._send(200, {"ok": True, "data": payload})
                return
            if path in ("/healthz", ""):
                self._send(200, {"ok": True, "data": {"status": "up"}})
                return
            if path == "/mock.png":
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(MOCK_PNG)))
                self.end_headers()
                self.wfile.write(MOCK_PNG)
                return
            self._fail(404, "NOT_FOUND", f"unknown path: {path}")
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            self._fail(500, "LOCAL_BACKEND_ERROR", str(exc))
        finally:
            sys.stderr.write(f"[lingzao-local] GET {path} {(time.time() - started) * 1000:.0f}ms\n")

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path.rstrip("/")
        started = time.time()
        try:
            if not path.startswith("/api/v1/research/"):
                self._fail(404, "NOT_FOUND", f"unknown path: {path}")
                return
            command = path.rsplit("/", 1)[-1]
            method_name = ROUTES.get(command)
            if not method_name:
                self._fail(404, "NOT_FOUND", f"unknown command: {command}")
                return

            body, is_multipart = self._read_body()
            req = body or {}
            # 让后端能拼出可访问的绝对 URL（mock 生图用）
            req.setdefault("_base_url", f"http://{self.headers.get('Host') or '127.0.0.1:8787'}")
            method = getattr(BACKEND, method_name)
            data = method(req, True) if method_name == "generate_image" and is_multipart else method(req)
            self._send(200, {"ok": True, "data": data})
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            self._fail(500, "LOCAL_BACKEND_ERROR", str(exc))
        finally:
            sys.stderr.write(f"[lingzao-local] POST {path} {(time.time() - started) * 1000:.0f}ms\n")


def main() -> int:
    global BACKEND
    parser = argparse.ArgumentParser(description="Zhizao local backend server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()

    BACKEND = load_backend()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"lingzao-local listening on http://{args.host}:{args.port}  backend={type(BACKEND).__name__}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
