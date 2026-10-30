# JustOneAPI 两条线接入说明

采集能力用 [JustOneAPI](https://docs.justoneapi.com/zh/)，**不经过织造平台**。
分成两条互不干扰的线：

```
线 A（MCP）  Agent ── MCP stdio ──> justoneapi-mcp ──> api.justoneapi.com
             适合：临时查数据、探索接口、写分析

线 B（REST） lingzao CLI ── HTTP ──> lingzao-local ──> api.justoneapi.com
             适合：跑织造的 40 个 playbook，输出走织造渲染
```

两条线共用同一个 token。

---

## 线 A：MCP

### 装在哪

| 项 | 值 |
|---|---|
| 源码 | `C:\Users\Administrator\.codex\mcp\justoneapi-mcp`（官方仓库 v2.0.0，已 `npm ci` + `npm run build`） |
| 启动器 | `run-mcp.mjs`（负责注入 token，两个客户端共用） |
| 入口 | `dist\src\index.js` |
| 工具数 | 7 |

工具：

| 工具 | 用途 | 需要 token |
|---|---|---|
| `list_platforms` | 列出支持的平台和端点数 | 否 |
| `search_endpoints` | 自然语言找接口 | 否 |
| `get_endpoint_schema` | 查参数契约、枚举、默认值 | 否 |
| `call_endpoint` | 真正取数（会计费） | **是** |
| `get_account_balance` | 查余额 | **是** |
| `get_usage_summary` | 查用量 | **是** |
| `refresh_catalog` | 刷新目录（管理员） | 管理员 token |

标准用法：`search_endpoints` → `get_endpoint_schema` → `call_endpoint`。

### 已注册到两个客户端

**DSH** — `C:\Users\Administrator\.dsh\cordis.patch.yml`

```yaml
  - id: justoneapi-mcp
    name: '@deepseek-ai/dsh-mcp-client'
    config:
      serverName: justoneapi
      transport: stdio
      command: C:\Program Files\nodejs\node.exe
      args:
      - C:\Users\Administrator\.codex\mcp\justoneapi-mcp\run-mcp.mjs
      cwd: C:\Users\Administrator\.codex\mcp\justoneapi-mcp
      toolCallTimeoutMs: 180000
      failOnStartupError: false
```

**Codex** — `C:\Users\Administrator\.codex\config.toml`

```toml
[mcp_servers.justoneapi]
command = 'C:\Program Files\nodejs\node.exe'
args = ['C:\Users\Administrator\.codex\mcp\justoneapi-mcp\run-mcp.mjs']
cwd = 'C:\Users\Administrator\.codex\mcp\justoneapi-mcp'
startup_timeout_sec = 30
tool_timeout_sec = 120
```

### token 怎么给（运行时）

启动器按顺序找：`JUSTONEAPI_TOKEN` 环境变量 → 同目录 `.justoneapi_token` 文件 → 都没有则注入哨兵值。

```powershell
# 推荐：写用户级环境变量，然后重启 DSH / Codex
setx JUSTONEAPI_TOKEN "你的 token"
```

> 哨兵值的作用：上游服务缺 token 会直接退出，导致客户端一直 `disconnected`。
> 注入哨兵后服务能起来，**目录类工具照常可用**，只有 `call_endpoint` 会鉴权失败并明确报错。
> 这是刻意的——不会假装取数成功。

### 验证

```powershell
cd D:\Users\Administrator\Documents\deepseek-harness\default-workspace\lingzao-local
node mcp_probe.mjs "C:\Users\Administrator\.codex\mcp\justoneapi-mcp\run-mcp.mjs" "C:\Users\Administrator\.codex\mcp\justoneapi-mcp"
```

预期输出 `count: 7`。**DSH 需要重启一次**才会重新拉起之前启动失败的进程。

---

## 线 B：REST（织造本地后端）

织造 CLI 只认 12 个固定路径的 JSON 形状，所以这层要做的是**翻译**：
`/api/v1/research/*` 的请求 → JustOneAPI 的接口 → 归一化成织造的形状。

- 契约：[contract.md](contract.md)
- 端点映射：[docs/mapping.md](docs/mapping.md)
- 官方接口目录（从 SDK 反解，含参数）：[docs/endpoints.json](docs/endpoints.json)
- 文档语料（63 篇，已落盘）：`docs/*.md`

### 状态

| 步骤 | 状态 |
|---|---|
| 抽出织造契约（12 接口） | ✅ 已完成并跑通 mock |
| 抓全 13 平台文档（63 篇） | ✅ |
| 反解官方 SDK 得到路径 + 参数 | ✅ 13 平台 / 155 端点 |
| 选定每个平台的核心 5–6 个接口 | ✅ 见 mapping.md |
| 写 REST 适配器（transport + 归一化） | ⏳ 待写 |
| 按真实响应校准字段 | ⏳ 需要一次真实调用 |

> 响应字段名官方未公开（文档的"响应示例"是前端动态加载的，OpenAPI 里 `data` 是空 schema）。
> 所以适配器按候选键匹配 + 保留原始 JSON，用一次真实响应就能校准，不用猜第二遍。

---

## 为什么不全走 MCP

MCP 是给 Agent 临时探索用的，每次调用都要模型决策、结果进上下文；
织造的 playbook 需要**稳定、可复现、字段确定**的数据管道，且要能一次拉多页再本地分析。
所以两条线并存：MCP 用于人机协作探索，REST 用于批量喂 playbook。
