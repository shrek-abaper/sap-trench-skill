# SAP Functional Skill

> SAP 业务领域 AI Skill 集合——十余年实战笔记，蒸馏为可被 AI 智能体直接复用的知识技能包。

---

## 项目背景

做 SAP 顾问这些年，真正有价值的经验往往散落在项目现场的每一次排查过程中——那些在标准文档之外、只有亲历才能积累的判断与洞察。

这些年笔记工具换了一轮又一轮：最早用 **Mybase** 做树形笔记，后来迁到 **OneNote**，再后来系统化整理进 **Notion**。每次迁移都是一次沉淀，但笔记终究只是静态的文档，对着 AI 对话窗口它们帮不上忙。

现在 AI Coding Agent 已经成为日常工具。与其让这些积累继续躺在 Notion 里，不如把它重新组织成 AI 智能体能直接加载、索引、引用的 **SKILL** 格式——让每一条记录都能在下一次对话里及时被召唤出来，也分享给同样在 SAP 战壕里作业的同行。

这就是 **SAP Functional Skill** 的起点。从最初记录 SAP 战壕里的第一手经验（[sap-trench-skill](skills/sap-trench-skill/)），到逐步扩展为覆盖 SAP 各业务领域的 Skill 集合。

---

## 项目简介

`sap-functional-skill` 是一个遵循标准 **SKILL 规范**的 SAP 业务领域 AI 技能包集合，适用于所有支持 SKILL 格式的 AI 智能体（包括 OpenCode、Claude Code 及其他兼容框架）。

- 实战事务码速查
- 真实排查案例（现象 → 根因 → 解决方案 → 经验总结）
- 关键数据表 & BAPI 参考
- 模块配置路径与常见坑
- ABAP 增强、集成技术（PI/IDoc/OData）实操记录

所有内容来自真实项目交付，**不是对 SAP Help 的二次搬运**。

---

## 覆盖模块

| 模块 | 文件 | 内容重点 |
|---|---|---|
| ABAP 开发 | `references/abap.md` | 语法、性能优化、BAdI/Enhancement Spot、调试工具 |
| MM 采购与库存 | `references/mm.md` | 采购订单、STO 工厂间调拨、科目确定、消息控制 |
| SD 销售与分销 | `references/sd.md` | 销售订单、定价、交货、开票、信贷管理、ATP/MTO |
| FI/CO 财务 | `references/fico.md` | 凭证过账、汇率、凭证分割、COPA、替换、自动付款 |
| PP 生产计划 | `references/pp.md` | 生产订单、BOM、工艺路线、MRP、可配置 BOM |
| WM 仓库管理 | `references/wm.md` | 转储单、转储需求、仓位管理、盘点 |
| PM 工厂维护 | `references/pm.md` | 设备、功能位置、维护订单、维护计划、序列号 |
| QM 质量管理 | `references/qm.md` | 检验批、使用决策、质量通知书、检验计划 |
| VMS 车辆管理 | `references/vms.md` | IS-AUTO VELO 对象、IDoc 增强、SPRO 配置 |
| 系统集成 | `references/integration.md` | PI/PO、IDoc、Proxy、OData、XML/JSON 排查 |
| 权限管理 | `references/auth.md` | AUTHORITY-CHECK、角色、SU53、权限对象 |
| 打印技术 | `references/print.md` | SmartForms、SAPscript、NACE 消息控制 |
| 事务码速查 | `references/reference-tables.md` | 全模块 T-code、关键表、BAPI 索引 |
| 排查案例库 | `references/troubleshooting.md` | CASE-001 ~ CASE-015，完整根因分析 |

---

## 安装与使用

```bash
# 克隆本仓库，将需要的 skill 目录放到你的 skills 目录下
git clone https://github.com/shrek-abaper/sap-functional-skill.git
cp -r sap-functional-skill/skills/sap-trench-skill ~/.agents/skills/
```

oh-my-opencode 会在对话启动时自动发现并加载此技能。

### 触发方式

在 AI 对话中提问任何 SAP 相关问题时，技能会自动触发，无需手动调用。

典型触发场景：
- "MIGO 过账时报错 Serial number already exists 怎么解决？"
- "SD 定价过程中 PR00 条件类型找不到，根因是什么？"
- "IDoc 状态 51 排查思路"
- "ABAP BAdI 实现步骤"

---

## 项目结构

```
sap-functional-skill/
└── skills/
    └── sap-trench-skill/     # SAP 实战排查 Skill（首个）
        ├── SKILL.md              # 技能触发层（路由表 + 关键词）
        ├── CONTRIBUTING.md       # 贡献指南
        └── references/           # 14 个知识文件
            ├── abap.md
            ├── auth.md
            ├── fico.md
            ├── integration.md
            ├── mm.md
            ├── pm.md
            ├── pp.md
            ├── print.md
            ├── qm.md
            ├── reference-tables.md
            ├── sd.md
            ├── troubleshooting.md
            ├── vms.md
            └── wm.md
```

---

## 贡献

欢迎提交你自己踩过的 SAP 坑。贡献规范见 [CONTRIBUTING.md](skills/sap-trench-skill/CONTRIBUTING.md)。

每条知识卡片遵循统一结构：**现象 → 根本原因 → 解决方案 → 经验总结**，确保 AI 能准确理解和引用。

---

## 适用平台

本技能遵循标准 SKILL 规范，凡是支持该规范的 AI 智能体均可直接加载使用：

- 任何支持 SKILL 格式的 AI Agent 框架（原生兼容）
- [OpenCode](https://github.com/opencode-ai/opencode)
- [oh-my-opencode](https://github.com/oh-my-opencode/oh-my-opencode)

---

## License

MIT — 知识应该流动，不应该沉睡。
