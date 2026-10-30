"""真实调用矩阵：验证各平台 detail / comments / 商业数据源。会产生费用，按需运行。

    python test_live.py            # 全部
    python test_live.py douyin     # 只跑某平台
"""
from __future__ import annotations

import json
import sys
from typing import Any, Dict

import justone as J


def brief(items: Any, n: int = 2) -> str:
    if not isinstance(items, list):
        return "n/a"
    out = []
    for it in items[:n]:
        if isinstance(it, dict):
            title = it.get("title") or it.get("text") or it.get("name") or ""
            out.append(str(title)[:28])
    return f"n={len(items)} " + " | ".join(out)


def run(label: str, fn) -> None:
    try:
        r = fn()
        print(f"OK   {label:<34} {r}")
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL {label:<34} {str(exc)[:80]}")


def main() -> int:
    b = J.JustOneBackend()
    only = sys.argv[1] if len(sys.argv) > 1 else ""

    def want(name: str) -> bool:
        return not only or only == name

    if want("douyin"):
        vid = "7545457847732079929"
        run("douyin detail", lambda: b.note_detail({"platform": "douyin", "note_id": vid})["item"]["title"][:40])
        run("douyin comments", lambda: brief(b.note_comments({"platform": "douyin", "note_id": vid})["comments"]))

    if want("kuaishou"):
        s = b.search_notes({"platform": "kuaishou", "query": "穿搭"})
        kid = s["items"][0]["id"] if s["items"] else ""
        run("kuaishou search", lambda: brief(s["items"]))
        if kid:
            run("kuaishou detail", lambda: b.note_detail({"platform": "kuaishou", "note_id": kid})["item"]["title"][:40])
            run("kuaishou comments", lambda: brief(b.note_comments({"platform": "kuaishou", "note_id": kid})["comments"]))

    if want("tiktok"):
        s = b.search_notes({"platform": "tiktok", "query": "outfit"})
        tid = s["items"][0]["id"] if s["items"] else ""
        run("tiktok search", lambda: brief(s["items"]))
        if tid:
            run("tiktok detail", lambda: b.note_detail({"platform": "tiktok", "note_id": tid})["item"]["title"][:40])
            run("tiktok comments", lambda: brief(b.note_comments({"platform": "tiktok", "note_id": tid})["comments"]))

    if want("xingtu"):
        p = b._call("/api/douyin-xingtu/gw/api/gsearch/search_for_author_square/v1", {"keyword": "穿搭", "page": 1})
        rows = J.find_largest_list(p.get("data") or {})
        run("xingtu search", lambda: brief(rows))
        if rows:
            kid = str(J.pick(rows[0], "kolId", "id", "authorId", default=""))
            run("xingtu kol info", lambda: str(J.first_text(b._call(
                "/api/douyin-xingtu/get-kol-info/v1", {"kolId": kid}).get("data") or {}, "name", "nickname")))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
