# 织造 Skill · 本地版

不依赖织造官方平台：数据从你自己买的 JustOneAPI 配额走，跑在本机。
生图只出提示词，不调用任何生图接口。

## 安装（Windows / PowerShell 7+）

`powershell
# 解压后进入目录
.\install.ps1 -Token "你的 JustOneAPI token"
`

没有 token 也可以先装（-SkillOnly 只装方法论，不需要联网）：

`powershell
.\install.ps1 -SkillOnly
`

## 启动数据后端

`powershell
cd $env:USERPROFILE\.lingzao-local
$env:LINGZAO_LOCAL_BACKEND = "justone:JustOneBackend"
python server.py --port 8787
`

另开一个终端：

`powershell
$env:LINGZAO_BASE_URL = "http://127.0.0.1:8787"
$env:LINGZAO_API_KEY  = "lgz_local"
lingzao doctor
`

## 目录

| 目录 | 内容 |
|---|---|
| `lingzao\` | skill 本体：SKILL.md + 42 个 playbook |
| `lingzao-local\` | 本地数据后端：HTTP 服务 + JustOneAPI 适配器 |

## 支持哪些平台

小红书、抖音、快手、微博、B 站、TikTok、YouTube、今日头条、Reddit、微信公众号、视频号。
不含 Instagram（数据源没有）。逐字稿：B站/YouTube 取原生字幕，其余平台返回视频直链，
需自己用多模态模型转写。

详细能力矩阵见 `lingzao\SKILL.md` 的「平台能力矩阵」。

## 常见问题

**必须是 Windows 吗？**
安装脚本是 PowerShell。Linux/macOS 可以手动拷贝 `lingzao\` 到 `~/.agents/skills/`，
再 `python server.py` 起后端，逻辑一致。

**token 从哪来？**
JustOneAPI 官网注册后在控制台获取。按接口计费。

**会不会覆盖我原来的 skill？**
会。安装时旧版本自动备份到 `<skill目录>.bak-<时间戳>`。

**数据准不准？**
字段结构按官方真实响应样本校准，但不同平台口径不同；做决策前建议抽样核对。
