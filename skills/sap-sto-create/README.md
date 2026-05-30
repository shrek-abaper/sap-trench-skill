# SAP STO 订单创建（OData）

通过 S/4HANA OData 服务 `API_PURCHASEORDER_PROCESS_SRV` 创建 STO 调拨订单，售后工厂发出时自动尝试创建外向交货单。

## 目录结构

```text
.
├── .env
├── .env.example
├── .gitignore
├── README.md
├── SKILL.md
├── evals/
│   └── evals.json
└── scripts/
    ├── sap_sto_cli.py          # CLI 入口
    ├── requirements.txt        # Python 依赖
    └── lib/
        ├── create_sto_odata.py # 核心业务逻辑
        └── java/
            ├── SapDeliveryCreator.java
            ├── sapjco3.jar
            └── lib/
                ├── linux/
                │   └── libsapjco3.so
                ├── macos/
                │   └── libsapjco3.jnilib  # macOS JCo 本地库（需自行放置）
                └── windows/
                    └── sapjco3.dll
```

## 环境配置

编辑 `.env`（请勿提交真实凭据）：

```bash
SAP_URL=http://your.sap.server:8000
SAP_ASHOST=your.sap.host
SAP_SYSNR=00
SAP_CLIENT=800
SAP_USER=your_username
SAP_PASSWORD=your_password
SAP_LANG=EN
```

`SAP_JCO_LIB_PATH` 默认不需要设置，JCo 本地库已随包附带，程序按操作系统自动选取：

| 系统 | 自动路径 | 文件 |
|------|----------|------|
| Linux | `scripts/lib/java/lib/linux/` | `libsapjco3.so` |
| macOS | `scripts/lib/java/lib/macos/` | `libsapjco3.jnilib` 或 `libsapjco3.dylib` |
| Windows | `scripts/lib/java/lib/windows/` | `sapjco3.dll` |

> **macOS 用户**：SAP 不在开源渠道分发 macOS 版 JCo 本地库，需从 [SAP Service Marketplace](https://support.sap.com/en/product/connectors/jco.html) 下载 macOS 版 SAP JCo 3，将 `libsapjco3.jnilib`（或 `libsapjco3.dylib`）放入 `scripts/lib/java/lib/macos/` 目录后即可自动生效。

如需使用自定义路径，设置 `SAP_JCO_LIB_PATH` 为绝对路径或相对技能根目录的路径。

## CLI 使用

```bash
python3 scripts/sap_sto_cli.py plants

python3 scripts/sap_sto_cli.py preview \
  --supply-plant P002 \
  --receiving-plant A002 \
  --material MAT-001:3 \
  --material MAT-002:1 \
  --delivery-date 2026-05-30 \
  --batch-number BATCH001

python3 scripts/sap_sto_cli.py create \
  --supply-plant P002 \
  --receiving-plant A002 \
  --material MAT-001:3 \
  --material MAT-002:1 \
  --delivery-date 2026-05-30 \
  --batch-number BATCH001 \
  --confirmed
```

`--batch-number` 为必输字段（最多14位），用于标识本次创建的业务批次并写入 SAP 采购订单的供应商销售员字段，提交前会自动校验该批次号在 SAP 中是否已存在。`--confirmed` 为必须显式传入的安全开关，防止误创建。

## 工厂与订单类型规则

- 量产工厂：`P001` `P002` `P003` `P004` `P005`
- 售后工厂：`A001` `A002`
- 只允许量产<->售后跨类型组合
- 发出或接收含 `P005`/`P001` → `ZSTO_T1`；其他合法组合 → `ZSTO_T2`
- 公司代码（按接收工厂）：`526x`→`C001`；`P001`→`C002`；`F1xx`→`C003`；`F2xx`→`C004`；`F3xx`→`C005`

## 外向交货单

发出工厂为售后时，STO 创建成功后自动尝试 JCo 创建外向交货单（`BAPI_OUTB_DELIVERY_CREATE_STO`）。失败不影响 STO 主单。

## 常见问题

- `Supplier ... cannot be processed`：ZSTO_T2 的 `Supplier` 必须留空
- `CSRF token validation failed`：检查会话 token、sap-client、鉴权和 URL
- 交货日期被顺延：SAP 工作日校验，按系统提示日期重试
- 外向交货单失败：多为业务校验（`VR420`）或 JCo 环境问题，不影响 STO 主单
