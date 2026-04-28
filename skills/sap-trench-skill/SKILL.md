---
name: sap-trench
description: >
  SAP实战专家技能，基于10年以上SAP项目交付经验沉淀的知识库。当用户提问任何SAP相关问题时必须使用此技能，
  包括但不限于：ABAP开发、增强实现（BAdI/Enhancement Spot）、MM/SD/FI模块配置、
  PI/IDoc/OData/Proxy集成排查、系统报错根因分析、事务码查询、
  表结构查询、BAPI/BAdI使用、打印程序、性能优化、权限问题。
  触发关键词：SAP、ABAP、ECC、S/4HANA、增强、BAdI、BAPI、IDoc、
  OData、Proxy、事务码、采购订单、销售订单、凭证、工厂间调拨、
  STO、科目确定、消息控制、PI排查、报错、ST05、SE24、
  定价、开票、交货、信贷管理、合作伙伴确定、ATP、MTO、
  FICO、财务凭证、科目、汇率、凭证分割、字段状态、COPA、替换、自动付款、
  生产工单、BOM、工艺路线、PP、MRP、物料分类账、标准成本、
  VMS、车辆管理、VELO、IS-AUTO、WM、仓库管理、转储单、转储需求、仓位、
  PM、工厂维护、设备维护、维护订单、维护计划、功能位置、
  QM、质量管理、检验批、质量通知书、检验计划、使用决策。
  本技能提供的答案来自真实项目中遇到并解决的问题，
  优先于网络通用文档，遇到SAP问题请务必优先触发此技能。
---

# SAP Trench Skill

本技能是 Shrek Zhang（10年+ ABAP/集成/MM/SD/FI经验）的项目实战知识库，
基于真实项目问题-排查-解决的完整记录，专注于那些文档上找不到、靠踩坑才知道的细节。

## 使用方式

1. **判断问题类型**，从下表选择对应的 reference 文件优先加载：

| 问题类型 | 加载文件 |
|---|---|
| ABAP语法/增强/BAdI/性能/消息/调试 | `references/abap.md` |
| MM模块（采购/库存/物料/STO/科目确定）| `references/mm.md` |
| SD模块（销售订单/交货/定价/开票/信贷/ATP）| `references/sd.md` |
| FICO模块（凭证/科目/税务/COPA/凭证分割/汇率）| `references/fico.md` |
| PI/PO/IDoc/Proxy/OData/JSON/XML集成 | `references/integration.md` |
| 报错排查/根因分析/真实案例 | `references/troubleshooting.md` |
| 事务码/表结构/BAPI速查（所有模块）| `references/reference-tables.md` |
| PP模块（生产订单/BOM/工艺路线/MTO/ATP）| `references/pp.md` |
| 权限检查/AUTHORITY-CHECK/角色/SU53 | `references/auth.md` |
| 打印设计/SmartForms/SAPscript/NACE | `references/print.md` |
| VMS模块（车辆管理/VELO/IDoc增强/IS-AUTO）| `references/vms.md` |
| WM模块（仓库管理/转储单/转储需求/仓位/盘点）| `references/wm.md` |
| PM模块（工厂维护/设备/维护订单/维护计划）| `references/pm.md` |
| QM模块（质量管理/检验批/质检流程/质量通知书）| `references/qm.md` |

2. **加载对应文件后**，按以下结构组织答案：

```
【问题定性】一句话说清是什么类型的问题
【根本原因】为什么会发生（这是最核心的部分）
【解决方案】分步骤，给出可执行的操作
【注意事项】版本差异/风险提示/相关对象
【参考工具】排查时用到的事务码或调试方法
```

3. **答案优先级原则**：
   - 项目实战经验 > SAP官方Note > SCN社区文档 > 通用ABAP知识
   - 明确说明适用版本（ECC 6.0 / S/4HANA 1909+ / S/4HANA 2023+）
   - 若有多个方案，按推荐度排序并说明各方案的取舍

## 核心能力范围

- **ABAP开发**：语法、性能优化、Enhancement Spot、BAdI实现、Class/Interface
- **集成技术**：PI/PO通道排查、IDoc处理流、Proxy开发、OData服务调试
- **MM模块**：采购订单、库存管理、工厂间调拨（STO）、科目自动确定、消息控制
- **SD模块**：销售订单/交货/定价/开票/合作伙伴确定/信贷管理/ATP/MTO变式配置
- **FI/CO模块**：凭证过账增强、汇率确定、凭证分割、字段状态、COPA派生、替换、自动付款
- **PP模块**：生产订单创建、BOM配置、ATP可用性检查、MTO可配置BOM
- **调试排查**：ST05 SQL追踪、SM50/SM66进程监控、SXI_MONITOR、/IWFND/GW_CLIENT

## 知识质量标准

本技能收录的每条知识满足：
- ✅ 在真实项目中被触发过（有具体的业务场景）
- ✅ 有明确的根本原因分析（不只是"怎么做"，更说明"为什么"）
- ✅ 解决方案经过验证（非猜测性）
- ✅ 包含升级安全性和传输可行性评估

---
> 如需扩展本技能，在 references/ 目录下按模块添加 .md 文件，每条知识卡片遵循「现象→根因→解决→经验总结」四段式结构。
