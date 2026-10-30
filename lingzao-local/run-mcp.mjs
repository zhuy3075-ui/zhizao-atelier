// JustOneAPI MCP 启动器
//
// token 解析顺序：
//   1. 环境变量 JUSTONEAPI_TOKEN（推荐：写进用户级环境变量，DSH / Codex 都能读到）
//   2. 同目录 .justoneapi_token 文件（临时用，别提交到仓库）
//   3. 都没有 → 注入哨兵值，让服务能启动（目录类工具可用），call_endpoint 会因鉴权失败而报错
//
// 用法：node run-mcp.mjs
import { readFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const tokenFile = join(here, ".justoneapi_token");

if (!process.env.JUSTONEAPI_TOKEN && existsSync(tokenFile)) {
  const token = readFileSync(tokenFile, "utf8").trim();
  if (token) process.env.JUSTONEAPI_TOKEN = token;
}

if (!process.env.JUSTONEAPI_TOKEN) {
  // 上游服务在缺少 token 时会直接退出，导致 MCP 客户端一直 disconnected。
  // 注入哨兵值让服务先起来：目录/参数查询不联网，照常可用。
  process.env.JUSTONEAPI_TOKEN = "__JUSTONEAPI_TOKEN_MISSING__";
  process.stderr.write(
    "[justoneapi-mcp] 未检测到 JUSTONEAPI_TOKEN。已用哨兵值启动：\n" +
      "  - 可用：list_platforms / search_endpoints / get_endpoint_schema\n" +
      "  - 不可用：call_endpoint / get_account_balance / get_usage_summary\n" +
      "配置方式（任选其一）：\n" +
      "  1) setx JUSTONEAPI_TOKEN \"你的token\"  然后重启 DSH / Codex\n" +
      "  2) 写入文件 " + tokenFile + "\n"
  );
}

await import(pathToFileURL(join(here, "dist", "src", "index.js")).href);
