# 织造 Skill 本地版 · 一键安装
#
#   .\install.ps1 -Token "你的 JustOneAPI token"
#   .\install.ps1 -NoMcp                    # 只装 skill + 后端，不装数据源 MCP
#   .\install.ps1 -SkillOnly                # 只装 skill（不需要联网取数）
#
# 幂等：重复运行不会重复写配置；旧版本会备份到 <skill>.bak-<时间戳>。
param(
    [string]$Token = "",
    [switch]$NoMcp,
    [switch]$SkillOnly,
    [switch]$NoDesktopShortcut,
    [string]$TargetRoot = "$env:USERPROFILE"
)

$ErrorActionPreference = "Stop"
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch {}
$utf8 = New-Object System.Text.UTF8Encoding($false)

$Root       = $PSScriptRoot
$SkillSrc   = Join-Path $Root "zhizao"
$BackendSrc = Join-Path $Root "lingzao-local"
$SkillDir   = Join-Path $TargetRoot ".agents\skills\zhizao"
$BackendDir = Join-Path $TargetRoot ".lingzao-local"
$McpDir     = Join-Path $TargetRoot ".codex\mcp\justoneapi-mcp"
$DshPatch   = Join-Path $TargetRoot ".dsh\cordis.patch.yml"
$CodexConf  = Join-Path $TargetRoot ".codex\config.toml"

function Say($m, $c = "Gray") { Write-Host $m -ForegroundColor $c }
function Need($cmd, $hint) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) { throw "缺少 $cmd，$hint" }
}

Say ""
Say "织造 Skill 本地版 · 安装" Cyan
Say "  目标目录: $TargetRoot"
Say ""

# ---------------------------------------------------------------- 1. Skill
if (-not (Test-Path (Join-Path $SkillSrc "SKILL.md"))) { throw "找不到包内 skill：$SkillSrc" }

if (Test-Path $SkillDir) {
    $bak = "$SkillDir.bak-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Move-Item $SkillDir $bak
    Say "[1/4] 已备份旧版 -> $bak" DarkGray
}
New-Item -ItemType Directory -Force -Path (Split-Path $SkillDir) | Out-Null
Copy-Item $SkillSrc $SkillDir -Recurse -Force
Say "[1/4] skill 已安装 -> $SkillDir" Green

if ($SkillOnly) {
    Say "[2/4] -SkillOnly：跳过后端与 MCP" DarkGray
    Say ""
    Say "完成。数据查询类功能不可用，纯方法论可用。" Green
    return
}

# ---------------------------------------------------------------- 2. 本地后端
if (-not (Test-Path (Join-Path $BackendSrc "server.py"))) { throw "找不到本地后端：$BackendSrc" }
if (Test-Path $BackendDir) { Remove-Item $BackendDir -Recurse -Force }
New-Item -ItemType Directory -Force -Path $BackendDir | Out-Null
Get-ChildItem $BackendSrc -File | Where-Object { $_.Extension -in ".py", ".md", ".ps1", ".mjs" } |
    Copy-Item -Destination $BackendDir -Force
foreach ($bat in @("启动织造.bat", "安装织造.bat")) {
    $src = Join-Path $BackendSrc $bat
    if (Test-Path $src) { Copy-Item $src (Join-Path $BackendDir $bat) -Force }
}
# 桌面放一个双击入口，小白不用找目录
$desktop = [Environment]::GetFolderPath("Desktop")
if (-not $NoDesktopShortcut -and $desktop -and (Test-Path $desktop)) {
    $launcher = Join-Path $BackendDir "启动织造.bat"
    if (Test-Path $launcher) {
        Copy-Item $launcher (Join-Path $desktop "启动织造.bat") -Force
        Say "      桌面已放好「启动织造」，以后双击它就行" DarkGray
    }
}
Say "[2/4] 本地后端已安装 -> $BackendDir" Green

# ---------------------------------------------------------------- 3. 数据源 MCP（可选）
if ($NoMcp) {
    Say "[3/4] -NoMcp：跳过 MCP，数据走 REST 后端" DarkGray
} elseif (Test-Path (Join-Path $McpDir "dist\src\index.js")) {
    Say "[3/4] MCP 已存在" DarkGray
} else {
    Need git "安装 Git 后重试，或加 -NoMcp 跳过"
    Need npm "安装 Node.js 后重试，或加 -NoMcp 跳过"
    Say "[3/4] 拉取并构建 justoneapi-mcp ..."
    New-Item -ItemType Directory -Force -Path (Split-Path $McpDir) | Out-Null
    git clone --depth 1 https://github.com/justoneapi-official/justoneapi-mcp.git $McpDir
    Push-Location $McpDir
    try {
        npm ci --no-audit --no-fund | Out-Null
        npm run build | Out-Null
    } finally { Pop-Location }
    # 启动器：缺 token 也能起来（目录类工具可用）
    $launcher = Join-Path $McpDir "run-mcp.mjs"
    if (-not (Test-Path $launcher)) { Copy-Item (Join-Path $BackendSrc "run-mcp.mjs") $launcher -Force }
    Say "      MCP 构建完成" Green

    # 注册到 DSH
    if (Test-Path $DshPatch) {
        if (-not (Select-String -Path $DshPatch -Pattern "justoneapi-mcp" -Quiet)) {
            $node = Join-Path $env:ProgramFiles "nodejs\node.exe"
            if (-not (Test-Path $node)) { $node = (Get-Command node).Source }
            $entry = @"
  - id: justoneapi-mcp
    name: '@deepseek-ai/dsh-mcp-client'
    config:
      serverName: justoneapi
      transport: stdio
      command: $node
      args:
      - $McpDir\run-mcp.mjs
      cwd: $McpDir
      toolCallTimeoutMs: 180000
      failOnStartupError: false
"@
            [System.IO.File]::WriteAllText($DshPatch, ([System.IO.File]::ReadAllText($DshPatch, [Text.Encoding]::UTF8)).TrimEnd() + "`n" + $entry, $utf8)
            Say "      已注册到 DSH" DarkGray
        }
    }
    # 注册到 Codex
    if (Test-Path $CodexConf) {
        if (-not (Select-String -Path $CodexConf -Pattern "mcp_servers\.justoneapi" -Quiet)) {
            $node = Join-Path $env:ProgramFiles "nodejs\node.exe"
            if (-not (Test-Path $node)) { $node = (Get-Command node).Source }
            $block = @"

[mcp_servers.justoneapi]
command = '$node'
args = ['$McpDir\run-mcp.mjs']
cwd = '$McpDir'
startup_timeout_sec = 30
tool_timeout_sec = 120
"@
            [System.IO.File]::WriteAllText($CodexConf, ([System.IO.File]::ReadAllText($CodexConf, [Text.Encoding]::UTF8)).TrimEnd() + $block + "`n", $utf8)
            Say "      已注册到 Codex" DarkGray
        }
    }
}

# ---------------------------------------------------------------- 4. Token
if (-not $Token -and -not $SkillOnly) {
    # 交互环境才问；批处理/管道里执行时跳过，不能因此中断安装
    $interactive = -not [Console]::IsInputRedirected
    if ($interactive) {
        Write-Host ""
        Write-Host "  ── 关于数据密钥 ──────────────────────────────" -ForegroundColor Cyan
        Write-Host "  查真实数据（搜笔记、看主页、读评论）需要一个数据密钥。"
        Write-Host "  不配也能用：选题、标题、内容包、发布检查、复盘都不需要它。"
        Write-Host ""
        Write-Host "  开通只要三步：" -ForegroundColor Cyan
        Write-Host "    1) 注册（有免费额度，不用立刻付费）"
        Write-Host "       https://dashboard.justoneapi.com/zh/register"
        Write-Host "    2) 登录控制台，找到「API Token / 访问令牌」，整串复制"
        Write-Host "       https://dashboard.justoneapi.com/zh"
        Write-Host "    3) 把密钥粘贴到下面，回车"
        Write-Host ""
        Write-Host "  官方说明：https://docs.justoneapi.com/zh/usage"
        Write-Host "  ─────────────────────────────────────────────" -ForegroundColor Cyan
        Write-Host ""
        try {
            $Token = (Read-Host "  请粘贴密钥（没有就直接回车，稍后再装）").Trim()
        } catch {
            $Token = ""
        }
    }
}

if ($Token) {
    [Environment]::SetEnvironmentVariable("JUSTONEAPI_TOKEN", $Token, "User")
    # 让 Agent 不必手敲命令：把后端地址也写进环境变量
    [Environment]::SetEnvironmentVariable("LINGZAO_BASE_URL", "http://127.0.0.1:8787", "User")
    [Environment]::SetEnvironmentVariable("LINGZAO_API_KEY", "lgz_local", "User")
    $env:JUSTONEAPI_TOKEN = $Token
    if (Test-Path $McpDir) {
        Set-Content -Path (Join-Path $McpDir ".justoneapi_token") -Value $Token -Encoding ASCII -NoNewline
    }
    Say "[4/4] token 已写入用户环境变量 JUSTONEAPI_TOKEN" Green
} else {
    Say "[4/4] 还没设置密钥：查数据会失败。" Yellow
    Say "      想补上，再双击一次「安装织造」，把密钥粘进去就行。" Yellow
    Say "      还没有密钥？注册地址（有免费额度）：" Yellow
    Say "        https://dashboard.justoneapi.com/zh/register" Yellow
    Say "      官方说明：https://docs.justoneapi.com/zh/usage" Yellow
}

Say ""
Say "============================================" Cyan
Say " 安装完成" Green
Say "============================================" Cyan
Say ""
Say "以后怎么用（三步）："
Say ""
Say "  1. 双击桌面上的「启动织造」，会弹出一个黑色窗口，不要关它"
Say "  2. 回到聊天窗口，直接跟 Agent 说话，比如" Cyan
Say "     「用织造帮我拆一下这条笔记」" Cyan
Say "  3. 用完直接关掉那个黑窗口就行" Cyan
Say ""
if (-not $Token) {
    Say " ⚠ 还没设置密钥：数据查询会失败。再双击一次「安装织造」补上即可。" Yellow
    Say ""
}
