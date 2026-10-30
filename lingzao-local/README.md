# lingzao-local

用**你自己的采集服务**驱动织造 Skill，不连织造平台。

织造的 40 个 playbook 是纯文本方法论，CLI 只是一层薄 RPC。把 RPC 指到本地，
方法论全部照用，采集和生图换成你自己的实现。

```
你的采集/生图  →  backend.py（映射成织造的 JSON 形状）  →  lingzao CLI  →  40 个 playbook
```

## 快速开始

一条命令装齐 **skill + 数据源 MCP + 两者配置**：

```powershell
cd lingzao-local
.\install.ps1 -Token "你的 JustOneAPI token"   # 省略 -Token 则稍后 setx
```

它会依次：装 skill → 拉取并构建 justoneapi-mcp → 写入 DSH 与 Codex 的 MCP 配置 → 写入 token。
重复运行安全（已存在的项会跳过）。

然后起本地后端：

```powershell
$env:LINGZAO_LOCAL_BACKEND = "justone:JustOneBackend"
python server.py --port 8787

# 另开一个终端
$env:LINGZAO_BASE_URL = "http://127.0.0.1:8787"
$env:LINGZAO_API_KEY  = "lgz_local"
lingzao doctor
```

不想接真实数据源、只想验证链路时，用 mock：

```powershell
.\smoke.ps1        # 13 条命令全跑一遍
```

## 接入你自己的实现

1. 新建 `my_backend.py`：

```python
from backend import Backend

class MyBackend(Backend):
    def search_notes(self, req):
        rows = my_crawler.search(req["query"], req.get("platform"), req.get("limit", 20))
        return {
            "platform": req.get("platform"),
            "query": req.get("query"),
            "items": [to_lingzao_item(r) for r in rows],   # 字段见 contract.md
            "page": {"next_cursor": None, "limit": req.get("limit", 20),
                     "returned_count": len(rows)},
        }
```

2. 启动时指定：

```powershell
$env:LINGZAO_LOCAL_BACKEND = "my_backend:MyBackend"
python server.py --port 8787
```

只实现你要用的方法即可，未实现的返回空数据（渲染成 `-`），不会崩。

## 字段契约

完整请求/响应字段见 [`contract.md`](contract.md)。三个最容易踩的坑：

1. **生图返回 base64**，不是 URL。CLI 只认 `data.image.b64_json`，不会去下载链接。
2. **评论的 `--limit` 在部分平台不可用**。小红书不支持，传了会直接退出（客户端校验），
   去掉 `--limit` 即可。
3. **`metrics` 键名固定**：`liked / collected / commented / shared`，写错不会报错，
   只会显示 0。

## 已验证

`smoke.ps1` 覆盖全部 13 条命令，用 MockBackend 实跑通过（2026-10-30）：

| 命令 | 结果 |
|---|---|
| doctor | ✅ |
| search-notes / search-users | ✅ |
| get-note-detail / get-note-comments | ✅ |
| get-user-info / get-user-posted-notes / analyze-user-profile | ✅ |
| get-article-detail / get-article-stats / get-related-articles | ✅ |
| extract-video-copy | ✅ |
| generate-image（2 张，解码落盘） | ✅ |

## 采集后端：两条线

| 线 | 入口 | 用途 |
|---|---|---|
| A · MCP | `justoneapi` 服务（DSH / Codex 已注册） | Agent 临时探索、查接口、单次取数 |
| B · REST | `justone.py` → `server.py` | 喂织造 40 个 playbook，批量取数后本地分析 |

两条线说明见 [mcp-justoneapi.md](mcp-justoneapi.md)。

启用 B 线：

```powershell
$env:JUSTONEAPI_TOKEN = "你的 token"
$env:LINGZAO_LOCAL_BACKEND = "justone:JustOneBackend"
python server.py --port 8787
```

`LINGZAO_JUSTONE_RAW=1` 会在输出里附带 JustOneAPI 原始 JSON，用于校准字段映射。

## 关于 SKILL.md 里的平台话术

SKILL.md 的 `Setup` 和 `Install And Online Capability Entry` 两节仍在让 Agent
“去 lingzao.atian.vip 开通 Key”。功能上不影响（playbook 照跑），只是对话里会
提到你不需要的入口。要彻底自洽，把这两节替换成本仓库的说明即可——注意
`npx skills add` 更新会覆盖，改完记得另存一份。
