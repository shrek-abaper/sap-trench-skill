# sap-trench-skill

SAP 实战知识技能包——十余年真实项目经验蒸馏，覆盖 SAP 全模块排查与开发场景。

## 适用场景

在 AI 对话中提问任何 SAP 相关问题时自动触发，无需手动调用。

典型触发示例：
- "MIGO 过账报 Serial number already exists 怎么解决？"
- "SD 定价过程中 PR00 条件类型找不到，根因是什么？"
- "IDoc 状态 51 的排查思路"
- "ABAP BAdI 实现步骤"
- "STO 调拨订单科目确定配置"

## 安装

```bash
cp -r sap-trench-skill ~/.agents/skills/
```

oh-my-opencode 会在对话启动时自动发现并加载此技能。

## 知识覆盖

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
| 排查案例库 | `references/troubleshooting.md` | CASE-001~CASE-015，完整根因分析 |

## 知识质量标准

每条收录的知识满足：

- 在真实项目中被触发过（有具体业务场景）
- 有明确的根本原因分析（不只是"怎么做"，更说明"为什么"）
- 解决方案经过验证（非猜测性）
- 包含升级安全性和传输可行性评估

## 贡献

参见 [CONTRIBUTING.md](CONTRIBUTING.md)。每条知识卡片遵循统一结构：**现象 → 根本原因 → 解决方案 → 经验总结**。
