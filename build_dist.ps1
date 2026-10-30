# 构建可分发包：dist\lingzao-dist\ + zip
#
#   .\build_dist.ps1
#   .\build_dist.ps1 -Version "1.0.1-local"
#
# 排除：docs/ 样本（9.7MB）、backup/、token、__pycache__、dist/ 自身
param(
    [string]$Version = "1.0.0-local.1",
    [string]$SkillSrc = "C:\Users\Administrator\.agents\skills\zhizao",
    [string]$OutDir = "$PSScriptRoot\dist"
)

$ErrorActionPreference = "Stop"
$utf8 = New-Object System.Text.UTF8Encoding($false)
$pkg = Join-Path $OutDir "lingzao-dist"
$zip = Join-Path $OutDir "lingzao-skill-local-$Version.zip"

if (Test-Path $pkg) { Remove-Item $pkg -Recurse -Force }
New-Item -ItemType Directory -Force -Path $pkg | Out-Null

# ---------------------------------------------------------------- 1. skill
Copy-Item $SkillSrc (Join-Path $pkg "zhizao") -Recurse -Force
Get-ChildItem (Join-Path $pkg "zhizao") -Recurse -Directory -Filter "__pycache__" |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# ---------------------------------------------------------------- 2. backend
$backend = Join-Path $pkg "lingzao-local"
New-Item -ItemType Directory -Force -Path $backend | Out-Null
$keep = @(
    "server.py", "justone.py", "backend.py", "query.py", "run-mcp.mjs",
    "smoke.ps1", "fetch_examples.py", "test_replay.py", "test_live.py",
    "README.md", "contract.md", "mcp-justoneapi.md", "启动织造.bat", "安装织造.bat"
)
foreach ($f in $keep) {
    $src = Join-Path $PSScriptRoot $f
    if (Test-Path $src) { Copy-Item $src (Join-Path $backend $f) -Force }
    else { Write-Warning "缺少 $f" }
}

# ---------------------------------------------------------------- 3. 顶层文件
Copy-Item (Join-Path $PSScriptRoot "install.ps1") (Join-Path $pkg "install.ps1") -Force
foreach ($bat in @("安装织造.bat", "启动织造.bat")) {
    $src = Join-Path $PSScriptRoot $bat
    if (Test-Path $src) { Copy-Item $src (Join-Path $pkg $bat) -Force } else { Write-Warning "缺少 $bat" }
}
@"
$Version
基于 Zhizao Skill 0.1.115 改造（数据层本地化）
"@.Trim() | Set-Content (Join-Path $pkg "VERSION") -Encoding UTF8

@"
# 织造 Skill · 本地版

不依赖织造官方平台：数据从你自己买的 JustOneAPI 配额走，跑在本机。
生图只出提示词，不调用任何生图接口。

## 安装（Windows / PowerShell 7+）

```powershell
# 解压后进入目录
.\install.ps1 -Token "你的 JustOneAPI token"
```

没有 token 也可以先装（`-SkillOnly` 只装方法论，不需要联网）：

```powershell
.\install.ps1 -SkillOnly
```

## 启动数据后端

```powershell
cd `$env:USERPROFILE\.lingzao-local
`$env:LINGZAO_LOCAL_BACKEND = "justone:JustOneBackend"
python server.py --port 8787
```

另开一个终端：

```powershell
`$env:LINGZAO_BASE_URL = "http://127.0.0.1:8787"
`$env:LINGZAO_API_KEY  = "lgz_local"
lingzao doctor
```

## 目录

| 目录 | 内容 |
|---|---|
| ``lingzao\`` | skill 本体：SKILL.md + 42 个 playbook |
| ``lingzao-local\`` | 本地数据后端：HTTP 服务 + JustOneAPI 适配器 |

## 支持哪些平台

小红书、抖音、快手、微博、B 站、TikTok、YouTube、今日头条、Reddit、微信公众号、视频号。
不含 Instagram（数据源没有）。逐字稿：B站/YouTube 取原生字幕，其余平台返回视频直链，
需自己用多模态模型转写。

详细能力矩阵见 ``lingzao\SKILL.md`` 的「平台能力矩阵」。

## 常见问题

**必须是 Windows 吗？**
安装脚本是 PowerShell。Linux/macOS 可以手动拷贝 ``lingzao\`` 到 ``~/.agents/skills/``，
再 ``python server.py`` 起后端，逻辑一致。

**token 从哪来？**
JustOneAPI 官网注册后在控制台获取。按接口计费。

**会不会覆盖我原来的 skill？**
会。安装时旧版本自动备份到 ``<skill目录>.bak-<时间戳>``。

**数据准不准？**
字段结构按官方真实响应样本校准，但不同平台口径不同；做决策前建议抽样核对。
"@ | Set-Content (Join-Path $pkg "README.md") -Encoding UTF8

@"
# NOTICE / 来源与授权

## 方法论文本（playbooks、SKILL.md 主体）

改造自 Zhizao Skill：

- 官方分发：`https://assets-tian.midao.site/skills/lingzao`（版本 0.1.115）
- 公开仓库：`https://github.com/atian-create/lingzao-skill`（MIT-0）

本包对原内容做了以下修改：移除织造平台/积分/API Key 相关话术；把生图改为只出提示词；
补充平台能力矩阵与本地后端调用规则；删除商品研究与 Instagram 相关功能。

**授权提示**：公开仓库为 MIT-0（可商用免署名），但官方 0.1.115 分发包未附 LICENSE。
对外分发或商用前，请自行确认上游授权；本包不附带任何授权承诺。

## 数据源

JustOneAPI（`https://api.justoneapi.com`），使用行为受其服务条款约束。
本包不含任何 API Key，token 由使用者自行配置。

## 第三方组件

`justoneapi-mcp`（MIT）由官方仓库单独拉取构建，不在本包内分发。
"@ | Set-Content (Join-Path $pkg "NOTICE.md") -Encoding UTF8

# ---------------------------------------------------------------- 4. 安全检查
$bad = @()
Get-ChildItem $pkg -Recurse -File | ForEach-Object {
    if ($_.Length -gt 2MB) { $bad += "超大文件: $($_.Name) $([math]::Round($_.Length/1MB,1))MB" }
    if ($_.Extension -in ".py", ".ps1", ".md", ".mjs", ".toml", ".yml", ".yaml") {
        $t = Get-Content $_.FullName -Raw -ErrorAction SilentlyContinue
        if ($t -match "(?i)\b(?:lgz|gho|ghp|sk)-[A-Za-z0-9_]{16,}") { $bad += "疑似密钥: $($_.Name)" }
        # 只拦"看起来像真 token 的赋值"，不拦路径/文件名引用
        if ($t -match "JUSTONEAPI_TOKEN\s*[=:]\s*[A-Za-z0-9_]{16,}") { $bad += "含 token 明文: $($_.Name)" }
        if ($t -match "lgz_[A-Za-z0-9_]{20,}") { $bad += "含 lgz_ token: $($_.Name)" }
    }
}
if (Test-Path (Join-Path $pkg "lingzao-local\docs")) { $bad += "误打包 docs/ 样本" }

if ($bad.Count -gt 0) {
    Write-Host "安全检查未通过：" -ForegroundColor Red
    $bad | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    throw "构建中止"
}

# ---------------------------------------------------------------- 5. 打包
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path (Join-Path $pkg "*") -DestinationPath $zip -CompressionLevel Optimal

$pkgSize = [math]::Round((Get-ChildItem $pkg -Recurse -File | Measure-Object Length -Sum).Sum / 1KB, 0)
$zipSize = [math]::Round((Get-Item $zip).Length / 1KB, 0)
$files = (Get-ChildItem $pkg -Recurse -File).Count

Write-Host ""
Write-Host "构建完成" Green
Write-Host "  目录: $pkg  ($files 个文件, $pkgSize KB)"
Write-Host "  压缩: $zip  ($zipSize KB)"
Write-Host ""
Write-Host "分发方式：" -ForegroundColor Cyan
Write-Host "  1) 直接发 zip，对方解压后跑 .\install.ps1 -Token ..."
Write-Host "  2) 放进 Git 仓库（先删 zip，只提交 lingzao-dist/）"
Write-Host "  3) 内网共享目录 / 网盘"
