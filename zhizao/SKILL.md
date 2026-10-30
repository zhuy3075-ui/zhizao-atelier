---
name: zhizao
description: 织造是给 WorkBuddy、OpenClaw、Codex 等 Agent 使用的跨平台创作者研究与自媒体运营 Skill。可做选题、标题、封面、账号诊断、发布检查、复盘，以及公众号对标适配判断和原创写作；查询公开内容、评论、短视频文案、公众号文章数据时走本地数据后端；出图只给可直接复制的提示词。
---

# 织造：跨平台创作者研究与自媒体运营 Skill

织造是一个主 Skill，不需要拆成标题、封面、账号诊断、图片生成等多个 Skill。
安装后，WorkBuddy、OpenClaw、Codex 等 Agent 会先把你的问题路由到合适的
创作者运营 playbook；只有当你需要查询公开内容、读取评论、提取短视频文案、
查看公众号文章数据时，才需要本地数据后端。

数据层完全跑在本机，由 `lingzao-local` 提供：一个本地 HTTP 服务把 JustOneAPI
的采集接口翻译成织造 CLI 认的形状。不依赖任何厂商平台，也不需要联网授权。

## 首次使用：先配一个数据密钥

方法层不需要联网，但一旦要查真实数据（搜笔记、看主页、读评论、拉作品），就需要一个数据源密钥。只配一次。

### 开通只要三步

1. 注册：去 https://dashboard.justoneapi.com/zh/register （注册后有免费调用额度，不用立刻付费）
2. 拿密钥：登录控制台 https://dashboard.justoneapi.com/zh ，找到「API Token / 访问令牌」，整串复制
3. 配上去：把密钥发给 Agent，或者双击「安装织造」重新粘贴一次

### 官方文档

- 使用指南（价格、认证方式、错误码、免费额度说明）：https://docs.justoneapi.com/zh/usage
- 接口文档（每个平台能查什么）：https://docs.justoneapi.com/zh/

### 对话里怎么处理

- 用户第一次要查数据、但明显没配过密钥时，**先要密钥**，并把上面三步和链接完整发一次；同一轮对话不要反复发。
- 用户问"密钥是什么、去哪开"，就按上面三步回答，不要含糊说"你去搞一个"。
- **不要编造密钥**，不要让用户去非官方渠道买，也不要替用户注册。
- 用户说"暂时没有"或"先不配"，**退回纯方法论模式**继续干活（选题、标题、内容包、发布检查、复盘都不需要密钥），不要卡在这里。
- 已经配过、能正常查数据时，不要再提这一段。

## 从这里开始

| 你现在想做 | 可以直接这样问 Agent |
| --- | --- |
| 找内容方向 | “用织造帮我围绕这个关键词做小红书、抖音、TikTok 或 YouTube 选题，给我 10 个可发方向。” |
| 找对标账号 | “帮我找这个赛道值得学习的对标账号，并说明每个账号适合学什么。” |
| 拆一条笔记或视频 | “分析这条内容为什么有效，拆成标题、封面、结构、评论需求和可复用模板。” |
| 改标题和封面 | “基于我的草稿，给我 3 个最强标题和 5 个小红书封面方向。” |
| 做发布前检查 | “发布前帮我检查标题、封面、前 3 行、关键词和用户点击理由。” |
| 做发布后复盘 | “根据这条内容的数据和评论，帮我判断下次要调整什么。” |
| 做每周内容包 | “用织造把我这一周的素材整理成 5 个母题，并分发成小红书、公众号、播客和短口播。” |
| 校准公众号对标 | “我发几篇喜欢的公众号文章和一篇自己的内容，你先判断适不适合我学，不适合再补找对标，然后帮我写成自己的文章。” |
| 做图片素材 | “帮我出 3 张小红书封面的生图提示词，要能直接粘进即梦用。” |
| 保存长结果 | “把这份分析整理成 Word、网页预览或知识库 Markdown 版本。” |

## 不需要数据源就能做

本地后端未启动时，织造仍然可以作为创作者运营路由和 playbook 使用。适合：

- 判断账号定位、赛道难度、内容主线和商业路径。
- 设计小红书标题、封面方向、发布关键词和图文结构。
- 改写草稿、拆解用户已经提供的内容材料、做发布前检查。
- 根据用户提供的数据截图或复盘信息，输出下一步实验建议。
- 把用户提供的一周素材整理成 5 个母题，并规划小红书、公众号、播客、
  短口播、社群和知识库分发。
- 把长分析整理成 Word、网页预览或知识库 Markdown 结构。

## 什么时候需要数据后端

当 Agent 需要实际查询线上公开内容时，走本地数据后端（`lingzao-local`），包括：

- 搜索公开内容和公开创作者：小红书、抖音、快手、微博、B 站、TikTok、YouTube、今日头条、Reddit、微信公众号、视频号。
- 查看创作者主页、近期公开内容、主页深度分析和对标账号证据。
- 打开单条公开内容详情，读取一级公开评论。
- 打开公众号公开文章详情，查看公开文章数据。
- 提取公开短视频字幕（B 站、YouTube 有原生字幕；抖音、小红书、快手需自备转写）。
- 查账号商业数据：小红书蒲公英、抖音巨量星图、腾讯互选（需各自的 id 体系）。
- 产出可直接复制的封面/配图生成提示词（只出提示词，不调用生图接口）。

平台能力差异见下方「平台能力矩阵」，不支持的操作要直接说明，不要换词重试。

用户已给出明确任务且属于小范围时，直接执行；首轮最多做 5 次外部查询。
如果需要扩大关键词、账号、内容详情、评论分页、文案提取或提示词数量，说明新增的业务范围并请用户确认配额消耗。

## 调用公开数据工具前（平台能力矩阵）

数据由本地后端转发到 JustOneAPI，**支持以下平台**。先查矩阵再决定怎么问，不要假装支持。

| 平台 | `--platform` | 关键词搜索 | 内容详情 | 评论 | 主页资料 | 作品列表 | 字幕 |
|---|---|---|---|---|---|---|---|
| 小红书 | `xiaohongshu` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| 抖音 | `douyin` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| 快手 | `kuaishou` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| 微博 | `weibo` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| B 站 | `bilibili` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| TikTok | `tiktok` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| YouTube | `youtube` | ✅ | ✅ | ✅ | ⚠️ 仅频道 | ✅ | ✅ |
| 今日头条 | `toutiao` | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| Reddit | `reddit` | ⚠️ 结构特殊 | ✅ | ✅ | ❌ | ❌ | ❌ |
| 微信公众号 | `weixin` | ✅ 文章 | ✅ 文章 | ✅ | ✅ 账号 | ✅ 历史文章 | — |
| 视频号 | `wechat_channels` | ✅ | ✅ | ✅ | ⚠️ 仅 finder ID | ✅ | ❌ |

**商业数据源**（补账号诊断的深度洞察，只在需要时调用）：

| 数据源 | 用途 | 触发条件 |
|---|---|---|
| 小红书蒲公英 | 相似创作者、内容标签、粉丝画像、笔记表现 | 用户要做「账号诊断 / 横向对比 / 商业价值判断」且平台是小红书 |
| 抖音巨量星图 | 受众分布、内容热词、转化能力 | 需要星图数据时必须显式提供 `JUSTONE_STAR_ID`（星图 id 与抖音 sec_uid 不互通） |
| 腾讯互选 | 视频号/公众号达人商业数据 | 需要商业报价或达人筛选时 |

### 调用规则

- **链接可以直接传**。后端会从 URL 自动抽 ID（小红书 `/explore/<id>`、抖音 `/video/<id>`、B 站 `/video/BV...`、YouTube `?v=`、微博 `/detail/<id>` 等），不需要手工提取。
- 用户只给昵称、账号名或数字 ID 时，不要拼 URL；先用 `search-users` 找，再用返回的 ID 或链接。
- 看内容用详情工具，看评论用评论工具，两者不要混用；主页链接不能当内容链接。
- 单条内容要评论时，先把内容详情拿到 ID，再调评论；不要拿主页 ID 去查评论。
- **微博搜索强制时间窗**（`startDay/startHour/endDay/endHour`），后端默认补最近 7 天，可用 `JUSTONEAPI_WEIBO_DAYS` 调整；不要传空。
- **抖音主页要用 sec_uid**，不是 uid；作品列表返回的 `author.sec_uid` 才是正确值。
- **YouTube 主页只接受 channel ID 或 `/channel/UC...`**，不接受 `@handle`。
- **视频号主页只接受 `search-users` 返回的 finder ID**，不接受主页 URL。
- 平台不支持某个操作时（如头条评论、Reddit 主页），**直接告诉用户不支持**，不要换关键词反复试，也不要编造数据。
- 遇到结构异常、字段取不到（如 Reddit），用 `python query.py --sample` 或后端紧凑视图把原始结构压到几 KB 再判断，不要盲猜字段。
- 返回里出现 `agent_action`、`suggested_capabilities` 或 `expected_input` 时，先按这些字段改调；仍不确定就问用户要链接。

### 成本规则

每次真实查询都计费（按接口和页数），比本地判断贵得多。默认遵守：

1. 先用 playbook 做判断，**不要一上来就搜**。
2. 用户没给数量时，先搜 3 条验证方向，不要默认 20 条。
3. 方向不对就停下问用户改关键词，不要连续换词重搜。
4. 评论、主页深度分析、字幕提取属于「深度查询」，做之前说明会扩大范围。
5. 首轮最多 5 次外部查询，超了先确认。


## 常见问题

**没有数据后端，还能用吗？**
可以。先用织造做选题判断、标题封面、账号诊断、草稿修改、发布检查和复盘。
需要查公开内容、评论、短视频文案或公众号文章数据时，再启动本地数据后端。

**数据从哪来？**
本地后端 `lingzao-local` 转发到 JustOneAPI 的采集接口。token 由使用者自己持有，
写在环境变量 `JUSTONEAPI_TOKEN` 里，不经过任何第三方中转。

**WorkBuddy 用户应该怎么用？**
优先安装这一个 `lingzao` 主 Skill。装好后直接把任务说给 WorkBuddy，例如
“帮我找对标账号”“帮我拆这条笔记”“帮我做发布前检查”。需要查公开数据时，
先按 `lingzao-local/README.md` 启动本地后端。

**织造能保证爆款、涨粉或变现吗？**
不能。织造只做公开内容研究、运营判断和工作流辅助。输出用于帮助你做判断和
复盘，不是保证结果，也不能用于复制他人内容。

**网络或服务失败怎么办？**
先保留当前问题和链接，不要重复扩大查询范围。检查 `doctor`、数据源 token 和
网络状态；图片生成或短视频文案提取这类异步任务可能需要等待轮询完成。
如果本地后端返回服务暂时不可用或响应超时，只用固定话术告诉用户：“数据服务暂时
不可用，请稍后重试。”如果返回了 `error_id`，可以附上 `error_id`，方便后续排查。
如果 CLI 返回了明确的用户可见原因和下一步，保留该指引，不要改写成其他故障，也不要自动重试。

## Agent Playbooks

For higher-level creator strategy tasks, use the playbooks in
`<skill_root>/playbooks/` before answering. They turn the skill's public-content
tools into creator workflows instead of isolated lookups.

## Playbook Routing Contract

Before reading a playbook, read `<skill_root>/playbooks/router-index.json`. Do not scan every playbook or use the long progressive map as an always-on prompt.

Route in this order:

1. Classify `input_shape`: homepage, single content, keyword, draft, image, Brief, metrics, or vague request.
2. Classify `platform`: Xiaohongshu, Douyin, Kuaishou, Weibo, Bilibili, TikTok, YouTube,
   Toutiao, Reddit, WeChat（公众号/视频号）。Instagram 未接入，遇到直接说明不支持。
   If the platform is unclear, do not start with a wide search. First ask or
  state a narrow starter scope: follower range, track/topic, account format,
  city/local scope when relevant, recent-update requirement, recent-hit
  requirement, and starter result count. Recommend starting with 3 accounts,
  then expanding only after the user confirms the direction. This keeps the
  research focused and avoids returning 100-follower seed accounts or huge mature
  accounts when the user asked for a specific stage.
- If the user asks how to write prompts for Zhizao or gives a broad copy-paste
  request, use `copy-paste-prompt-scope-boundary.md` first. Provide a
  ready-to-copy prompt that includes the smallest useful scope instead of
  telling the user to add broad instructions by themselves.
- If the user says they know nothing about self-media, are starting from zero,
  do not know what to post, or only say they want to make money, use
  `zero-beginner-onboarding-gate.md` before any search. Do not call online
  lookup first. Start with a free life-signal intake, give the lowest creator
  cognition, and move them to one concrete first task.
- For `search-notes`, ask one short question only when the platform is missing
  and cannot be inferred. When sorting, note type, or time range is not
  specified, do not ask first: use `general`, `不限`, and `不限` and state those
  defaults in one sentence at the start of the reply. Allowed values:
  sort can be `general`, `most_liked`, `popularity_descending`,
  `comment_descending`, or `collect_descending`; note type can be `不限`,
  `视频笔记`, `图文笔记`, or `直播笔记`; time range can be `不限`, `一天内`,
  `一周内`, or `半年内`.
- Douyin and TikTok `search-notes` currently support only `general`, `most_liked`, and
  `popularity_descending`. Do not pass `comment_descending` or
  `collect_descending` for Douyin or TikTok searches.
- Douyin and TikTok `search-notes` note type currently supports only `不限`, `视频笔记`,
  and `图文笔记`. Do not pass `直播笔记` for Douyin or TikTok searches.
- YouTube `search-notes` supports only `--sort general`, `--note-type 不限|视频笔记`,
  and `--time-filter 不限|一天内|一周内`; use the returned opaque `next_cursor`
  with `--cursor`, repeat the same keyword and filters, and do not infer internal
  pagination fields. Changing a filter invalidates the cursor before another lookup.
- For `get-note-comments`, ask whether the user wants latest comments or
  liked-count sorting before calling Xiaohongshu. Use `--sort latest` for latest
  comments and `--sort most_liked` for Xiaohongshu liked-count sorting.
- Douyin 和 TikTok 的评论目前只支持 `latest`（TikTok 用服务默认排序）。
  不要在这两个平台请求或传 `--sort most_liked`。
- YouTube comments support `latest` and `most_liked`; only top-level comments
  are returned. Reuse `next_cursor` unchanged and repeat the same `--sort` on
  every next-page request; omitting it after `most_liked` defaults to `latest`
  and invalidates the cursor before another lookup.


- For TikTok `search-notes`, `search-users`,
  `get-user-posted-notes`, and
  `get-note-comments`, pass the returned `data.page.next_cursor` unchanged with
  `--cursor` to fetch one next page. Repeat the original search keyword and
  filters, creator, or content item for that cursor; never reuse it for another
  request identity. Never parse the opaque cursor or hide multi-page fanout.
  TikTok 游标如果是 Skill `0.1.92` 之前创建的，已失效：丢弃并从第一页重开。 If Zhizao returns `PAGINATION_CURSOR_STALE`, also discard
  that cursor and restart from the first page; do not loop it.
- Xiaohongshu list-style commands (`search-notes`, `get-user-posted-notes`,
  `analyze-user-profile`) return `xhs_note_type` on each note item when
  Zhizao can identify whether it is 图文 or 视频. When continuing from one of
  those note items to `get-note-detail`, pass the returned value directly as
  `--xhs-note-type`; do not infer the type from the URL. If a Xiaohongshu note
  item has no `xhs_note_type`, use its canonical URL, `/discovery/item/` URL,
  note_id, or short link directly. Content, metrics, and copy need no type;
  request `--xhs-note-type video` only when playback or duration is needed. If
  `get-note-detail` returns `NOTE_NOT_FOUND_OR_INACCESSIBLE`, do not retry the
  same request or probe the other Xiaohongshu type automatically. Ask the user
  to confirm the note is public or provide the original share link.
  `get-note-comments` can still be called without this type.
- Missing search filters use the documented defaults without asking; state the
  defaults used in the reply.

After a successful research command, tell the user the estimated time saved
shown in the CLI Markdown output. If you called multiple Zhizao research
commands for one user request, summarize the total once. Do not show time-saved
language for `doctor`, `check-version`, failed commands, or JSON-only automation
flows.

## 怎么用：用户说人话，你翻译成动作

用户不需要知道任何命令、参数、接口。看到需求，你自己决定调什么。

### 常见说法 → 你要做的

| 用户可能会说 | 你要做的 |
|---|---|
| "帮我看看这个号怎么样" ＋ 主页链接 | 拉主页资料 + 最近作品，做账号拆解 |
| "这条笔记为什么火" ＋ 链接 | 拉详情 + 一页评论，做单条拆解 |
| "帮我找 5 个对标账号" | 先给筛选标准让用户确认，再搜 3 个试方向 |
| "我要做女性成长这个方向" | 走选题 / 内容包 playbook，先不查数据 |
| "帮我起 3 个标题" | 直接给，不需要查任何数据 |
| "这条能不能发" ＋ 草稿 | 走发布前检查，不需要查数据 |
| "发完了数据不好" ＋ 截图 | 走复盘，用用户给的截图，不默认去搜对标 |
| "帮我做张封面" | 输出提示词卡片，**不调用生图** |
| "把这条视频的文案扒出来" | 有字幕的直接取；没有的给视频直链 |
| "这个平台上帮我查一下" | 先看平台能力矩阵，不支持就直接说 |

### 内部调用（用户看不到，你不用解释）

下面是你自己用的，不要把命令念给用户听：

| 要做什么 | 命令 | 关键参数 |
|---|---|---|
| 按关键词搜内容 | `lingzao search-notes` | `--keyword` `--platform`（可选 `--limit`） |
| 搜创作者 | `lingzao search-users` | `--keyword` `--platform` |
| 主页资料（粉丝、简介） | `lingzao get-user-info` | `--url` 或 `--user-id` |
| 主页最近作品 | `lingzao get-user-posted-notes` | `--url` 或 `--user-id` |
| 主页深度分析 | `lingzao analyze-user-profile` | `--url` 或 `--user-id` |
| 单条内容详情 | `lingzao get-note-detail` | `--url` 或 `--note-id` |
| 一级评论 | `lingzao get-note-comments` | `--url` 或 `--note-id`（可选 `--sort`） |
| 公众号文章 | `lingzao get-article-detail` | `--url` |
| 公众号文章数据 | `lingzao get-article-stats` | `--url` |
| 字幕 / 视频直链 | `lingzao extract-video-copy` | `--url` |
| 主页全部视频直链 | `<skill_root>/scripts/video_links.py` | `--platform` `--user` `--limit` `--out` |
| 批量下载视频 | `<skill_root>/scripts/download_videos.ps1` | `-Csv` `-Out`（可选 `-Index`） |

### 视频直链怎么给用户

小红书这类平台，主页列表**只有笔记链接，没有视频文件**。要视频必须逐条查详情：

- 单条：`extract-video-copy --url <笔记链接>`，如果这条没有字幕，返回值里的 `content` 就是视频直链。
- 批量：`python "<skill_root>/scripts/video_links.py" --platform <平台> --user <主页链接或ID> --limit 10 --out links.csv`

**已验证支持视频直链的平台**：小红书、抖音、TikTok。快手接口里有 mp4 但未逐个验证。

各平台传什么 ID：
- 小红书：主页链接或 user_id（自动识别）
- 抖音：**sec_uid**（不是 uid），从作品列表的 `author.sec_uid` 取
- TikTok：**secUid**，从 `search-users` 或作品作者取
- 快手：userId

下载：脚本会生成 CSV，再用 `<skill_root>/scripts/download_videos.ps1 -Csv links.csv -Out <目录>` 批量下。
脚本会自动找本地后端（`LINGZAO_LOCAL_DIR` → 同级 lingzao-local → `~/.lingzao-local`），不用手配路径。

两个必须说清的点：

1. **直链是带签名的临时地址，几小时就失效**，拿到就要下载，不能当长期素材存。
2. **条数就是调用次数**：主页 21 条视频 = 21 次详情调用。用户没说要几条时，先跑 5 条给他看，别默认全量。

三条铁律：

1. **链接直接传**。用户给什么链接就传什么，后端会自己从网址里认出 ID，不要手工截取。
2. **只调必要的**。用户问"这个号怎么样"，不要顺手把 20 条笔记详情全拉了。
3. **失败了就说人话**。"这个平台查不到评论"比抛一段错误码有用。

### 口播逐字稿

分两种情况，别混：

**B 站 / YouTube**：有原生字幕，`extract-video-copy` 直接返回文字。

**抖音 / 小红书 / 快手 / TikTok / 视频号**：没有字幕接口。命令会返回**视频直链**，你要告诉用户：

> 这条没有字幕，我拿到了视频下载地址（可能很快失效）。你可以下载后交给能看视频的 AI，
> 让它逐字转写口播内容。要我帮你把链接整理出来吗？

不要说"已经转写好了"——转写不是你能做的事。

### 做封面和图文：给提示词，不给图

**本 skill 不生成图片。** 用户要图时，你输出一张**可以直接复制去别的工具用**的提示词卡片。

#### 卡片里必须有什么

- **一段可直接粘贴的中文描述**：把下面这些揉成一段完整的话
- 平台和比例
- 风格方向（如"无人物知识卡片"）
- 图上文字：主标题、副标题，**逐字写出**
- 版式结构、配色、字体方向
- 参考图借什么：排版、配色、构图，还是人物风格
- 不要出现什么
- 怎么判断这张图算合格

#### 尺寸参考

| 场景 | 比例 | 建议像素 |
|---|---|---|
| 小红书封面 | 3:4 竖版 | 1242×1660 |
| 小红书内页 | 3:4 竖版 | 1242×1660 |
| 公众号封面 | 2.35:1 横版 | 900×383 |
| 公众号配图 | 16:9 横版 | 1280×720 |
| 知乎 / 头条封面 | 16:9 | 1280×720 |

#### 六条硬要求

1. **图上文字必须逐字给出**。AI 最不会写中文，让模型自己编一定翻车。文字用户定，模型只管画面。
2. **每页只讲一件事**。4 页按"封面 / 问题 / 方法 / 行动"分工；7 页按"封面 / 诊断 / 准备 / 步骤 / 清单 / 行动"分工。
3. **参考图只借结构**。写清借排版、配色还是构图，并明确不抄它的文字、logo 和完全相同构图。
4. **默认带上负面约束**：不要伪造 App 截图、不要编数据或价格、不要紫色渐变、不要图库感背景、不超过 3 级文字层级。
5. **用户只给宽泛主题时先问两个锚点**：有没有参考图、想要什么配色。最多再问一个（平台尺寸 / 图上文字 / 要不要人物）。不要直接给一份泛泛的提示词。
6. **要几张就给几份卡片**，不要用一句"可以生成多张"糊过去。

#### 用户会怎么说

> "帮我做张小红书封面，主题是 30 岁转行" → 先问参考图和配色，再给 1 份卡片

> "参考这张图，给我 3 页图文的提示词" → 3 份卡片，每份写明借它的排版和配色，不抄文字

> "我要一套 4 页图文" → 按封面 / 问题 / 方法 / 行动 出 4 份

## Usage Notes

- For profile and post URLs, pass the URL directly when possible.
- For direct IDs, include `--platform`. For Xiaohongshu follow-up profile checks,
  prefer the 24-character `users[].id` returned by `search-users`; RED ID is
  display metadata only.
- Omit `--limit` unless the user asks for a specific count.
- Search notes default to comprehensive sorting, all note types, and all time; use `--sort`, `--note-type`, and `--time-filter` when the user asks for ranked or filtered note search.
- Use `--format json` only when another tool needs structured output.
- Default output is Markdown for agents to read and summarize.
- If the data-source token needs attention, point the user to `lingzao-local/README.md`.

### 深度主页翻页

小红书深度分析支持 `full_page=true`：每次一整页，首通常22条含置顶，之后通常20条，忽略 limit，每页固定50配额。不传 full_page 或传 false 时按 limit 返回，后续只需传上一页 `page.next_cursor`，1–20条50配额、21–40条100配额。小红书所有 next_cursor 均为签名 cursor，必须原样回传，不解析、不跨博主或能力混用。两个参数都省略时仅 next_cursor 升级为签名格式，其他数据保持原行为；旧缓存也免费返回签名 cursor。不同 full_page/cursor 不复用，完全同参60分钟内复用且不扣费。抖音暂不支持这两个参数（含 false），传入返回400、不扣费；继续省略参数使用原分析。

CLI：`analyze-user-profile --url <主页URL> --full-page`；续页加 `--cursor <next_cursor>`；按 limit 首次直接用 `--limit 20`（也可加 `--no-full-page`），之后用 `--cursor <next_cursor> --limit 20`。
