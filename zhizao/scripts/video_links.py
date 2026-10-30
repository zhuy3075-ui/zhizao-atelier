"""批量提取博主主页里的视频直链（多平台）。

主页列表只有笔记链接，不含视频文件；要视频必须逐条查详情。
所以：N 条视频 = N 次详情调用（按条计费）。

这个脚本是 skill 自带的，可以从任何位置运行：它会自己找本地后端。

用法：
    python "<skill_root>/scripts/video_links.py" --platform xiaohongshu --user "<主页链接或ID>" --limit 10
    python "<skill_root>/scripts/video_links.py" --platform douyin --user "<sec_uid>" --limit 5 --out dy.csv
    python "<skill_root>/scripts/video_links.py" --platform tiktok --user "<secUid>" --limit 5

后端位置解析顺序：
    1. 环境变量 LINGZAO_LOCAL_DIR
    2. 包布局：脚本同级 ../lingzao-local
    3. 安装布局：~/.lingzao-local
    4. 脚本所在目录本身（兼容旧位置）

平台差异：
- xiaohongshu：user 可以是主页链接，自动抽 ID
- douyin：需要 sec_uid（不是 uid）
- tiktok：需要 secUid
- kuaishou：需要 userId

直链带签名，通常几小时失效，拿到就下。配套下载脚本：scripts/download_videos.ps1
"""
from __future__ import annotations

import argparse
import csv
import os
import pathlib
import sys
import time


def _load_backend():
    """把本地后端目录塞进 sys.path，然后导入 justone。"""
    here = pathlib.Path(__file__).resolve().parent
    candidates = []
    env = os.environ.get("LINGZAO_LOCAL_DIR")
    if env:
        candidates.append(pathlib.Path(env))
    candidates += [
        here,                                     # 脚本就在后端目录里（旧位置）
        here.parents[1] / "lingzao-local",         # 分发包布局：zhizao/scripts -> ../lingzao-local
        here.parents[3] / ".lingzao-local"         if len(here.parents) > 3 else here,  # 安装布局：<root>/.agents/skills/zhizao/scripts
        here.parent / "lingzao-local",             # 少数布局：scripts/lingzao-local
        pathlib.Path.home() / ".lingzao-local",    # 安装后布局
    ]
    for c in candidates:
        if (c / "justone.py").exists():
            sys.path.insert(0, str(c))
            return c
    raise SystemExit(
        "找不到本地后端 justone.py。\n"
        "请设置环境变量 LINGZAO_LOCAL_DIR 指向 lingzao-local 目录，"
        "或确认已用 install.ps1 安装（默认 ~/.lingzao-local）。"
    )


BACKEND_DIR = _load_backend()
import justone as J  # noqa: E402

PLATFORMS = ("xiaohongshu", "douyin", "tiktok", "kuaishou")


def main() -> int:
    ap = argparse.ArgumentParser(description="批量提取主页视频直链")
    ap.add_argument("--platform", default="xiaohongshu", choices=PLATFORMS)
    ap.add_argument("--user", required=True, help="主页链接或用户 ID（抖音/TikTok 需 sec_uid / secUid）")
    ap.add_argument("--limit", type=int, default=10, help="最多处理多少条视频（会逐条计费）")
    ap.add_argument("--out", help="导出 CSV 路径")
    ap.add_argument("--all-types", action="store_true", help="不筛类型，所有作品都试一遍")
    args = ap.parse_args()

    b = J.JustOneBackend()
    if not b.token:
        print("缺少 JUSTONEAPI_TOKEN，先运行安装脚本配置数据密钥。", file=sys.stderr)
        return 2

    plat = args.platform
    uid = J.coerce_id(plat, args.user)
    print(f"平台: {plat}  用户: {uid}", file=sys.stderr)
    print(f"后端: {BACKEND_DIR}", file=sys.stderr)

    page = b.user_posted_notes({"platform": plat, "user_id": uid})
    items = page.get("items") or []
    videos = [it for it in items if args.all_types or (it.get("content_type") or "").lower() == "video"]
    if not videos:
        videos = items  # 有些平台不返回类型，退回全试
    target = videos[: args.limit]
    print(f"作品 {len(items)} 条，候选 {len(videos)} 条，处理 {len(target)} 条", file=sys.stderr)

    rows = []
    for i, it in enumerate(target, 1):
        nid = it.get("id") or ""
        try:
            payload = b._exec(plat, "detail", {"item_id": nid})
            url = J.find_video_url(payload)
        except J.JustOneError as exc:
            print(f"  [{i}/{len(target)}] {nid} 失败: {str(exc)[:60]}", file=sys.stderr)
            continue
        kind = "m4a" if ".m4a" in url else ("mp4" if url else "-")
        rows.append({
            "platform": plat,
            "item_id": nid,
            "title": it.get("title", ""),
            "note_url": it.get("url", ""),
            "video_url": url,
            "kind": kind,
            "liked": it.get("metrics", {}).get("liked", 0),
        })
        print(f"  [{i}/{len(target)}] {'✓' if url else '✗'} {kind:<3} {it.get('title','')[:28]}", file=sys.stderr)
        time.sleep(0.3)

    got = [r for r in rows if r["video_url"]]
    print(f"\n成功 {len(got)} / {len(rows)}")
    for r in got:
        print(f"\n{r['title'][:40]}")
        print(f"  笔记: {r['note_url']}")
        print(f"  视频: {r['video_url'][:110]}")

    if args.out:
        out = pathlib.Path(args.out)
        with out.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["platform", "item_id", "title", "note_url", "video_url", "kind", "liked"])
            w.writeheader()
            w.writerows(rows)
        print(f"\n已导出: {out.resolve()}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
