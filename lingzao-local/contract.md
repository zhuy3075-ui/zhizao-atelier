# 织造 Skill 本地后端契约

织造 CLI（`scripts/lingzao_client.py`）只是一层薄 RPC：把参数 POST 给你的服务，
拿到 JSON，本地渲染成 Markdown。**所以只要你的服务返回同样的 JSON 形状，全部 40 个
playbook 无需任何修改就能工作。**

- 传输：HTTP/1.1，`Content-Type: application/json`
- 认证：`Authorization: Bearer <api_key>`（本地可忽略，但必须接受，否则不会 401）
- Base URL：`LINGZAO_BASE_URL`（或 `--base-url`），末尾不要带 `/`
- 所有成功响应统一为 `{"ok": true, "data": {...}}`
- 失败响应：`{"ok": false, "error": {"code": "...", "message": "..."}}` + 非 2xx

> 关键：渲染层用 `as_dict()` / `as_list()` 做防御性取值，**字段缺失不会崩，只会显示 `-`**。
> 所以可以先返回最小可用形状跑通，再逐字段补全质量。

---

## 0. 健康检查

### `GET /api/v1/me`

`doctor` 用。不消耗额度。

```json
{
  "ok": true,
  "user": { "id": "local-user", "name": "local", "email": "" },
  "api_key": { "key_prefix": "lgz_local" }
}
```

---

## 1. `POST /api/v1/research/search-notes`

请求：

| 字段 | 类型 | 说明 |
|---|---|---|
| `platform` | string | `xiaohongshu` / `douyin` / `tiktok` / `instagram` / `youtube` / `wechat_channels` |
| `query` | string | 关键词 |
| `limit` | int | 条数 |
| `cursor` | string? | 分页游标，原样回传 |
| `sort` | string? | 排序 |
| `note_type` | string? | 内容类型过滤 |
| `time_filter` | string? | 时间范围 |

响应：

```json
{
  "ok": true,
  "data": {
    "platform": "xiaohongshu",
    "query": "通勤穿搭",
    "items": [
      {
        "id": "note_id",
        "title": "标题",
        "url": "https://...",
        "content_type": "video",
        "xhs_note_type": "video",
        "author": { "id": "u1", "name": "作者名" },
        "metrics": { "liked": 1200, "collected": 300, "commented": 88, "shared": 12 },
        "tags": ["标签1", "标签2"],
        "summary": "摘要"
      }
    ],
    "page": { "next_cursor": null, "limit": 20, "returned_count": 1 }
  }
}
```

> `metrics` 四个键名固定为 `liked / collected / commented / shared`，渲染层直接读。

---

## 2. `POST /api/v1/research/search-users`

请求：`platform`, `query`, `limit`, `cursor`

响应 `data`：`platform`, `query`, `users[]`, `page{}`

`users[]` 单项（渲染层兼容多个别名）：

```json
{
  "id": "u1",
  "name": "账号名",
  "red_id": "小红书号（也可用 redId / handle）",
  "url": "https://...",
  "bio": "完整简介",
  "bio_preview": "简介摘要",
  "stats": { "fans": 12000, "notes": 88, "liked": 50000 }
}
```

---

## 3. `POST /api/v1/research/get-user-info`

请求：`platform`, `url` 或 `user_id`

响应 `data`：`platform`, `profile{...}`, `stats{fans,notes,liked}`, `bio`, `bio_preview`

---

## 4. `POST /api/v1/research/get-user-posted-notes`

请求：`platform`, `url` 或 `user_id`, `limit`, `cursor`

响应 `data`：`platform`, `user{}`, `items[]`（同 search-notes 的 item 形状）, `page{}`, `notice?`

---

## 5. `POST /api/v1/research/analyze-user-profile`

请求：`platform`, `url` 或 `user_id`, `limit`, `force_new`, `full_page`, `cursor`

响应 `data`：

```json
{
  "platform": "xiaohongshu",
  "user": { "id": "u1", "nickname": "账号名" },
  "page": { "returned_count": 20, "limit": 20, "next_cursor": null, "full_page": false },
  "items": [ { "...": "同 item 形状，可带 metrics/media/text/subtitle/monetization/collaboration/commerce_note" } ],
  "artifacts": {
    "subtitle_markdown": { "status": "ready", "url": "https://.../subs.md" }
  },
  "profile_insights": {
    "content_hot_keywords": {
      "status": "ready",
      "items": [ { "text": "热词", "score": 0.91, "rank": 1, "category": "品类" } ]
    },
    "similar_creators": {
      "status": "ready",
      "items": [ {
        "id": "u2", "name": "相似账号", "fans": 30000,
        "expected_play_count": 8000, "similarity": 0.87,
        "tags": ["tag"], "recommend_reasons": ["原因"]
      } ]
    }
  },
  "warnings": []
}
```

`subtitle_markdown.status` 取值：`ready` / `unsupported` / 其他（`unavailable` 等）。
`unsupported` 表示该平台主页不产字幕，需改用 `extract-video-copy`。

---

## 6. `POST /api/v1/research/get-note-detail`

请求：`platform`, `url` 或 `note_id`, `xhs_note_type`, `content_type`

响应 `data`：`platform`, `item{...}`（完整正文、图片、指标、标签）

---

## 7. `POST /api/v1/research/get-note-comments`

请求：`platform`, `url` 或 `note_id`, `cursor`, `limit`, `sort`

响应 `data`：`comments[]`, `page{}`, `author?`

```json
{ "comments": [ { "text": "评论", "liked": 12, "author": { "name": "用户" }, "created_at": "..." } ] }
```

---

## 8. `POST /api/v1/research/get-article-detail`

请求：`platform`, `url`（必填）

响应 `data`：`article{ title, digest, content_text }`

> `--output <path>` 时由 CLI 本地落盘，服务端不用关心。

---

## 9. `POST /api/v1/research/get-article-stats`

请求：`platform`, `url`

响应 `data`：`metrics{ read, liked, shared, ... }`

---

## 10. `POST /api/v1/research/get-related-articles`

请求：`platform`, `url`

响应 `data`：`articles[]`, `page{}`

---

## 11. `POST /api/v1/research/extract-video-copy`

请求：`url` 或 `note_id`, `platform`

响应 `data`：

```json
{
  "batch": { "id": "b1", "status": "completed" },
  "replayed": false,
  "items": [ { "url": "...", "status": "ready", "content": "口播全文", "subtitle": "...", "format": "text" } ]
}
```

失败单项可带 `error_code` / `message` / `retryable` / `billing_effect` / `agent_action`。

---

## 12. `POST /api/v1/research/generate-image`

请求 JSON：`prompt`, `count` 等；带参考图时改用 multipart（字段 + `images` 文件）。

响应必须满足四点，否则 CLI 认为还在排队、失败或缺图：

```json
{
  "ok": true,
  "data": {
    "type": "generate-image",
    "status": "completed",
    "pending_count": 0,
    "batch_id": "b1",
    "requested_count": 1,
    "succeeded_count": 1,
    "size": "1024x1024",
    "output_format": "png",
    "image": {
      "b64_json": "<图片的 base64>",
      "mime_type": "image/png",
      "sha256": "<可选，仅用于回显>"
    }
  }
}
```

- `type` 必须等于 `"generate-image"`
- `status` ∈ `completed` / `failed` / `partial`（`partial` 时 `pending_count` 必须为 0）
- **图片以 base64 放在 `image.b64_json`**（多图放 `images: [{"index": 0, "image": {...}}]`）。
  客户端**不下载 URL**，只解码 base64 落盘——这点和直觉相反，容易踩坑。
- 至少一项有 `image` 对象，否则抛 `no generated image data`

> 如果你们的生图服务只给 URL，本地后端里自己 `requests.get` 下载再 base64 编码即可，
> 不要让 CLI 去下载。

---

## 最小可用实现顺序

1. `GET /api/v1/me` → 让 `lingzao doctor` 通过
2. `search-notes` + `get-note-detail` → 覆盖 60% 的 playbook（对标发现、爆款拆解、选题）
3. `get-note-comments` → 补上“评论需求缺口”，这是拆解质量的关键
4. `analyze-user-profile` → 账号诊断和横向对比
5. `extract-video-copy` / `generate-image` → 按需
