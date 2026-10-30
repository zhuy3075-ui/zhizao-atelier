# NOTICE / 来源与授权

## 方法论文本（playbooks、SKILL.md 主体）

改造自 Zhizao Skill：

- 官方分发：https://assets-tian.midao.site/skills/lingzao（版本 0.1.115）
- 公开仓库：https://github.com/atian-create/lingzao-skill（MIT-0）

本包对原内容做了以下修改：移除织造平台/积分/API Key 相关话术；把生图改为只出提示词；
补充平台能力矩阵与本地后端调用规则；删除商品研究与 Instagram 相关功能。

**授权提示**：公开仓库为 MIT-0（可商用免署名），但官方 0.1.115 分发包未附 LICENSE。
对外分发或商用前，请自行确认上游授权；本包不附带任何授权承诺。

## 数据源

JustOneAPI（https://api.justoneapi.com），使用行为受其服务条款约束。
本包不含任何 API Key，token 由使用者自行配置。

## 第三方组件

justoneapi-mcp（MIT）由官方仓库单独拉取构建，不在本包内分发。
