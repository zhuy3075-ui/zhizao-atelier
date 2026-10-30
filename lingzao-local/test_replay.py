"""离线回归：把 docs/examples 里的真实样本喂给归一化层，检查字段是否被正确抽出。

用法: python test_replay.py
"""
from __future__ import annotations

import json
import pathlib
import sys

import justone as J

EX = pathlib.Path(__file__).parent / "docs" / "examples"

# slug 关键字 -> 操作
OP_RULES = [
    ("comment", "comments"),
    ("caption", "skip"),
    ("get_user_detail", "user_info"),
    ("get_user_v3", "user_info"),
    ("get_kol_info", "user_info"),
    ("get_user_note_list", "user_posts"),
    ("get_user_video_list", "user_posts"),
    ("get_user_post", "user_posts"),
    ("channel_videos", "user_posts"),
    ("account_videos", "user_posts"),
    ("history_articles", "user_posts"),
    ("search_user", "search_users"),
    ("detail", "detail"),
    ("search", "search"),
]


def infer_op(slug: str) -> str:
    for needle, op in OP_RULES:
        if needle in slug:
            return op
    return "search"


def main() -> int:
    rows = []
    for f in sorted(EX.glob("*.json")):
        plat, _, slug = f.stem.partition("__")
        if plat not in J.NOTE_SPEC and plat not in J.USER_SPEC:
            continue  # 商业数据源另行验证
        op = infer_op(slug)
        if op == "skip":
            continue
        payload = json.loads(f.read_text(encoding="utf-8"))["example"]
        try:
            if op == "search":
                rows.extend(_check(f.stem, op, lambda p: [J.norm_note(r, plat) for r in J._locate_list(p, J.NOTE_SPEC.get(plat, {}).get("list", []))], payload))
            elif op == "user_posts":
                rows.extend(_check(f.stem, op, lambda p: [J.norm_note(r, plat) for r in J._locate_list(p, J.NOTE_SPEC.get(plat, {}).get("list", []))], payload))
            elif op == "search_users":
                rows.extend(_check(f.stem, op, lambda p: [J.norm_user(r, plat) for r in J._locate_list(p, J.USER_SPEC.get(plat, {}).get("list", []))], payload))
            elif op == "comments":
                rows.extend(_check(f.stem, op, lambda p: J.norm_comments(p, plat), payload))
            elif op == "detail":
                block = J.detail_block(plat, payload)
                note = J.norm_note(block, plat)
                note["text"] = J.first_text(block, "desc", "content", "text", "summary")
                rows.append(_row(f.stem, op, [note]))
            elif op == "user_info":
                block = J.user_block(plat, payload)
                rows.append(_row(f.stem, op, [J.norm_user(block, plat)]))
        except Exception as exc:  # noqa: BLE001
            rows.append({"file": f.stem, "op": op, "n": 0, "id": 0, "title": 0, "metric": 0, "err": repr(exc)[:50]})
    return _report(rows)


def _check(name, op, fn, payload):
    return [_row(name, op, fn(payload))]


def _row(name, op, items):
    if op == "comments":
        idh = sum(1 for i in items if i.get("text"))
        titleh = sum(1 for i in items if i.get("author", {}).get("name"))
        metrich = sum(1 for i in items if i.get("liked"))
    elif op in ("search_users", "user_info"):
        idh = sum(1 for i in items if i.get("id"))
        titleh = sum(1 for i in items if i.get("name"))
        metrich = sum(1 for i in items if i.get("stats", {}).get("fans"))
    else:
        idh = sum(1 for i in items if i.get("id"))
        titleh = sum(1 for i in items if i.get("title"))
        metrich = sum(1 for i in items if any(i.get("metrics", {}).values()))
    return {"file": name, "op": op, "n": len(items), "id": idh, "title": titleh, "metric": metrich, "err": ""}


def _report(rows) -> int:
    ok = 0
    print(f"{'file':<46}{'op':<13}{'n':>4}{'id':>4}{'title':>6}{'metric':>7}  status")
    for r in rows:
        good = r["n"] > 0 and r["id"] > 0 and r["title"] > 0
        ok += 1 if good else 0
        flag = "OK" if good else ("EMPTY" if r["n"] == 0 else "PARTIAL")
        if r["err"]:
            flag = "ERROR " + r["err"]
        print(f"{r['file']:<46}{r['op']:<13}{r['n']:>4}{r['id']:>4}{r['title']:>6}{r['metric']:>7}  {flag}")
    print(f"\n{ok}/{len(rows)} 完全通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
