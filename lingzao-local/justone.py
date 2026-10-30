"""织造本地后端 · JustOneAPI 实现（v2，按真实响应样本校准）。

与 v1 的区别：不再靠"深度键猜测"。每个平台/操作都有明确的数组定位路径和字段映射，
依据是官方 `/status/api-example/detail` 返回的真实抓包样本（见 docs/examples/）。

启动：
    set JUSTONEAPI_TOKEN=xxx
    set LINGZAO_LOCAL_BACKEND=justone:JustOneBackend
    python server.py --port 8787
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Sequence

from backend import Backend, _page

BASE_URL = os.environ.get("JUSTONEAPI_BASE_URL", "https://api.justoneapi.com").rstrip("/")
TIMEOUT = int(os.environ.get("JUSTONEAPI_TIMEOUT", "120"))
RETRIES = int(os.environ.get("JUSTONEAPI_RETRIES", "2"))
RAW = os.environ.get("LINGZAO_JUSTONE_RAW", "").lower() in {"1", "true", "yes"}

PLATFORM_ALIAS = {
    "xiaohongshu": "xiaohongshu", "xhs": "xiaohongshu", "rednote": "xiaohongshu",
    "douyin": "douyin", "kuaishou": "kuaishou",
    "wechat_official": "weixin", "wechat_oa": "weixin", "weixin": "weixin",
    "wechat_channels": "weixin_channels", "weixin_channels": "weixin_channels",
    "weibo": "weibo", "bilibili": "bilibili", "tiktok": "tiktok",
    "youtube": "youtube", "reddit": "reddit", "toutiao": "toutiao", "twitter": "twitter", "x": "twitter",
}

# path 里的平台段（JustOneAPI 实际路径用连字符）
PATH_SEG = {"weixin": "weixin", "weixin_channels": "weixin-channels", "xiaohongshu": "xiaohongshu"}


class JustOneError(RuntimeError):
    pass


# ---------------------------------------------------------------- 取值工具

def path_get(obj: Any, path: str) -> Any:
    """支持 'a.b' / 'a[0].b' / 'a[]'。"""
    cur = obj
    for part in path.split("."):
        if cur is None:
            return None
        if part.endswith("[]"):
            cur = cur.get(part[:-2]) if isinstance(cur, dict) else None
            if isinstance(cur, list):
                return cur
            return None
        if part.endswith("]"):
            name, _, idx = part[:-1].partition("[")
            cur = cur.get(name) if isinstance(cur, dict) else None
            try:
                cur = cur[int(idx)] if isinstance(cur, list) else None
            except (ValueError, IndexError):
                return None
        else:
            cur = cur.get(part) if isinstance(cur, dict) else None
    return cur


def pick(obj: Any, *candidates: str, default: Any = None) -> Any:
    for c in candidates:
        v = path_get(obj, c) if "." in c or "[" in c else (obj.get(c) if isinstance(obj, dict) else None)
        if v not in (None, "", [], {}):
            return v
    return default


def maybe_json(v: Any) -> Any:
    """抖音等平台把内层数据塞成 JSON 字符串。"""
    if isinstance(v, str) and v[:1] in "{[":
        try:
            return json.loads(v)
        except (ValueError, TypeError):
            return v
    return v


def unwrap_envelope(payload: Any, limit: int = 3) -> Any:
    """剥掉 {code,message,ttl,data} 这类信封层（B 站等平台是双层）。"""
    cur = payload
    for _ in range(limit):
        if isinstance(cur, dict) and "data" in cur:
            inner = cur["data"]
            keys = set(cur.keys())
            looks_envelope = bool(keys & {"code", "ttl", "message"}) and isinstance(inner, dict) and "data" in inner
            if looks_envelope:
                cur = inner
                continue
        break
    return cur


def find_largest_list(obj: Any, depth: int = 0) -> List[Any]:
    """兜底：在未知结构里找最长的 dict 列表。"""
    best: List[Any] = []
    if depth > 5:
        return best
    if isinstance(obj, dict):
        for v in obj.values():
            if isinstance(v, list) and v and isinstance(v[0], dict) and len(v) > len(best):
                best = v
            elif isinstance(v, (dict, list)):
                cand = find_largest_list(v, depth + 1)
                if len(cand) > len(best):
                    best = cand
    elif isinstance(obj, list):
        for v in obj[:10]:
            cand = find_largest_list(v, depth + 1)
            if len(cand) > len(best):
                best = cand
    return best


def to_int(v: Any) -> int:
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, (int, float)):
        return int(v)
    if isinstance(v, str):
        s = v.strip().replace(",", "").replace("+", "")
        mult = 1
        for suf, m in (("万", 10000), ("w", 10000), ("W", 10000), ("亿", 100000000), ("k", 1000), ("K", 1000)):
            if s.endswith(suf):
                mult, s = m, s[: -len(suf)]
                break
        try:
            return int(float(s) * mult)
        except ValueError:
            return 0
    return 0


def first_text(obj: Any, *cands: str) -> str:
    v = pick(obj, *cands)
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, str):
        return " ".join(v.split())[:300]
    return ""


def compact_view(payload: Any, max_items: int = 8, max_str: int = 60, depth: int = 4) -> Dict[str, Any]:
    """把任意平台的响应压成 agent 可读的紧凑视图。

    不依赖任何字段表：只认"数组里装 dict"这种通用结构。
    2MB 的响应通常能压到几 KB，语义判断留给 agent。
    """
    def slim(v, d=0):
        if d > depth:
            return None
        if isinstance(v, dict):
            out = {}
            for k, val in v.items():
                if isinstance(val, (dict, list)):
                    continue
                if isinstance(val, str):
                    if not val.strip():
                        continue
                    out[k] = val[:max_str]
                elif isinstance(val, (int, float, bool)):
                    out[k] = val
            return out
        return None

    blocks = []
    seen = set()

    def walk(node, path="data", d=0):
        if d > 4 or len(blocks) >= 6:
            return
        if isinstance(node, dict):
            for k, v in node.items():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    key = f"{path}.{k}"
                    if key in seen:
                        continue
                    seen.add(key)
                    inner = []
                    for it in v[:max_items]:
                        if not isinstance(it, dict):
                            continue
                        row = slim(it)
                        # 再把子对象压平一层（author/statistics 这类）
                        for sk, sv in it.items():
                            if isinstance(sv, dict):
                                for kk, vv in list(sv.items())[:8]:
                                    if isinstance(vv, (str, int, float, bool)) and not isinstance(vv, bool) or isinstance(vv, bool):
                                        if isinstance(vv, str) and not vv.strip():
                                            continue
                                        row[f"{sk}.{kk}"] = vv[:max_str] if isinstance(vv, str) else vv
                        inner.append(row)
                    if inner:
                        blocks.append({"path": key, "count": len(v), "items": inner})
                elif isinstance(v, (dict, list)):
                    walk(v, f"{path}.{k}", d + 1)
        elif isinstance(node, list):
            for it in node[:3]:
                walk(it, path, d + 1)

    walk(payload)
    # 按"字段丰富度"排序：内容数组的字段多，UI 配置数组的字段少
    def richness(b):
        items = b["items"][:3] or [{}]
        return sum(len([k for k, v in it.items() if not isinstance(v, (dict, list))]) for it in items) / len(items)

    blocks = [b for b in blocks if b["count"] >= 2 and richness(b) >= 2]
    blocks.sort(key=lambda b: (richness(b), b["count"]), reverse=True)
    # 兜底：没有内容数组时，输出有界标量路径（Reddit 这类纯嵌套结构）
    scalars: Dict[str, Any] = {}

    def leaves(node, path="data", d=0):
        if d > 6 or len(scalars) >= 120:
            return
        if isinstance(node, dict):
            for k, v in node.items():
                if isinstance(v, (dict, list)):
                    leaves(v, f"{path}.{k}", d + 1)
                elif isinstance(v, str):
                    if v.strip():
                        scalars[f"{path}.{k}"] = v[:max_str]
                elif isinstance(v, (int, float, bool)):
                    scalars[f"{path}.{k}"] = v
        elif isinstance(node, list):
            for i, v in enumerate(node[:3]):
                leaves(v, f"{path}[{i}]", d + 1)

    if not blocks:
        leaves(payload)

    top = slim(payload) or {}
    return {"top_level": top, "content_arrays": blocks[:3], "scalars": scalars}

ID_PATTERNS = {
    "xiaohongshu": [r"/explore/([0-9a-f]{16,})", r"/discovery/item/([0-9a-f]{16,})", r"/user/profile/([0-9a-f]{16,})"],
    "douyin": [r"/video/(\d+)", r"/user/([\w\-]+)"],
    "tiktok": [r"/video/(\d+)", r"/photo/(\d+)", r"/@[\w.]+"],
    "kuaishou": [r"/short-video/([\w\-]+)", r"/profile/([\w\-]+)"],
    "bilibili": [r"/video/(BV[0-9A-Za-z]+)", r"space\.bilibili\.com/(\d+)"],
    "weibo": [r"/detail/(\d+)", r"/status/(\w+)", r"/u/(\d+)"],
    "youtube": [r"[?&]v=([\w\-]{6,})", r"youtu\.be/([\w\-]{6,})", r"/channel/([\w\-]+)"],
    "twitter": [r"/status/(\d+)"],
    "reddit": [r"/comments/([\w]+)"],
}


def coerce_id(plat: str, value: Any) -> Any:
    """把 URL 里的 ID 抽出来；不是 URL 就原样返回。"""
    if not isinstance(value, str) or not value.startswith("http"):
        return value
    for pat in ID_PATTERNS.get(plat, []):
        m = re.search(pat, value)
        if m:
            return m.group(1)
    return value

# ---------------------------------------------------------------- 规格表
# list:  内容数组路径（按顺序尝试）
# unwrap: 数组元素里再取一层（如小红书 items[].note）
# 字段: 均为候选路径，按顺序取第一个非空

NOTE_SPEC: Dict[str, Dict[str, Any]] = {
    "xiaohongshu": {
        "list": ["data.items"], "unwrap": ["note"],
        "id": ["id", "note_id", "noteId"],
        "title": ["display_title", "title", "desc"],
        "desc": ["desc", "title"],
        "liked": ["liked_count", "likes", "liked"],
        "collected": ["collected_count", "collected"],
        "commented": ["comments_count", "comment_count"],
        "shared": ["shared_count", "share_count"],
        "author": ["user.nickname", "user.name"], "author_id": ["user.userid", "user.id"],
        "tags": ["tag_info", "hash_tag"],
        "time": ["create_time", "time"],
        "url_tpl": "https://www.xiaohongshu.com/explore/{id}",
    },
    "douyin": {
        "list": ["data.business_data", "data.aweme_list"], "unwrap": ["data.aweme_info"],
        "id": ["aweme_id", "id"], "title": ["desc"], "desc": ["desc"],
        "liked": ["statistics.digg_count"], "collected": ["statistics.collect_count"],
        "commented": ["statistics.comment_count"], "shared": ["statistics.share_count"],
        "author": ["author.nickname"], "author_id": ["author.sec_uid", "author.uid"],
        "tags": ["cha_list"], "time": ["create_time"], "url": ["share_url"],
    },
    "kuaishou": {
        "list": ["data.feeds"], "unwrap": [],
        "id": ["id", "photo_id", "photoId"], "title": ["caption", "title"], "desc": ["caption"],
        "liked": ["like_count", "likeCount", "realLikeCount"], "collected": ["collect_count", "collectCount"],
        "commented": ["comment_count", "commentCount"], "shared": ["forward_count", "shareCount"],
        "author": ["author.name", "user_name", "userName"], "author_id": ["author.id", "user_id"],
        "time": ["timestamp", "create_time"], "url": ["main_mv_urls.0.url"],
    },
    "weibo": {
        "list": ["data.weibo_list", "data.list"], "unwrap": [],
        "id": ["id", "mid", "bid"], "title": ["text"], "desc": ["text"],
        "liked": ["attitudes_count", "attitudes"], "collected": ["fav_count"],
        "commented": ["comments_count", "comments"], "shared": ["reposts_count", "reposts"],
        "author": ["screen_name", "user.screen_name"], "author_id": ["user_id", "user.id"],
        "time": ["created_at"], "url": ["article_url", "scheme"],
    },
    "bilibili": {
        "list": ["data.result", "data.data.result"], "unwrap": [],
        "id": ["bvid", "aid"], "title": ["title"], "desc": ["description", "desc"],
        "liked": ["like", "stat.like"], "collected": ["favorites", "stat.favorite"],
        "commented": ["review", "stat.reply"], "shared": ["share", "stat.share"],
        "author": ["author", "owner.name", "up_name"], "author_id": ["mid", "owner.mid", "up_id"],
        "time": ["pubdate", "senddate"], "url_tpl": "https://www.bilibili.com/video/{id}",
    },
    "tiktok": {
        "list": ["data.search_item_list", "data.aweme_list"], "unwrap": ["aweme_info"],
        "id": ["aweme_id", "id"], "title": ["desc"], "desc": ["desc"],
        "liked": ["statistics.digg_count"], "collected": ["statistics.collect_count"],
        "commented": ["statistics.comment_count"], "shared": ["statistics.share_count"],
        "author": ["author.nickname"], "author_id": ["author.uid"],
        "time": ["create_time"], "url": ["share_url"],
    },
    "youtube": {
        "list": ["data.items", "data.videos"], "unwrap": [],
        "id": ["video_id", "videoId", "id"], "title": ["title"], "desc": ["description", "title"],
        "liked": ["likeCount", "like_count"], "collected": [],
        "commented": ["commentCount", "comment_count"], "shared": [],
        "author": ["channel.name", "channelTitle", "author"], "author_id": ["channel.id", "channelId"],
        "time": ["publishedTime", "publishedTimeText"], "url_tpl": "https://www.youtube.com/watch?v={id}",
    },
    "toutiao": {
        # 注意：头条搜索返回中文键
        "list": ["data.list", "list"], "unwrap": [],
        "id": ["文章链接", "item_id", "group_id"], "title": ["文章标题", "title", "content"], "desc": ["文章摘要", "content"],
        "liked": ["点赞量"], "collected": ["收藏量"], "commented": ["评论量"], "shared": [],
        "author": ["作者名称", "source"], "author_id": [], "time": ["发表时间"],
        "url": ["文章链接"],
    },
    "twitter": {
        "list": ["data.timeline"], "unwrap": [],
        "id": ["id", "tweet_id", "id_str", "rest_id"], "title": ["text", "full_text"], "desc": ["text"],
        "liked": ["favorites", "favorite_count"], "collected": ["bookmarks"],
        "commented": ["replies", "reply_count"], "shared": ["retweets", "retweet_count"],
        "author": ["screen_name", "user.name"], "author_id": ["user.rest_id", "author.rest_id"],
        "time": ["created_at"], "url_tpl": "https://x.com/i/status/{id}",
    },
    "reddit": {
        "list": ["data.postsInfoByIds"], "unwrap": [],
        "id": ["id"], "title": ["title", "content"], "desc": ["content", "title"],
        "liked": ["score", "upvoteCount"], "collected": [], "commented": ["commentCount"], "shared": [],
        "author": ["authorInfo.name", "author"], "author_id": ["authorInfo.id"],
        "time": ["createdAt"], "url_tpl": "https://www.reddit.com/comments/{id}",
    },
}

USER_SPEC: Dict[str, Dict[str, Any]] = {
    "xiaohongshu": {
        "list": ["data.users"], "unwrap": [],
        "id": ["id", "userid"], "name": ["name", "nickname"], "red_id": ["red_id"],
        "bio": ["desc", "sub_title"], "fans": ["fans", "fans_count"], "notes": ["notes"],
        "liked": ["liked"], "url": ["link"], "avatar": ["image"],
    },
    "douyin": {
        "list": ["data.business_data"], "unwrap": ["data.raw_data", "data.user_info", "data.user"],
        "id": ["uid", "sec_uid"], "name": ["nickname"], "red_id": ["unique_id", "short_id"],
        "bio": ["signature"], "fans": ["follower_count"], "notes": ["aweme_count"],
        "liked": ["total_favorited"], "url": [], "avatar": ["avatar_thumb.url_list.0"],
    },
    "kuaishou": {
        "list": ["data.users"], "unwrap": [],
        "id": ["user_id"], "name": ["user_name"], "red_id": ["kwaiId"],
        "bio": ["user_text"], "fans": ["fan", "fans", "fansCount", "followerCount", "ownerCount"], "notes": [], "liked": [],
        "url": [], "avatar": ["headurl"],
    },
    "weibo": {
        "list": ["data.list", "data.users"], "unwrap": [],
        "id": ["id", "uid"], "name": ["screen_name"], "red_id": ["idstr"],
        "bio": ["description"], "fans": ["followers_count"], "notes": ["statuses_count"],
        "liked": [], "url": ["profile_url"], "avatar": ["profile_image_url"],
    },
    "tiktok": {
        "list": ["data.user_list"], "unwrap": ["user_info"],
        "id": ["uid", "id"], "name": ["nickname", "unique_id"], "red_id": ["unique_id"],
        "bio": ["signature"], "fans": ["follower_count"], "notes": ["aweme_count"],
        "liked": ["total_favorited", "heart_count"], "url": [], "avatar": ["avatar_thumb"],
    },
    "bilibili": {
        "list": [], "unwrap": [],
        "id": ["mid", "uid"], "name": ["name", "uname"], "red_id": [],
        "bio": ["sign", "usign"], "fans": ["fans", "follower"], "notes": [],
        "liked": [], "url_tpl": "https://space.bilibili.com/{id}", "avatar": ["face"],
    },
    "twitter": {
        "list": ["data.timeline"], "unwrap": [],
        "id": ["rest_id", "id_str"], "name": ["name"], "red_id": ["screen_name"],
        "bio": ["desc"], "fans": ["sub_count", "followers_count"], "notes": ["statuses_count"],
        "liked": [], "url_tpl": "https://x.com/{id}", "avatar": ["avatar"],
    },
    "toutiao": {
        "list": [], "unwrap": [],
        "id": ["user_id"], "name": ["name"], "red_id": [],
        "bio": ["description"], "fans": ["followers_count"], "notes": ["publish_count"],
        "liked": ["digg_count"], "url": [], "avatar": ["avatar_url"],
    },
    "youtube": {
        "list": ["data.items"], "unwrap": ["channel"],
        "id": ["id"], "name": ["name", "title"], "red_id": ["handle"],
        "bio": ["description"], "fans": ["subscriberCount", "subscriberCountText"], "notes": [],
        "liked": [], "url_tpl": "https://www.youtube.com/channel/{id}", "avatar": ["avatar"],
    },
}

# 每个平台的操作 -> (路径, 参数映射)
ROUTES: Dict[str, Dict[str, Any]] = {
    "xiaohongshu": {
        "search": ("/api/xiaohongshu/search-note/v2", {"keyword": "keyword", "page": "page"}),
        "search_users": ("/api/xiaohongshu/search-user/v2", {"keyword": "keyword", "page": "page"}),
        "user_info": ("/api/xiaohongshu/get-user/v3", {"user_id": "userId"}),
        "user_posts": ("/api/xiaohongshu/get-user-note-list/v4", {"user_id": "userId", "cursor": "lastCursor"}),
        "detail": ("/api/xiaohongshu/get-note-detail/v6", {"item_id": "noteId"}),
        "comments": ("/api/xiaohongshu/get-note-comment/v2", {"item_id": "noteId", "cursor": "lastCursor", "sort": "sort"}),
    },
    "douyin": {
        "search": ("/api/douyin/search-video/v4", {"keyword": "keyword", "page": "page"}),
        "search_users": ("/api/douyin/search-user/v2", {"keyword": "keyword", "page": "page"}),
        "user_info": ("/api/douyin/get-user-detail/v3", {"user_id": "secUid"}),
        "user_posts": ("/api/douyin/get-user-video-list/v1", {"user_id": "secUid", "cursor": "maxCursor"}),
        "detail": ("/api/douyin/get-video-detail/v2", {"item_id": "videoId"}),
        "comments": ("/api/douyin/get-video-comment/v1", {"item_id": "awemeId", "page": "page"}),
    },
    "kuaishou": {
        "search": ("/api/kuaishou/search-video/v2", {"keyword": "keyword", "page": "page"}),
        "search_users": ("/api/kuaishou/search-user/v2", {"keyword": "keyword", "page": "page"}),
        "user_info": ("/api/kuaishou/get-user-detail/v1", {"user_id": "userId"}),
        "user_posts": ("/api/kuaishou/get-user-video-list/v2", {"user_id": "userId", "cursor": "pcursor"}),
        "detail": ("/api/kuaishou/get-video-detail/v2", {"item_id": "videoId"}),
        "comments": ("/api/kuaishou/get-video-comment/v1", {"item_id": "videoId", "cursor": "pcursor"}),
    },
    "weibo": {
        "search": ("/api/weibo/search-all/v2", {"keyword": "q", "page": "page"}),
        "search_users": ("/api/weibo/search-profile/v1", {"keyword": "q", "page": "page"}),
        "user_info": ("/api/weibo/get-user-detail/v3", {"user_id": "uid"}),
        "user_posts": ("/api/weibo/get-user-post/v1", {"user_id": "uid", "page": "page"}),
        "detail": ("/api/weibo/get-weibo-detail/v1", {"item_id": "id"}),
        "comments": ("/api/weibo/get-post-comments/v1", {"item_id": "mid"}),
    },
    "bilibili": {
        "search": ("/api/bilibili/search-video/v2", {"keyword": "keyword", "page": "page"}),
        "user_info": ("/api/bilibili/get-user-detail/v2", {"user_id": "uid"}),
        "user_posts": ("/api/bilibili/get-user-video-list/v2", {"user_id": "uid", "page": "param"}),
        "detail": ("/api/bilibili/get-video-detail/v2", {"item_id": "bvid"}),
        "comments": ("/api/bilibili/get-video-comment/v2", {"item_id": "aid"}),
        "captions": ("/api/bilibili/get-video-caption/v2", {"item_id": "bvid"}),
    },
    "tiktok": {
        "search": ("/api/tiktok/search-post/v1", {"keyword": "keyword", "cursor": "offset"}),
        "search_users": ("/api/tiktok/search-user/v1", {"keyword": "keyword", "cursor": "cursor"}),
        "user_info": ("/api/tiktok/get-user-detail/v1", {"user_id": "secUid"}),
        "user_posts": ("/api/tiktok/get-user-post/v1", {"user_id": "secUid", "cursor": "cursor"}),
        "detail": ("/api/tiktok/get-post-detail/v1", {"item_id": "postId"}),
        "comments": ("/api/tiktok/get-post-comment/v1", {"item_id": "awemeId", "cursor": "cursor"}),
    },
    "youtube": {
        "search": ("/api/youtube/search/v1", {"keyword": "keyword", "cursor": "nextToken"}),
        "user_posts": ("/api/youtube/get-channel-videos/v1", {"user_id": "channelId", "cursor": "cursor"}),
        "detail": ("/api/youtube/get-video-detail/v1", {"item_id": "videoId"}),
        "comments": ("/api/youtube/get-video-comment/v1", {"item_id": "videoId", "cursor": "cursor"}),
        "captions": ("/api/youtube/get-video-captions/v1", {"item_id": "videoId"}),
    },
    "reddit": {
        "search": ("/api/reddit/search/v1", {"keyword": "keyword", "cursor": "after"}),
        "detail": ("/api/reddit/get-post-detail/v1", {"item_id": "postId"}),
        "comments": ("/api/reddit/get-post-comments/v1", {"item_id": "postId"}),
    },
    "toutiao": {
        "search": ("/api/toutiao/search/v2", {"keyword": "keyword"}),
        "user_info": ("/api/toutiao/get-user-detail/v1", {"user_id": "userId"}),
        "detail": ("/api/toutiao/get-article-detail/v1", {"item_id": "id"}),
    },
    "twitter": {
        "search": ("/api/twitter/search/v1", {"keyword": "keyword", "cursor": "cursor"}),
        "user_info": ("/api/twitter/get-user-detail/v1", {"user_id": "restId"}),
        "user_posts": ("/api/twitter/get-user-posts/v1", {"user_id": "restId", "cursor": "cursor"}),
        "detail": ("/api/twitter/get-post-detail/v1", {"item_id": "tweetId"}),
        "comments": ("/api/twitter/get-post-comments/v1", {"item_id": "tweetId", "cursor": "cursor"}),
    },
    "weixin": {
        "search": ("/api/weixin/search-article/v2", {"keyword": "keyword", "page": "page"}),
        "user_info": ("/api/weixin/search-account/v2", {"keyword": "keyword"}),
        "user_posts": ("/api/weixin/get-account-history-articles/v2", {"user_id": "accountId", "page": "page"}),
        "detail": ("/api/weixin/get-article-detail/v5", {"url": "articleUrl"}),
        "metrics": ("/api/weixin/get-article-metrics/v2", {"url": "articleUrl"}),
    },
    "weixin_channels": {
        "search": ("/api/weixin-channels/search-video/v2", {"keyword": "keyword"}),
        "search_users": ("/api/weixin-channels/search-account/v3", {"keyword": "keyword"}),
        "user_posts": ("/api/weixin-channels/get-account-videos/v1", {"user_id": "finderId"}),
        "detail": ("/api/weixin-channels/get-video-basic-info/v1", {"item_id": "feedInfo"}),
        "comments": ("/api/weixin-channels/get-video-comment/v1", {"item_id": "videoId"}),
    },
}

COMMENT_SPEC = {
    "xiaohongshu": {"list": ["data.comments"], "text": ["content"], "liked": ["like_count"], "author": ["user.nickname"], "replies": ["sub_comment_count"]},
    "douyin": {"list": ["data.comments"], "text": ["text"], "liked": ["digg_count"], "author": ["user.nickname"], "replies": ["reply_comment_total"]},
    "kuaishou": {"list": ["data.rootComments"], "text": ["content"], "liked": ["likeCount", "likedCount"], "author": ["author_name", "authorName"], "replies": ["subCommentCount"]},
    "weibo": {"list": ["data.data", "data.rootComment"], "text": ["text"], "liked": ["like_counts", "likeCount"], "author": ["user.screen_name", "screen_name"], "replies": ["total_number"]},
    "bilibili": {"list": ["data.replies"], "text": ["content.message"], "liked": ["like"], "author": ["member.uname"], "replies": ["rcount"]},
    "tiktok": {"list": ["data.comments"], "text": ["text"], "liked": ["digg_count"], "author": ["user.nickname"], "replies": ["reply_comment_total"]},
    "youtube": {"list": ["data.comments"], "text": ["content", "text"], "liked": ["like_count", "likeCount"], "author": ["author.display_name", "author.name", "author"], "replies": ["reply_count", "replyCount"]},
    "reddit": {"list": ["data.postInfoById.commentForest.trees", "data.postInfoById.commentForest", "data.postsInfoByIds"], "text": ["body", "content"], "liked": ["score"], "author": ["authorInfo.name", "author"], "replies": ["replyCount"]},
    "twitter": {"list": ["data.timeline"], "text": ["text", "full_text"], "liked": ["favorites", "favorite_count"], "author": ["screen_name", "user.name"], "replies": ["replies", "reply_count"]},
    "weixin_channels": {"list": ["data.comments"], "text": ["content"], "liked": ["likeCount"], "author": ["nickname"], "replies": []},
}

# 某些操作的内容数组不在 NOTE_SPEC 默认位置
LIST_OVERRIDE = {
    ("xiaohongshu", "user_posts"): ["data.notes"],
    ("bilibili", "user_posts"): ["data.item", "data.data.item"],
    ("weibo", "user_posts"): ["data.list"],
    ("twitter", "search"): ["data.timeline"],
}


def user_block(plat: str, payload: Any) -> Any:
    if plat == "kuaishou":
        up = path_get(payload, "data.userProfile") or {}
        prof = dict(up.get("profile") or {})
        prof.update(up.get("ownerCount") or {})
        if prof:
            return prof
    """各平台用户对象所在位置不同，按优先级取第一个 dict。"""
    cands = [
        "data.space.info", "data.userInfo.user", "data.user", "data.common.userInfo",
        "data.data", "data.userProfile.profile", "data.profile", "data", "user",
    ]
    if plat == "tiktok":
        ui = path_get(payload, "data.userInfo") or {}
        merged = dict(ui.get("user") or {})
        merged.update(ui.get("stats") or {})
        if merged:
            return merged
    for c in cands:
        v = maybe_json(path_get(payload, c))
        if isinstance(v, dict) and v:
            inner = v.get("user_info") if "user_info" in v else None
            return inner if isinstance(inner, dict) and inner else v
    return unwrap_envelope(payload) if isinstance(unwrap_envelope(payload), dict) else {}


def detail_block(plat: str, payload: Any) -> Any:
    """详情对象所在位置不同，按平台取。"""
    special = {
        "tiktok": ["data.itemInfo.itemStruct"],
        "douyin": ["data.aweme_detail"],
        "weibo": ["data.status"],
        "kuaishou": ["data.photos[0]", "data"],
        "reddit": ["data.postsInfoByIds[0]"],
        "toutiao": ["data.data", "data"],
        "bilibili": ["data.videoData"],
    }
    for c in special.get(plat, []):
        v = path_get(payload, c)
        if isinstance(v, dict) and v:
            return v
    v = path_get(payload, "data")
    if isinstance(v, list):
        return v[0] if v and isinstance(v[0], dict) else {}
    if isinstance(v, dict):
        return v
    return {}


# ---------------------------------------------------------------- 归一化

def _locate_list(payload: Any, paths: Sequence[str]) -> List[Any]:
    roots = [payload, unwrap_envelope(payload)]
    for p in paths:
        for r in roots:
            v = path_get(r, p)
            if isinstance(v, list) and v:
                return v
    for r in roots:
        cand = find_largest_list(r)
        if cand:
            return cand
    return []


def _unwrap(item: Any, keys: Sequence[str]) -> Any:
    for k in keys or ():
        v = maybe_json(path_get(item, k))
        if isinstance(v, dict) and v:
            inner = v.get("user_info")
            return inner if isinstance(inner, dict) and inner else v
    return item


def norm_note(item: Any, platform: str) -> Dict[str, Any]:
    spec = NOTE_SPEC.get(platform, {})
    it = _unwrap(item, spec.get("unwrap", []))
    nid = str(pick(it, *spec.get("id", []), default="") or "")
    url = first_text(it, *spec.get("url", []))
    if not url and spec.get("url_tpl") and nid:
        url = spec["url_tpl"].format(id=nid)
    tags_raw = pick(it, *spec.get("tags", []), default=[])
    tags: List[str] = []
    if isinstance(tags_raw, list):
        for t in tags_raw[:10]:
            if isinstance(t, dict):
                v = pick(t, "name", "tag_name", "hashtag_name", "cha_name")
                if v:
                    tags.append(str(v))
            elif isinstance(t, str):
                tags.append(t)
    return {
        "id": nid,
        "title": first_text(it, *spec.get("title", [])),
        "url": url,
        "content_type": first_text(it, "type", "note_type", "content_type"),
        "author": {
            "id": str(pick(it, *spec.get("author_id", []), default="") or ""),
            "name": first_text(it, *spec.get("author", [])),
        },
        "metrics": {
            "liked": to_int(pick(it, *spec.get("liked", []), default=0)),
            "collected": to_int(pick(it, *spec.get("collected", []), default=0)),
            "commented": to_int(pick(it, *spec.get("commented", []), default=0)),
            "shared": to_int(pick(it, *spec.get("shared", []), default=0)),
        },
        "tags": tags,
        "summary": first_text(it, *spec.get("desc", [])),
    }


def norm_user(item: Any, platform: str) -> Dict[str, Any]:
    spec = USER_SPEC.get(platform, {})
    it = _unwrap(item, spec.get("unwrap", []))
    uid = str(pick(it, *spec.get("id", []), default="") or "")
    url = first_text(it, *spec.get("url", []))
    if not url and spec.get("url_tpl") and uid:
        url = spec["url_tpl"].format(id=uid)
    return {
        "id": uid,
        "name": first_text(it, *spec.get("name", [])),
        "red_id": first_text(it, *spec.get("red_id", [])),
        "url": url,
        "bio": first_text(it, *spec.get("bio", [])),
        "bio_preview": first_text(it, *spec.get("bio", []))[:80],
        "stats": {
            "fans": to_int(pick(it, *spec.get("fans", []), default=0)),
            "notes": to_int(pick(it, *spec.get("notes", []), default=0)),
            "liked": to_int(pick(it, *spec.get("liked", []), default=0)),
        },
    }


def norm_comments(payload: Any, platform: str) -> List[Dict[str, Any]]:
    spec = COMMENT_SPEC.get(platform, {})
    rows = _locate_list(payload, spec.get("list", []))
    out = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        out.append({
            "text": first_text(r, *spec.get("text", [])),
            "liked": to_int(pick(r, *spec.get("liked", []), default=0)),
            "author": {"name": first_text(r, *spec.get("author", []))},
            "reply_count": to_int(pick(r, *spec.get("replies", []), default=0)),
        })
    return out


def _fallback_items(payload: Any, plat: str) -> List[Dict[str, Any]]:
    """字段表没命中时的兜底：用紧凑视图兜住，别让调用方拿到空列表。"""
    view = compact_view(payload)
    arrays = view.get("content_arrays") or []
    if not arrays:
        return []
    rows = arrays[0].get("items") or []
    out = []
    for i, r in enumerate(rows, 1):
        title = ""
        for k in ("title", "desc", "content", "text", "caption", "name"):
            if isinstance(r.get(k), str) and r[k].strip():
                title = r[k]
                break
        out.append({
            "id": str(r.get("id") or r.get("note_id") or r.get("aweme_id") or f"row-{i}"),
            "title": title or f"(未映射字段 #{i})",
            "url": "",
            "content_type": "",
            "author": {"id": "", "name": str(r.get("author.nickname") or r.get("user.nickname") or "")},
            "metrics": {"liked": 0, "collected": 0, "commented": 0, "shared": 0},
            "tags": [],
            "summary": json.dumps(r, ensure_ascii=False)[:200],
        })
    return out



def find_image_urls(payload: Any, limit: int = 12) -> List[str]:
    """从详情里抽正文图片链接。"""
    out: List[str] = []
    def walk(node, depth=0):
        if depth > 6 or len(out) >= limit:
            return
        if isinstance(node, dict):
            for k, v in node.items():
                if k in ("url_default", "urlPre", "url", "master_url") and isinstance(v, str) \
                   and v.startswith("http") and any(x in v for x in (".jpg", ".jpeg", ".webp", ".png", "ci.xiaohongshu")):
                    if v not in out:
                        out.append(v)
                else:
                    walk(v, depth + 1)
        elif isinstance(node, list):
            for v in node[:8]:
                walk(v, depth + 1)
    walk(payload)
    return out[:limit]


VIDEO_KEYS = ("master_url", "masterUrl", "play_url", "playUrl", "video_url", "videoUrl")


def find_video_url(payload: Any, depth: int = 0) -> str:
    """在任意嵌套里找可下载的视频直链。"""
    if depth > 8:
        return ""
    if isinstance(payload, dict):
        for k, v in payload.items():
            if k in VIDEO_KEYS and isinstance(v, str) and v.startswith("http"):
                return v
            got = find_video_url(v, depth + 1)
            if got:
                return got
    elif isinstance(payload, list):
        for v in payload[:8]:
            got = find_video_url(v, depth + 1)
            if got:
                return got
    elif isinstance(payload, str):
        if payload.startswith("http") and (".mp4" in payload or "/play/" in payload):
            return payload
    return ""


# ---------------------------------------------------------------- 后端

class JustOneBackend(Backend):
    def __init__(self) -> None:
        token = os.environ.get("JUSTONEAPI_TOKEN", "").strip()
        self.token = "" if token.startswith("__") else token

    # ---- 传输 ----
    def _call(self, path: str, params: Dict[str, Any]) -> Any:
        if not self.token:
            raise JustOneError("缺少 JUSTONEAPI_TOKEN：设置环境变量后重启本地服务（目录类能力不需要它）。")
        query = {"token": self.token}
        for k, v in params.items():
            if v not in (None, ""):
                query[k] = v
        url = f"{BASE_URL}{path}?{urllib.parse.urlencode(query, doseq=True)}"
        req = urllib.request.Request(url, headers={"accept": "application/json"})
        last_error = ""
        for attempt in range(RETRIES + 1):
            try:
                with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                try:
                    body = exc.read().decode("utf-8", "replace")[:200]
                except Exception:  # noqa: BLE001
                    body = ""
                raise JustOneError(f"JustOneAPI HTTP {exc.code}: {body}") from exc
            except urllib.error.URLError as exc:
                raise JustOneError(f"JustOneAPI 网络错误: {exc.reason}") from exc
            code = payload.get("code")
            # 301 采集失败、302 限流：官方文档明确要求重试
            if code in (301, 302) and attempt < RETRIES:
                last_error = str(payload.get("message") or payload.get("reason") or code)
                time.sleep(1.5 * (attempt + 1))
                continue
            break
        else:  # pragma: no cover
            raise JustOneError(f"JustOneAPI 重试 {RETRIES} 次仍失败: {last_error}")
        code = payload.get("code")
        if code not in (0, None):
            msg = payload.get("message") or payload.get("reason") or ""
            raise JustOneError(f"JustOneAPI code={code} {msg}".strip())
        return payload

    def _exec(self, platform: str, op: str, ctx: Dict[str, Any]) -> Any:
        key = PLATFORM_ALIAS.get((platform or "").lower())
        if not key:
            raise JustOneError(f"不支持的平台: {platform!r}")
        spec = ROUTES.get(key, {}).get(op)
        if not spec:
            raise JustOneError(f"平台 {key} 不支持操作 {op}")
        path, mapping = spec
        params = {}
        # 微博关键词搜索强制要求日+小时时间窗，默认取最近 7 天
        if key == "weibo" and op == "search":
            end = _dt.datetime.now()
            start = end - _dt.timedelta(days=int(os.environ.get("JUSTONEAPI_WEIBO_DAYS", "7")))
            params.update({
                "startDay": start.strftime("%Y-%m-%d"), "startHour": start.hour,
                "endDay": end.strftime("%Y-%m-%d"), "endHour": end.hour,
            })
        for sem, field in mapping.items():
            val = ctx.get(sem)
            if val in (None, ""):
                continue
            if field.lower().endswith(("id", "uid", "secuid", "bvid", "aid", "mid", "feedinfo")):
                val = coerce_id(key, val)
            params[field] = val
        return self._call(path, params)

    @staticmethod
    def _wrap(data: Dict[str, Any], payload: Any) -> Dict[str, Any]:
        if RAW:
            data["raw"] = payload
        return data

    # ---- 织造操作 ----
    def search_notes(self, req: Dict[str, Any]) -> Dict[str, Any]:
        plat = PLATFORM_ALIAS.get((req.get("platform") or "xiaohongshu").lower(), "xiaohongshu")
        payload = self._exec(plat, "search", {"keyword": req.get("query"), "page": req.get("page") or 1, "cursor": req.get("cursor")})
        spec = NOTE_SPEC.get(plat, {})
        paths = LIST_OVERRIDE.get((plat, "search"), spec.get("list", []))
        rows = _locate_list(payload, paths)
        items = [norm_note(r, plat) for r in rows]
        if not items or not any(i.get("title") or i.get("id") for i in items):
            items = _fallback_items(payload, plat)
        data = {"platform": plat, "query": req.get("query"), "items": items,
                "page": _page(returned_count=len(items), next_cursor=pick(payload, "data.cursor", "data.next_cursor", "data.has_more"))}
        return self._wrap(data, payload)

    def search_users(self, req: Dict[str, Any]) -> Dict[str, Any]:
        plat = PLATFORM_ALIAS.get((req.get("platform") or "xiaohongshu").lower(), "xiaohongshu")
        payload = self._exec(plat, "search_users", {"keyword": req.get("query"), "page": req.get("page") or 1, "cursor": req.get("cursor")})
        spec = USER_SPEC.get(plat, {})
        rows = _locate_list(payload, spec.get("list", []))
        users = [norm_user(r, plat) for r in rows]
        return self._wrap({"platform": plat, "query": req.get("query"), "users": users,
                           "page": _page(returned_count=len(users))}, payload)

    def user_info(self, req: Dict[str, Any]) -> Dict[str, Any]:
        plat = PLATFORM_ALIAS.get((req.get("platform") or "xiaohongshu").lower(), "xiaohongshu")
        payload = self._exec(plat, "user_info", {"user_id": req.get("user_id") or req.get("url")})
        data_block = user_block(plat, payload)
        user = norm_user(data_block if isinstance(data_block, dict) else {}, plat)

        return self._wrap({"platform": plat, "profile": user, "stats": user["stats"],
                           "bio": user["bio"], "bio_preview": user["bio_preview"]}, payload)

    def user_posted_notes(self, req: Dict[str, Any]) -> Dict[str, Any]:
        plat = PLATFORM_ALIAS.get((req.get("platform") or "xiaohongshu").lower(), "xiaohongshu")
        payload = self._exec(plat, "user_posts", {"user_id": req.get("user_id") or req.get("url"),
                                                  "cursor": req.get("cursor"), "page": req.get("page") or 1})
        spec = NOTE_SPEC.get(plat, {})
        paths = LIST_OVERRIDE.get((plat, "user_posts"), spec.get("list", []))
        rows = _locate_list(payload, paths)
        items = [norm_note(r, plat) for r in rows]
        return self._wrap({"platform": plat, "user": {}, "items": items,
                           "page": _page(returned_count=len(items))}, payload)

    def analyze_user_profile(self, req: Dict[str, Any]) -> Dict[str, Any]:
        plat = PLATFORM_ALIAS.get((req.get("platform") or "xiaohongshu").lower(), "xiaohongshu")
        user_id = req.get("user_id") or req.get("url")
        info = self._exec(plat, "user_info", {"user_id": user_id})
        posts = self._exec(plat, "user_posts", {"user_id": user_id, "page": 1})
        spec = NOTE_SPEC.get(plat, {})
        items = [norm_note(r, plat) for r in _locate_list(posts, spec.get("list", []))]
        block = user_block(plat, info)
        user = norm_user(block if isinstance(block, dict) else {}, plat)
        insights = self._insights(plat, coerce_id(plat, user_id))
        data = {
            "platform": plat,
            "user": {"id": user["id"], "nickname": user["name"], "fans": user["stats"]["fans"]},
            "page": _page(returned_count=len(items), full_page=False),
            "items": items,
            "artifacts": {"subtitle_markdown": {"status": "unsupported"}},
            "warnings": [],
            "profile_insights": insights,
        }
        return self._wrap(data, {"info": info, "posts": posts})

    def _insights(self, plat: str, user_id: Any) -> Dict[str, Any]:
        """用蒲公英/星图补织造缺的 profile_insights。失败不影响主流程。"""
        out: Dict[str, Any] = {}
        if os.environ.get("JUSTONE_DISABLE_INSIGHTS", "").lower() in {"1", "true"}:
            return out
        try:
            if plat == "xiaohongshu" and user_id:
                sim = self._call("/api/xiaohongshu-pgy/api/solar/kol/get_similar_kol/v1", {"userId": user_id, "pageNum": 1})
                rows = path_get(sim, "data.kols") or []
                if rows:
                    out["similar_creators"] = {"status": "ready", "items": [
                        {"id": str(pick(r, "userId", "id", default="")), "name": first_text(r, "name", "nickname"),
                         "fans": to_int(pick(r, "fansCount", "fans", default=0)),
                         "similarity": pick(r, "similarity", "score"), "tags": pick(r, "tags", default=[]),
                         "recommend_reasons": []} for r in rows[:5] if isinstance(r, dict)]}
                tags = self._call("/api/xiaohongshu-pgy/api/solar/kol/dataV2/kolContentTags/v1", {"userId": user_id})
                tag_rows = tags.get("data") if isinstance(tags.get("data"), list) else []
                if tag_rows:
                    out["content_hot_keywords"] = {"status": "ready", "items": [
                        {"text": str(pick(t, "tagName", "name", default="")),
                         "score": pick(t, "score"), "rank": i + 1, "category": pick(t, "tagType", default="")}
                        for i, t in enumerate(tag_rows[:8]) if isinstance(t, dict)]}
            elif plat == "douyin" and user_id:
                # 星图用独立 star_id 体系，与抖音 sec_uid 不互通；必须显式提供
                star_id = os.environ.get("JUSTONE_STAR_ID", "").strip()
                if not star_id:
                    out["_note"] = "星图洞察需要 star_id（JUSTONE_STAR_ID），抖音 sec_uid 不可直接使用"
                    return out
                kw = self._call("/api/douyin-xingtu/get-author-content-hot-keywords/v1", {"kolId": star_id})
                words = path_get(kw, "keyword_map") or {}
                if isinstance(words, dict) and words:
                    out["content_hot_keywords"] = {"status": "ready", "items": [
                        {"text": str(k), "score": None, "rank": i + 1, "category": ""}
                        for i, k in enumerate(list(words.keys())[:8])]}
        except JustOneError:
            pass
        return out

    def note_detail(self, req: Dict[str, Any]) -> Dict[str, Any]:
        plat = PLATFORM_ALIAS.get((req.get("platform") or "xiaohongshu").lower(), "xiaohongshu")
        payload = self._exec(plat, "detail", {"item_id": req.get("note_id") or req.get("url")})
        block = detail_block(plat, payload)
        item = norm_note(block if isinstance(block, dict) else {}, plat)
        item["text"] = first_text(block if isinstance(block, dict) else {}, "desc", "content", "text", "summary")
        item["video_url"] = find_video_url(block)
        item["images"] = find_image_urls(block)
        return self._wrap({"platform": plat, "item": item}, payload)

    def note_comments(self, req: Dict[str, Any]) -> Dict[str, Any]:
        plat = PLATFORM_ALIAS.get((req.get("platform") or "xiaohongshu").lower(), "xiaohongshu")
        payload = self._exec(plat, "comments", {"item_id": req.get("note_id") or req.get("url"),
                                               "cursor": req.get("cursor"), "sort": req.get("sort")})
        comments = norm_comments(payload, plat)
        return self._wrap({"comments": comments, "page": _page(returned_count=len(comments))}, payload)

    # ---- 公众号 ----
    def article_detail(self, req: Dict[str, Any]) -> Dict[str, Any]:
        payload = self._exec("weixin", "detail", {"url": req.get("url")})
        block = payload.get("data")
        if isinstance(block, list):
            block = block[0] if block else {}
        article = {
            "title": first_text(block, "title"),
            "digest": first_text(block, "summary", "digest"),
            "content_text": first_text(block, "content", "content_text", "text"),
            "url": req.get("url", ""),
            "account_name": first_text(block, "wx_name"),
        }
        return self._wrap({"article": article}, payload)

    def article_stats(self, req: Dict[str, Any]) -> Dict[str, Any]:
        payload = self._exec("weixin", "metrics", {"url": req.get("url")})
        block = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        metrics = {
            "read": to_int(pick(block, "read_num", "read", "readCount", default=0)),
            "liked": to_int(pick(block, "like_num", "liked", "likeCount", default=0)),
            "shared": to_int(pick(block, "share_num", "shared", "forward_num", default=0)),
        }
        return self._wrap({"metrics": metrics}, payload)

    def related_articles(self, req: Dict[str, Any]) -> Dict[str, Any]:
        return {"articles": [], "page": _page()}

    # ---- 字幕 / 生图 ----
    def extract_video_copy(self, req: Dict[str, Any]) -> Dict[str, Any]:
        """字幕优先；没有原生字幕的平台，退回「给视频直链 + 交多模态转录」。"""
        plat = PLATFORM_ALIAS.get((req.get("platform") or "youtube").lower(), "youtube")
        item_id = req.get("note_id") or req.get("url")
        try:
            payload = self._exec(plat, "captions", {"item_id": item_id})
        except JustOneError:
            payload = None
        if payload is not None:
            text = ""
            block = payload.get("data")
            if isinstance(block, list) and block and isinstance(block[0], dict):
                text = first_text(block[0], "subtitle", "content", "text")
            elif isinstance(block, dict):
                text = first_text(block, "content", "text", "subtitle")
            if text:
                return {"batch": {"id": "justone-captions", "status": "completed"}, "replayed": False,
                        "items": [{"url": req.get("url", ""), "status": "ready",
                                   "content": text, "subtitle": text, "format": "text"}]}
        # 回退：取视频直链，交给多模态模型转写
        try:
            detail = self._exec(plat, "detail", {"item_id": item_id})
        except JustOneError as exc:
            return {"batch": {"id": "justone-video", "status": "failed"}, "replayed": False,
                    "items": [{"status": "error", "error_code": "VIDEO_URL_UNAVAILABLE",
                               "message": str(exc)}]}
        video_url = find_video_url(detail)
        note = "已取到视频直链：先下载到本地，再让多模态模型看完视频后生成逐字稿（平台无原生字幕）。"
        return {
            "batch": {"id": "justone-video", "status": "completed" if video_url else "failed"},
            "replayed": False,
            "message": note,
            "items": [{
                "url": video_url or "",
                "origin_url": req.get("url", ""),
                "status": "needs_transcription" if video_url else "error",
                "error_code": "" if video_url else "VIDEO_URL_NOT_FOUND",
                "message": note if video_url else "详情里没有找到可下载的视频地址",
                "content": (
                    "视频直链（临时地址，通常几小时内失效，拿到就下载）：\n" + video_url
                ) if video_url else "这条详情里没有可下载的视频地址（可能是图文笔记）。",
                "subtitle": "", "format": "video",
            }],
        }
        text = ""
        block = payload.get("data")
        if isinstance(block, list) and block and isinstance(block[0], dict):
            text = first_text(block[0], "subtitle", "content", "text")
        elif isinstance(block, dict):
            text = first_text(block, "content", "text", "subtitle")
        return {"batch": {"id": "justone-captions", "status": "completed"}, "replayed": False,
                "items": [{"url": req.get("url", ""), "status": "ready" if text else "empty",
                           "content": text, "subtitle": text, "format": "text"}]}

    def generate_image(self, req: Dict[str, Any], files: Any = None) -> Dict[str, Any]:
        return {"type": "generate-image", "status": "failed", "pending_count": 0,
                "items": [{"status": "error", "error_code": "IMAGE_BACKEND_NOT_CONFIGURED",
                           "message": "JustOneAPI 不提供生图，请接你自己的生图服务"}]}
