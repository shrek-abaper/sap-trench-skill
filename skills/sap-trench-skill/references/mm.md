# MM 模块知识库（采购/库存/物料管理）

---

## 一、科目自动确定（Account Determination）

### 核心逻辑
MM-FI集成通过 **OBYC**（自动科目确定）配置，货物移动时系统自动生成FI凭证，无需手工记账。

### 关键事务码
| 事务码 | 用途 |
|---|---|
| `OBYC` | 自动科目确定配置（最常用）|
| `OMWM` | 评估区域设置（工厂级还是公司代码级）|
| `OMSK` | 评估类维护 |
| `OMWB` | 分析科目确定结果（模拟测试）|

### 主要TE码（Transaction/Event Keys）
| TE键 | 含义 | 触发场景 |
|---|---|---|
| `BSX` | 库存记账 | 收货，库存增加 |
| `GBB` | 库存记账冲销/消耗记账 | 发货、费用型PO |
| `WRX` | GR/IR清除科目 | 收货/发票校验 |
| `PRD` | 价格差异 | 移动平均价差异 |
| `AKO` | 寄售转自有库存差异 | MB1B 411K |
| `AUM` | 跨评估类别转移差异 | 物料转移 |

### 评估类（Valuation Class）
| 评估类 | 含义 |
|---|---|
| `3000` | 原材料 |
| `3100` | 商品（贸易品）|
| `7920` | 成品 |

### 费用型采购订单（科目分配类别=K）配置路径
1. **OMSF**：物料组配置
2. **OME9**：科目分配类别 → 科目修改码（如 VBR）
3. **OMQW**：物料组 → 评估类绑定（无物料主数据时）
4. **OBYC → GBB-VBR**：配置总账科目

---

## 二、STO 工厂间调拨

### STO 类型区别
| 类型 | 凭证类型 | BSTYP | 说明 |
|---|---|---|---|
| 公司间调拨 | ZD30/NB类 | `N` | 跨公司代码，有发票 |
| 工厂间调拨 | ZD06/UB类 | `U` | 同公司代码，无发票 |

### STO 业务流程（带SD交货）
```
ME21N（创建STO）
  ↓
VL10B（创建外向交货）
  ↓
PGI（发货过账）
  ↓
VF01（开具发票，仅公司间STO）
  ↓
MIGO 101（接收工厂收货）
```

### STO 后台配置关键步骤（SPRO路径）
1. `OME0`：设置供应工厂作为虚拟供应商
2. `OMGN`：定义装运数据（发货工厂→接收工厂）
3. 凭证类型分配：将UB/NB分配到对应工厂
4. `OMSL`：交货类型分配（NL/NLCC）

---

## 三、库存管理特殊场景

### 寄售库存（Consignment）完整流程
```
ME11 K → ME21N K（寄售PO）→ MIGO收货 → MB1B 411K（转自有库存）→ MRKO（结算）
```

**常见问题**：
- MRKO提示"没有发现税务信息" → ME12维护信息记录税码
- 提示"寄售结算: 未发现合作伙伴的消息" → `OMRM` 维护 M8-443消息，设为 `-`（关闭）

### 分包业务（Subcontracting）涉及科目
| TE键 | 说明 |
|---|---|
| `BSV` | 分包至供应商的物料（在供应商处的库存）|
| `FRL` | 分包加工费 |
| `PPV` | 分包成本差异 |
| `GBB-VBO` | 分包消耗记账 |

### MARD/MARDH历史库存计算逻辑
- `MARD`：当前库存数据（按物料+工厂+库位）
- `MARDH`：历史库存（按物料+工厂+库位+月份）
- 历史库存计算：`MARDH历史月份值` + `MSEG凭证累加` = 当前库存

---

## 四、增强实现（MM模块BAdI速查）

### 货物移动增强
**BAdI**: `MB_DOCUMENT_BADI`
- 方法 `MB_DOCUMENT_BEFORE_UPDATE`：可调试，不能写COMMIT WORK
- 方法 `MB_DOCUMENT_UPDATE`：实际写数据用此方法（无法打断点，在上方方法调试）

```abap
METHOD if_ex_mb_document_badi~mb_document_update.
  " 通过 xmkpf 获取物料凭证抬头，xmseg 获取行项目
  READ TABLE xmkpf INTO gs_mkpf INDEX 1.
  LOOP AT xmseg INTO gs_mseg.
    " 根据移动类型和特殊库存类型判断业务场景
    IF gs_mseg-bwart EQ '201' AND gs_mseg-sobkz EQ ' '.
      " 处理移动201-普通发货逻辑
    ENDIF.
  ENDLOOP.
ENDMETHOD.
```

### 采购订单增强
**BAdI**: `ME_PROCESS_PO_CUST`
- 触发时机：PO创建/修改保存时
- **注意**：在OData框架校验（`CL_MM_PUR_PO_CTR_ODATA_API`）之后触发，无法通过此BAdI绕过OData校验

### 采购申请增强
**BAdI**: `ME_PROCESS_REQ_CUST`

### 发票校验增强
**BAdI**: `INVOICE_UPDATE`
- 方法 `CHANGE_AT_SAVE`：发票保存时触发

### 采购订单消息增强
- 增强组件：`MM06E005`（采购凭证增强）
- 函数出口：`EXIT_SAPMM06E_012`

---

## 五、主要 BAPI 速查

### BAPI_GOODSMVT_CREATE（货物移动）
对应事务码：MB01(01), MB31(02), MB1A(03), MB1B(04), MB1C(05)
参数 `GOODSMVT_CODE` 控制对应功能，取值存储在表 `T158G`。

```abap
CALL FUNCTION 'BAPI_GOODSMVT_CREATE'
  EXPORTING
    goodsmvt_header = ls_header     " MKPF数据
    goodsmvt_code   = '05'          " 对应MB1C
  TABLES
    goodsmvt_item   = lt_item       " MSEG数据
    return          = lt_return.
CALL FUNCTION 'BAPI_TRANSACTION_COMMIT'.
```

### BAPI_INCOMINGINVOICE_CREATE（发票校验MIRO）
**headerdata必输字段**：`invoice_ind='X'`, `doc_date`, `pstng_date`, `comp_code`, `currency`, `gross_amount`
**itemdata必输字段**：`invoice_doc_item`, `po_number`, `po_item`, `item_amount`, `quantity`, `po_unit`, `ref_doc`, `ref_doc_year`, `ref_doc_it`

> ⚠️ `calc_tax_ind='X'` 时ME23N看不到发票凭证号，避免设置

### VMD_EI_API（供应商创建/修改）
```abap
" 供应商创建 - 使用类而非BAPI
DATA: lo_api TYPE REF TO vmd_ei_api.
CALL METHOD vmd_ei_api=>maintain_direct_input
  EXPORTING is_vendor = ls_vendor_data
  IMPORTING et_error  = lt_errors.
" 类似 CMD_EI_API 处理客户主数据
```

### ME_INFORECORD_MAINTAIN（采购信息记录PIR）
- `info_type`: 0=标准, 1=可记帐, 2=寄售, 3=分包合同, P=管道
- 判断新建/修改：查表 `EINA`（抬头）和 `EINE`（采购组织数据）
- 维护净价同时必须维护价格条件（`cond_validity` + `condition`），否则净价写不进去

---

## 六、采购订单配置要点

### 过量/不足交货控制优先级
优先级：**采购订单行项目 > 物料主数据采购价值码**

### 授权隐藏净价
删除用户权限对象 `M_BEST_BSA/EKG/EKO/WRK` 中的活动 `09`（显示价格）

### 发票校验基础配置
- `OMR6`：配置发票校验容差范围（金额差异、数量差异百分比）
- `MIRO`：创建发票校验凭证
- `MIR4`：显示发票凭证
- `MIR7`：预制发票（parking invoice）

---

## 七、关键数据表（MM专用）

| 表名 | 内容 |
|---|---|
| `EKKO` | 采购凭证抬头 |
| `EKPO` | 采购凭证行项目 |
| `EKBE` | 采购凭证历史（收货/发票关联）|
| `EBAN` | 采购申请 |
| `EINA` | 采购信息记录抬头 |
| `EINE` | 采购信息记录采购组织数据 |
| `MARA` | 物料主数据（客户端级）|
| `MARC` | 物料工厂数据 |
| `MARD` | 库位库存 |
| `MBEW` | 物料评估/库存价值 |
| `MKPF` | 物料凭证抬头 |
| `MSEG` | 物料凭证行项目 |
| `RBKP` | 发票凭证抬头（LIV）|
| `RSEG` | 发票凭证行项目（LIV）|
| `EKET` | 交货计划行 |
| `EKKN` | 采购凭证科目分配 |
| `LFA1` | 供应商主数据（一般）|
| `LFM1` | 供应商主数据（采购组织）|
| `T158G` | BAPI货物移动代码对应表 |
| `T161` | 采购凭证类型（BSTYP区分NB/UB）|
