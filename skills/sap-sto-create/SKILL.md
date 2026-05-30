---
name: sap-sto-create
description: "通过 S/4HANA OData API 创建 STO 调拨订单（ZSTO_T1/ZSTO_T2）。当用户意图为：创建 STO、创建 SAP 调拨订单、公司间/工厂间调拨、指定发出工厂+接收工厂+物料+数量+交期创建采购订单时触发。必须强制执行「先 preview 确认、再 create」的双步骤门禁。"
---

# SAP STO 订单创建技能（OData）

通过 `API_PURCHASEORDER_PROCESS_SRV` 创建 STO 调拨订单，售后工厂发出时自动尝试创建外向交货单（JCo）。

## CLI Location

The CLI is `scripts/sap_sto_cli.py` relative to this skill's directory.

```bash
python3 scripts/sap_sto_cli.py <command>
```

First run auto-installs dependencies. All commands output JSON to stdout.

## Commands Quick Reference

| Command | Usage | Description |
|---------|-------|-------------|
| `plants` | `plants` | 列出所有支持的工厂代码和名称 |
| `preview` | `preview --supply-plant PLANT --receiving-plant PLANT --material MAT:QTY[:DATE] [--material ...] [--delivery-date DATE] --batch-number BATCH_NO` | 预览 STO 订单信息（不创建），生成一次性确认标识，输出 `requires_confirmation=true` + `confirmation_summary` |
| `create` | `create --supply-plant PLANT --receiving-plant PLANT --material MAT:QTY[:DATE] [--material ...] [--delivery-date DATE] --batch-number BATCH_NO --confirmed` | 创建 STO 订单，必须显式传 `--confirmed` |

`--material` 可重复，格式 `MAT:QTY` 或 `MAT:QTY:YYYY-MM-DD`。`--batch-number` 为必输字段，最多14位。

## Key Behaviors & Gotchas

- **强制双步骤门禁**：禁止在同一执行流里 `preview` 后直接 `create`。必须 preview → 输出确认摘要 → 用 question tool 询问用户 → 仅在获得明确确认后 → 单独调用 `create --confirmed`。
- **确认标识单次有效**：每次 `preview` 会生成一个新的一次性确认标识（写入 `~/.sap_sto_confirm_token.json`）。`create --confirmed` 会立即消耗该标识——无论创建成功还是失败，标识均作废。同一对话内，任何情况下都不能复用上一次的确认——再次创建必须重新运行 `preview`，再次用 question tool 询问用户确认后，才能调用 `create --confirmed`。
- **批次号唯一性校验**：`create` 执行前会调用 SAP 查询 `SupplierRespSalesPersonName eq '<batch_number>'`，若已有匹配 PO 则拒绝创建并提示重复的 PO 号。需要用户更换批次号后重新 preview。
- **批次号写入 SAP**：创建成功后，批次号写入采购订单头的 `SupplierRespSalesPersonName`（供应商销售员）字段，作为永久标记。
- **交货日期必填**：整单用 `--delivery-date`，逐行在 `MAT:QTY:DATE` 里指定；两者都不传会被本地拦截。
- **工厂组合**：量产工厂（`P001` `P002` `P003` `P004` `P005`）与售后工厂（`A001` `A002`）必须跨类型组合；同类组合本地直接拦截。
- **订单类型**：发出或接收含 `P005`/`P001` → `ZSTO_T1`；其余合法组合 → `ZSTO_T2`。
- **公司代码**（按接收工厂）：`526x` → `C001`；`P001` → `C002`；`F1xx` → `C003`；`F2xx` → `C004`；`F3xx` → `C005`。
- **ZSTO_T2 供应商**：`Supplier` 必须留空字符串，否则 SAP 会拒绝。
- **外向交货单**：发出工厂为售后时，STO 创建成功后自动尝试 JCo 创建交货单；失败不影响 STO 主单成功。
- **JCo 平台库**：程序自动按操作系统选取本地库目录（`lib/linux/` → Linux，`lib/macos/` → macOS，`lib/windows/` → Windows）；macOS 用户需自行从 SAP Service Marketplace 下载 JCo 并将 `libsapjco3.jnilib`（或 `libsapjco3.dylib`）放入 `scripts/lib/java/lib/macos/`。
- **自然语言日期**：用户说"月底"/"下周五"时，先换算成 `YYYY-MM-DD` 再调用。
- **敏感配置**：不输出或回显账号、密码、主机凭据。
- **环境变量缺失**：若输出含 `缺少必要环境变量`，立即引导用户在技能根目录（`SKILL.md` 所在目录）执行首次配置流程，不要继续尝试创建订单。

## Output Schemas & Enums

**`preview` 成功返回**：
```json
{
  "requires_confirmation": true,
  "confirmation_summary": "...",
  "order_data_preview": { "doc_type": "ZSTO_T2", "supply_plant": "P002", "company_code": "C003", "items": [...] }
}
```

**`create` 成功返回**：
```json
{
  "success": true,
  "po_number": "4500012345",
  "delivery_created": false,
  "delivery_number": null,
  "order_data": { "doc_type": "ZSTO_T2", "supply_plant": "P002", "company_code": "C003", "items": [...] }
}
```

**`create` 失败返回**：
```json
{
  "success": false,
  "messages": [{ "type": "E", "message": "..." }],
  "suggest": "...",
  "order_data": { ... }
}
```

## Workflows

**标准创建流程**：
1. `preview --supply-plant P002 --receiving-plant A002 --material MAT-001:3 --delivery-date 2026-05-30 --batch-number BATCH001`
2. 输出 `confirmation_summary`（含批次号），停止，用 question tool 询问用户是否确认
3. 用户确认后：`create --supply-plant P002 --receiving-plant A002 --material MAT-001:3 --delivery-date 2026-05-30 --batch-number BATCH001 --confirmed`
4. 成功：渲染 `### ✅ STO 订单创建成功` + 订单抬头表格 + 物料明细表格，采购订单号高亮 `**_PO号_**`
5. 失败：渲染 `### ❌ STO 订单创建失败` + 错误明细表格 + 可执行建议

**查看工厂列表**：`plants` → 获取所有可用工厂代码，再做 preview/create

**多物料**：`--material MAT1:QTY1:DATE1 --material MAT2:QTY2:DATE2`（逐行交期），或统一用 `--delivery-date DATE`（整单交期）
**首次配置（环境变量缺失时）**：
1. 在技能根目录执行：`cp .env.example .env`（Windows：`copy .env.example .env`）
2. 编辑 `.env`，填入必填项：`SAP_URL`、`SAP_ASHOST`、`SAP_SYSNR`、`SAP_CLIENT`、`SAP_USER`、`SAP_PASSWORD`
3. 若发出工厂为售后工厂（需创建外向交货单），以上变量已包含 JCo 所需配置，无需额外添加
4. 填写完成后重新执行 `preview` 命令
