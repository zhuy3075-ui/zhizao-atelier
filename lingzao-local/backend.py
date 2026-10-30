"""织造本地后端：用你自己的采集能力，替换织造平台。

用法
----
1. 继承 ``Backend``，实现你要用的方法（未实现的方法会返回空数据，不会崩）。
2. 用环境变量告诉服务端加载你的实现：

       set LINGZAO_LOCAL_BACKEND=my_backend:MyBackend

3. 启动服务：

       python server.py --port 8787

4. 让织造 CLI 指向它（不修改 ~/.lingzao/config.json）：

       set LINGZAO_BASE_URL=http://127.0.0.1:8787
       set LINGZAO_API_KEY=lgz_local

默认 ``MockBackend`` 返回形状正确的假数据，用于先跑通链路。

方法签名里的 ``req`` 是客户端原始请求体（dict），字段见 contract.md。
返回值是响应里的 ``data`` 部分；外层 ``{"ok": true, "data": ...}`` 由 server.py 包。
"""

from __future__ import annotations

import base64
import hashlib
import os
from typing import Any, Dict

# 1x1 透明 PNG，供 mock 生图链路验证下载
MOCK_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
MOCK_PNG_SHA256 = hashlib.sha256(MOCK_PNG).hexdigest()


class Backend:
    """实现任意子集即可；未实现 = 返回空列表，渲染层会显示'-'。"""

    def me(self) -> Dict[str, Any]:
        return {
            "user": {"id": "local-user", "name": "local", "email": ""},
            "api_key": {"key_prefix": "lgz_local"},
        }

    # ---- 搜索 ----
    def search_notes(self, req: Dict[str, Any]) -> Dict[str, Any]:
        return _empty_search(req)

    def search_users(self, req: Dict[str, Any]) -> Dict[str, Any]:
        return {"platform": req.get("platform"), "query": req.get("query"), "users": [], "page": _page()}

    # ---- 账号 ----
    def user_info(self, req: Dict[str, Any]) -> Dict[str, Any]:
        return {"platform": req.get("platform"), "profile": {}, "stats": {}, "bio": "", "bio_preview": ""}

    def user_posted_notes(self, req: Dict[str, Any]) -> Dict[str, Any]:
        return {"platform": req.get("platform"), "user": {}, "items": [], "page": _page()}

    def analyze_user_profile(self, req: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "platform": req.get("platform"),
            "user": {},
            "page": _page(full_page=False),
            "items": [],
            "artifacts": {"subtitle_markdown": {"status": "unavailable"}},
            "warnings": [],
        }

    # ---- 内容 ----
    def note_detail(self, req: Dict[str, Any]) -> Dict[str, Any]:
        return {"platform": req.get("platform"), "item": {}}

    def note_comments(self, req: Dict[str, Any]) -> Dict[str, Any]:
        return {"comments": [], "page": _page()}

    # ---- 公众号 ----
    def article_detail(self, req: Dict[str, Any]) -> Dict[str, Any]:
        return {"article": {"title": "", "digest": "", "content_text": ""}}

    def article_stats(self, req: Dict[str, Any]) -> Dict[str, Any]:
        return {"metrics": {}}

    def related_articles(self, req: Dict[str, Any]) -> Dict[str, Any]:
        return {"articles": [], "page": _page()}

    # ---- 视频 / 生图 ----
    def extract_video_copy(self, req: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "batch": {"id": "local-batch", "status": "completed"},
            "replayed": False,
            "items": [],
        }

    def generate_image(self, req: Dict[str, Any], files: Any = None) -> Dict[str, Any]:
        # 未接入真实生图时明确失败，避免返回假图让下游误以为成功
        return {
            "type": "generate-image",
            "status": "failed",
            "pending_count": 0,
            "items": [
                {
                    "status": "error",
                    "error_code": "LOCAL_BACKEND_NOT_IMPLEMENTED",
                    "message": "生图已停用：本仓库只输出提示词",
                }
            ],
        }


def _page(**extra: Any) -> Dict[str, Any]:
    page = {"next_cursor": None, "limit": 20, "returned_count": 0}
    page.update(extra)
    return page


def _empty_search(req: Dict[str, Any]) -> Dict[str, Any]:
    return {"platform": req.get("platform"), "query": req.get("query"), "items": [], "page": _page()}


class MockBackend(Backend):
    """形状正确的假数据，用于验证链路和 playbook 渲染。"""

    def search_notes(self, req: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "platform": req.get("platform") or "xiaohongshu",
            "query": req.get("query") or "",
            "items": [
                {
                    "id": "mock_note_1",
                    "title": "【MOCK】小个子通勤穿搭 3 套",
                    "url": "https://www.xiaohongshu.com/explore/mock_note_1",
                    "content_type": "video",
                    "xhs_note_type": "video",
                    "author": {"id": "mock_user_1", "name": "MOCK 博主"},
                    "metrics": {"liked": 12000, "collected": 3400, "commented": 210, "shared": 96},
                    "tags": ["通勤穿搭", "小个子"],
                    "summary": "这是 MockBackend 生成的假数据，仅用于跑通渲染链路。",
                }
            ],
            "page": _page(returned_count=1),
        }

    def search_users(self, req: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "platform": req.get("platform") or "xiaohongshu",
            "query": req.get("query") or "",
            "users": [
                {
                    "id": "mock_user_1",
                    "name": "MOCK 博主",
                    "red_id": "mock123",
                    "url": "https://www.xiaohongshu.com/user/profile/mock_user_1",
                    "bio": "MOCK 简介",
                    "bio_preview": "MOCK 简介",
                    "stats": {"fans": 32000, "notes": 88, "liked": 210000},
                }
            ],
            "page": _page(returned_count=1),
        }

    def note_detail(self, req: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "platform": req.get("platform") or "xiaohongshu",
            "item": {
                "id": "mock_note_1",
                "title": "【MOCK】小个子通勤穿搭 3 套",
                "url": "https://www.xiaohongshu.com/explore/mock_note_1",
                "content_type": "video",
                "author": {"id": "mock_user_1", "name": "MOCK 博主"},
                "metrics": {"liked": 12000, "collected": 3400, "commented": 210, "shared": 96},
                "tags": ["通勤穿搭", "小个子"],
                "summary": "MOCK 数据",
                "text": "MOCK 正文：这里应该放你的真实采集结果。",
            },
        }

    def note_comments(self, req: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "comments": [
                {"text": "MOCK 评论：求链接", "liked": 12, "author": {"name": "路人甲"}},
                {"text": "MOCK 评论：小个子真的能穿吗", "liked": 8, "author": {"name": "路人乙"}},
            ],
            "page": _page(returned_count=2),
            "author": {"name": "MOCK 博主"},
        }

    def generate_image(self, req: Dict[str, Any], files: Any = None) -> Dict[str, Any]:
        base = str(req.get("_base_url") or "http://127.0.0.1:8787").rstrip("/")
        count = max(int(req.get("count") or 1), 1)
        # 注意：CLI 从 image.b64_json 解码落盘，不下载 URL
        image = {
            "b64_json": base64.b64encode(MOCK_PNG).decode("ascii"),
            "mime_type": "image/png",
            "sha256": MOCK_PNG_SHA256,
            "url": f"{base}/mock.png",
        }
        data = {
            "type": "generate-image",
            "status": "completed",
            "pending_count": 0,
            "batch_id": "mock-batch",
            "requested_count": count,
            "succeeded_count": count,
            "size": "1024x1024",
            "output_format": "png",
        }
        if count == 1:
            data["image"] = image
        else:
            data["images"] = [{"index": i, "image": dict(image)} for i in range(count)]
        return data


def load_backend() -> Backend:
    """按 LINGZAO_LOCAL_BACKEND=module:Class 加载；默认 MockBackend。"""
    spec = os.environ.get("LINGZAO_LOCAL_BACKEND", "").strip()
    if not spec:
        return MockBackend()
    module_name, _, attr = spec.partition(":")
    if not module_name or not attr:
        raise SystemExit("LINGZAO_LOCAL_BACKEND must look like 'my_backend:MyBackend'")
    import importlib

    module = importlib.import_module(module_name)
    target = getattr(module, attr)
    return target() if isinstance(target, type) else target
