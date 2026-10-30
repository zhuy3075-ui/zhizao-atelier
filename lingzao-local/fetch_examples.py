"""拉取 JustOneAPI 每个端点的真实响应示例，并生成结构摘要。

用法: python fetch_examples.py
输出: docs/examples/<platform>__<slug>.json  原始样本
      docs/shapes.md                          结构摘要（人读 + 用于写映射）
"""
from __future__ import annotations

import json
import pathlib
import time
import urllib.parse
import urllib.request

BASE = "https://api.justoneapi.com/status/api-example/detail"
OUT = pathlib.Path(__file__).parent / "docs"
EX = OUT / "examples"
EX.mkdir(parents=True, exist_ok=True)

# platform 标签 -> [(别名, api 路径)]
TARGETS = {
    "xiaohongshu": [
        ("search_note_v2", "/api/xiaohongshu/search-note/v2"),
        ("search_user_v2", "/api/xiaohongshu/search-user/v2"),
        ("get_user_v3", "/api/xiaohongshu/get-user/v3"),
        ("get_user_note_list_v4", "/api/xiaohongshu/get-user-note-list/v4"),
        ("get_note_detail_v6", "/api/xiaohongshu/get-note-detail/v6"),
        ("get_note_comment_v2", "/api/xiaohongshu/get-note-comment/v2"),
    ],
    "douyin": [
        ("search_video_v4", "/api/douyin/search-video/v4"),
        ("search_user_v2", "/api/douyin/search-user/v2"),
        ("get_user_detail_v3", "/api/douyin/get-user-detail/v3"),
        ("get_user_video_list_v1", "/api/douyin/get-user-video-list/v1"),
        ("get_video_detail_v2", "/api/douyin/get-video-detail/v2"),
        ("get_video_comment_v1", "/api/douyin/get-video-comment/v1"),
    ],
    "kuaishou": [
        ("search_video_v2", "/api/kuaishou/search-video/v2"),
        ("search_user_v2", "/api/kuaishou/search-user/v2"),
        ("get_user_detail_v1", "/api/kuaishou/get-user-detail/v1"),
        ("get_user_video_list_v2", "/api/kuaishou/get-user-video-list/v2"),
        ("get_video_detail_v2", "/api/kuaishou/get-video-detail/v2"),
        ("get_video_comment_v1", "/api/kuaishou/get-video-comment/v1"),
    ],
    "weixin": [
        ("search_article_v2", "/api/weixin/search-article/v2"),
        ("get_article_detail_v5", "/api/weixin/get-article-detail/v5"),
        ("get_article_metrics_v2", "/api/weixin/get-article-metrics/v2"),
        ("search_account_v2", "/api/weixin/search-account/v2"),
        ("get_account_history_articles_v2", "/api/weixin/get-account-history-articles/v2"),
    ],
    "weixin_channels": [
        ("search_video_v2", "/api/weixin-channels/search-video/v2"),
        ("search_account_v3", "/api/weixin-channels/search-account/v3"),
        ("get_account_videos_v1", "/api/weixin-channels/get-account-videos/v1"),
        ("get_video_basic_info_v1", "/api/weixin-channels/get-video-basic-info/v1"),
        ("get_video_comment_v1", "/api/weixin-channels/get-video-comment/v1"),
    ],
    "weibo": [
        ("search_all_v2", "/api/weibo/search-all/v2"),
        ("search_profile_v1", "/api/weibo/search-profile/v1"),
        ("get_user_detail_v3", "/api/weibo/get-user-detail/v3"),
        ("get_user_post_v1", "/api/weibo/get-user-post/v1"),
        ("get_weibo_detail_v1", "/api/weibo/get-weibo-detail/v1"),
        ("get_post_comments_v1", "/api/weibo/get-post-comments/v1"),
    ],
    "bilibili": [
        ("search_video_v2", "/api/bilibili/search-video/v2"),
        ("get_video_detail_v2", "/api/bilibili/get-video-detail/v2"),
        ("get_video_comment_v2", "/api/bilibili/get-video-comment/v2"),
        ("get_user_detail_v2", "/api/bilibili/get-user-detail/v2"),
        ("get_user_video_list_v2", "/api/bilibili/get-user-video-list/v2"),
        ("get_video_caption_v2", "/api/bilibili/get-video-caption/v2"),
    ],
    "tiktok": [
        ("search_post_v1", "/api/tiktok/search-post/v1"),
        ("search_user_v1", "/api/tiktok/search-user/v1"),
        ("get_user_detail_v1", "/api/tiktok/get-user-detail/v1"),
        ("get_user_post_v1", "/api/tiktok/get-user-post/v1"),
        ("get_post_detail_v1", "/api/tiktok/get-post-detail/v1"),
        ("get_post_comment_v1", "/api/tiktok/get-post-comment/v1"),
    ],
    "youtube": [
        ("search_v1", "/api/youtube/search/v1"),
        ("get_video_detail_v1", "/api/youtube/get-video-detail/v1"),
        ("get_video_comment_v1", "/api/youtube/get-video-comment/v1"),
        ("get_channel_videos_v1", "/api/youtube/get-channel-videos/v1"),
        ("get_video_captions_v1", "/api/youtube/get-video-captions/v1"),
    ],
    "reddit": [
        ("search_v1", "/api/reddit/search/v1"),
        ("get_post_detail_v1", "/api/reddit/get-post-detail/v1"),
        ("get_post_comments_v1", "/api/reddit/get-post-comments/v1"),
    ],
    "toutiao": [
        ("search_v2", "/api/toutiao/search/v2"),
        ("get_user_detail_v1", "/api/toutiao/get-user-detail/v1"),
        ("get_article_detail_v1", "/api/toutiao/get-article-detail/v1"),
    ],
    "twitter": [
        ("search_v1", "/api/twitter/search/v1"),
        ("get_user_detail_v1", "/api/twitter/get-user-detail/v1"),
        ("get_user_posts_v1", "/api/twitter/get-user-posts/v1"),
        ("get_post_detail_v1", "/api/twitter/get-post-detail/v1"),
        ("get_post_comments_v1", "/api/twitter/get-post-comments/v1"),
    ],
    # —— 织造缺的商业数据源 ——
    "xiaohongshu_pgy": [
        ("get_kol_info_v1", "/api/xiaohongshu-pgy/get-kol-info/v1"),
        ("get_kol_data_summary_v2", "/api/xiaohongshu-pgy/get-kol-data-summary/v2"),
        ("get_kol_fans_summary_v1", "/api/xiaohongshu-pgy/get-kol-fans-summary/v1"),
        ("get_similar_kol_v1", "/api/xiaohongshu-pgy/api/solar/kol/get_similar_kol/v1"),
        ("get_kol_note_list_v1", "/api/xiaohongshu-pgy/get-kol-note-list/v1"),
        ("get_kol_feature_tags_v1", "/api/xiaohongshu-pgy/api/solar/kol/dataV2/kolFeatureTags/v1"),
        ("get_kol_content_tags_v1", "/api/xiaohongshu-pgy/api/solar/kol/dataV2/kolContentTags/v1"),
    ],
    "douyin_xingtu": [
        ("get_kol_info_v1", "/api/douyin-xingtu/get-kol-info/v1"),
        ("get_kol_audience_distribution_v1", "/api/douyin-xingtu/get-kol-audience-distribution/v1"),
        ("get_author_content_hot_keywords_v1", "/api/douyin-xingtu/get-author-content-hot-keywords/v1"),
        ("get_author_hot_comment_tokens_v1", "/api/douyin-xingtu/get-author-hot-comment-tokens/v1"),
        ("get_kol_spread_info_v1", "/api/douyin-xingtu/get-kol-spread-info/v1"),
    ],
    "qq_huxuan": [
        ("finder_publisher_search_v1", "/api/qq-huxuan/cgi-bin/advertiser/finder_publisher/search/v1"),
        ("finder_publisher_detail_v1", "/api/qq-huxuan/cgi-bin/advertiser/finder_publisher/detail/v1"),
    ],
}


def fetch(api: str) -> dict | None:
    url = f"{BASE}?{urllib.parse.urlencode({'api': api})}"
    req = urllib.request.Request(url, headers={"accept": "application/json"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if payload.get("code") not in (0, None):
        return None
    return payload.get("data")


def item_keys(items, limit=45):
    """列表样本里前 3 条的键并集（含一层子对象键）。"""
    keys = set()
    for it in items[:3]:
        if not isinstance(it, dict):
            continue
        for k, v in it.items():
            keys.add(k)
            if isinstance(v, dict):
                for sub in list(v.keys())[:8]:
                    keys.add(f"{k}.{sub}")
    return sorted(keys)[:limit]


def digest(label: str, api: str, detail: dict) -> list[str]:
    out = [f"## {label}  `{api}`"]
    ex = detail.get("example")
    if not ex:
        out.append("- ⚠ 无样本")
        return out
    data = ex.get("data")
    if not isinstance(data, dict):
        out.append(f"- data 类型: {type(data).__name__}")
        return out
    out.append(f"- data 键: {', '.join(list(data.keys())[:20])}")
    for k, v in data.items():
        if isinstance(v, list) and v:
            out.append(f"- `data.{k}` 列表 len={len(v)} 项键: {', '.join(item_keys(v))}")
        elif isinstance(v, list):
            out.append(f"- `data.{k}` 空列表")
        elif isinstance(v, dict):
            out.append(f"- `data.{k}` 对象键: {', '.join(list(v.keys())[:15])}")
    return out


def main() -> int:
    lines = ["# JustOneAPI 真实响应结构", "", "由 `/status/api-example/detail` 拉取的真实样本生成。", ""]
    total = 0
    for plat, eps in TARGETS.items():
        for slug, api in eps:
            name = f"{plat}__{slug}"
            try:
                detail = fetch(api)
            except Exception as exc:  # noqa: BLE001
                lines.append(f"## {name}  `{api}`\n- ❌ 拉取失败: {exc}\n")
                continue
            if detail is None:
                lines.append(f"## {name}  `{api}`\n- ❌ 业务错误\n")
                continue
            (EX / f"{name}.json").write_text(
                json.dumps(detail, ensure_ascii=False, indent=1), encoding="utf-8"
            )
            lines.extend(digest(name, api, detail))
            lines.append("")
            total += 1
            time.sleep(0.15)
    (OUT / "shapes.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"saved {total} examples -> {EX}")
    print(f"digest -> {OUT / 'shapes.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
