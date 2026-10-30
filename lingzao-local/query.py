"""agent 用的紧凑查询器：调 JustOneAPI，输出压缩后的结构视图。

为什么不用织造 CLI：CLI 按固定形状渲染，字段表没命中就全是 `-`。
这个工具把响应压到几 KB 后直接给 agent 看，字段由 agent 现场判断。

用法:
    python query.py search --platform xiaohongshu --keyword "通勤穿搭"
    python query.py detail --platform douyin --id 7xxxx
    python query.py comments --platform weibo --id 5xxxx
    python query.py --sample docs/examples/tiktok__search_post_v1.json   # 离线看样本

环境变量: JUSTONEAPI_TOKEN
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

import justone as J


def load_sample(path: str) -> dict:
    data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    return data.get("example") or data


def main() -> int:
    ap = argparse.ArgumentParser(description="compact JustOneAPI query for agents")
    ap.add_argument("op", nargs="?", default="search", choices=["search", "detail", "comments", "user_posts", "user_info"])
    ap.add_argument("--platform", default="xiaohongshu")
    ap.add_argument("--keyword")
    ap.add_argument("--id", dest="item_id")
    ap.add_argument("--page", type=int, default=1)
    ap.add_argument("--sample", help="离线读本地样本，不发请求")
    ap.add_argument("--raw-bytes", action="store_true", help="打印压缩前后的字节数")
    ap.add_argument("--full", action="store_true", help="打印完整紧凑视图（默认截断输出）")
    args = ap.parse_args()

    if args.sample:
        payload = load_sample(args.sample)
    else:
        backend = J.JustOneBackend()
        ctx = {"keyword": args.keyword, "item_id": args.item_id, "page": args.page}
        payload = backend._exec(args.platform, args.op, ctx)

    view = J.compact_view(payload)
    text = json.dumps(view, ensure_ascii=False, indent=1)

    if args.raw_bytes:
        raw_len = len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        out_len = len(text.encode("utf-8"))
        ratio = (raw_len / out_len) if out_len else 0
        print(f"# raw={raw_len/1024:.0f}KB  compact={out_len/1024:.1f}KB  压缩 {ratio:.0f}x", file=sys.stderr)

    if not args.full and len(text) > 6000:
        text = text[:6000] + "\n... (truncated; use --full)"
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
