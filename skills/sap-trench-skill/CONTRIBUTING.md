# SAP Trench Skill — 贡献指南

## 如何从 Notion 迁移笔记到本 Skill

### 新增一个知识卡片（troubleshooting.md）

复制以下模板，填入 `references/troubleshooting.md`：

```markdown
## CASE-NNN：[问题标题，包含关键模块和症状]

**标签**：`#模块` `#关键词1` `#关键词2` `#SAP版本`

**现象**
[用户操作了什么，系统发生了什么，报了什么错]

**根本原因**
[为什么会发生这个问题。这是最核心的部分，也是区别于网络文档的关键]

**如何定位（可选）**
[用什么工具定位到根因的，排查思路]

**解决方案**
[可执行的步骤，如有多方案按推荐度排序]

**经验总结**
[规律性认识，下次遇到类似问题能快速联想到]
```

### 知识卡片质量标准

- ✅ 必须来自真实项目场景（不是理论推导）
- ✅ 根本原因必须说清楚"为什么"，不只是"怎么做"
- ✅ 解决方案经过验证
- ✅ 标签包含：`#模块`、`#关键技术`、`#SAP版本`（ECC/S4HANA）

### 向 references/ 添加新模块文件

如果某个主题积累了 5 条以上知识点，可以新建独立文件：

```
references/
├── abap.md           ← ABAP 开发：语法、增强、BAdI、性能优化
├── auth.md           ← 权限管理：AUTHORITY-CHECK、角色、SU53
├── fico.md           ← FI/CO 模块：凭证、科目、COPA、汇率
├── integration.md    ← 系统集成：PI/PO、IDoc、Proxy、OData
├── mm.md             ← MM 模块：采购、库存、STO、科目确定
├── pm.md             ← PM 模块：工厂维护、设备、维护订单
├── pp.md             ← PP 模块：生产订单、BOM、MRP、ATP
├── print.md          ← 打印技术：SmartForms、SAPscript、NACE
├── qm.md             ← QM 模块：检验批、使用决策、质量通知书
├── reference-tables.md  ← 全模块 T-code / 关键表 / BAPI 索引
├── sd.md             ← SD 模块：销售订单、定价、交货、开票
├── troubleshooting.md   ← 排查案例库（CASE-NNN 格式）
├── vms.md            ← VMS 模块：IS-AUTO VELO、IDoc 增强
├── wm.md             ← WM 模块：仓库管理、转储单、盘点
│
│   # 以下为待建扩展方向，欢迎贡献：
├── btp.md            ← BTP / CPI / 云集成（待建）
└── rap.md            ← RAP / Fiori Elements（待建）
```

新建文件后，在 `SKILL.md` 的路由表中添加对应行。

### Notion → Skill 批量迁移建议

优先迁移以下类型的页面：
1. **项目排查笔记**（如 CASE 格式的问题记录）→ `troubleshooting.md`
2. **技术知识总结**（如 ABAP 增强、PI 接口方法论）→ 对应模块 `.md`
3. **代码片段库**（如 ZCL_ABAP_TOOLS）→ 对应模块 `.md` 的代码示例部分
4. **事务码速查**→ `reference-tables.md`

**暂不迁移**：
- 项目专属配置（含客户信息）
- 截图类笔记（Skill 不支持图片）
- 实验性/未验证的内容

## Skill 文件大小控制

- `SKILL.md`：保持在 150 行以内（触发层）
- 每个 `references/*.md`：建议 200-400 行，超过 400 行则拆分为子文件
- 超大的代码库（如 ZCL_ABAP_TOOLS）单独放一个文件，在 references 文件中引用路径
