# SD 模块知识库（销售与分销）

---

## 一、常用事务码

### 销售订单
| 事务码 | 用途 |
|---|---|
| `VA01/VA02/VA03` | 创建/更改/显示销售订单 |
| `V.02` | 不完整订单清单 |
| `V_RA` | 拖欠订单处理：选择清单 |
| `V_V2` | 拖欠订单处理：按物料更新销售凭证 |
| `V_SA` | 汇总处理分析 |

### 交货与运输
| 事务码 | 用途 |
|---|---|
| `VL01N` | 创建外向交货（带订单参考）|
| `VL02N` | 更改外向交货 |
| `VL03N` | 显示外向交货 |
| `VL06O` | 外向交货监控 |
| `VL06I` | 内向交货 |
| `VL10CUA` | 货运到期清单 |
| `OVL3` | 交货计划配置 |

### 开票
| 事务码 | 用途 |
|---|---|
| `VF01/VF02/VF03` | 创建/更改/显示发票 |
| `VF04` | 合并开票清单 |
| `VFX3` | 批准发票凭证传到会计 |
| `VF31` | 发票输出处理 |
| `VF44` | 单独价格更正 |

### 信贷管理
| 事务码 | 用途 |
|---|---|
| `FD32` | 客户信贷控制 |
| `F.28` | 信贷重建 |
| `VKM1~VKM4` | 冻结/批准信贷SD凭证 |
| `CO09` | 可用性总览/MRP元素 |
| `CO06` | 拖欠订单处理 |

### 主数据
| 事务码 | 用途 |
|---|---|
| `XD01/XD02/XD03` | 创建/更改/显示客户（含销售视图）|
| `VAP1/VAP2/VAP3` | 创建/更改/显示联系人 |
| `MSC1N/MSC2N/MSC3N` | 创建/更改/显示批量 |
| `VELO` | 车辆管理 |

### 配置
| 事务码 | 用途 |
|---|---|
| `VOFM` | 维护例程、需求与公式 |
| `VK11/VK12` | 维护/更改条件记录 |
| `V/LD` | 执行定价报表 |
| `OVK1/OVK3/OVK4` | 税确定规则/客户税码/物料税码 |
| `BUBA/BUPT` | 业务合作伙伴配置 |

---

## 二、关键数据表

### 销售订单
| 表名 | 内容 |
|---|---|
| `VBAK` | 销售凭证抬头 |
| `VBAP` | 销售凭证行项目 |
| `VBEP` | 计划行（交货计划）|
| `VBKD` | 业务数据（付款条件等）|
| `VBPA` | 合作伙伴（售达方/送达方等）|
| `VBUK` | 单据抬头状态 |
| `VBUP` | 单据行项目状态 |
| `VBFA` | 单据流（销售→交货→开票）|

### 交货与发票
| 表名 | 内容 |
|---|---|
| `LIKP` | 交货单抬头 |
| `LIPS` | 交货单行项目 |
| `VBRK` | 发票抬头 |
| `VBRP` | 发票行项目 |
| `VKDFS` | SD索引：开票发起方 |
| `VEPVG` | 交货到期索引 |

### 客户主数据
| 表名 | 内容 |
|---|---|
| `KNA1` | 客户基本数据（客户端级）|
| `KNB1` | 客户公司代码数据 |
| `KNVV` | 客户销售组织数据 |
| `KNVP` | 客户合作伙伴功能 |
| `KNVK` | 客户联系人 |
| `KNKK` | 客户信贷控制数据（含信贷限额）|
| `KNVI` | 客户税标识 |

### 定价
| 表名 | 内容 |
|---|---|
| `PRCD_ELEMENTS` | 单据定价条件（S/4）|
| `KONV` | 单据定价条件（ECC，已废弃）|
| `KONH/KONP` | 条件主数据抬头/行项（AXXX 表）|

### 信贷
| 表名 | 内容 |
|---|---|
| `S066` | 未清订单信贷管理 |
| `S067` | 未清交货/发票（信贷管理）|

> ⚠️ `KNKK` 中的应收值不一定准确，需与 `BSID` 核对；`S066/S067` 不准时执行 F.28 重建

---

## 三、主要 BAPI 速查

### BAPI_SALESORDER_CREATEFROMDAT2（创建销售订单）
关键结构：`ORDER_HEADER_IN`（抬头）、`ORDER_ITEMS_IN`（行项）、`ORDER_PARTNERS`（合作伙伴）、`ORDER_SCHEDULES_IN`（计划行）、`ORDER_CONDITIONS_IN`（条件）

```abap
" 合作伙伴结构 - 必填4种功能
order_partners-partn_role = 'AG'.  " 售达方
order_partners-partn_role = 'RE'.  " 收票方
order_partners-partn_role = 'RG'.  " 付款方
order_partners-partn_role = 'WE'.  " 送达方

" LOGIC_SWITCH 定价控制 - 仅支持 ' BCG'，自定义条件类型用BDC
" 来自发票的退货单(Price Type E)无法用BAPI，需用BDC
```

### BAPI_BILLINGDOC_CREATEMULTIPLE（合并开票）
对应 `VF04`。按 `fkara+vkorg+kunnr` 分组，分两阶段：测试运行（`testrun='X'`）→ 正式过账。

### BAPI_OUTB_DELIVERY_CONFIRM_DEC（交货过账确认）
对应 `VL02N` PGI 操作。

### BAPI_OUTB_DELIVERY_CHANGE（修改交货单）
> ⚠️ 需激活 Business Function `LOG_LE_INTEGRATION` 才能触发 BAdI `LE_SHP_DELIVERY_UPDATE`

### BAPI_OUTB_DELIVERY_CREATE_STO（STO交货单创建）
紧接 BAPI_PO创建后调用会报错，解决方法：

```abap
" 使用 DESTINATION 'NONE' 并清除全局变量
FIELD-SYMBOLS <fs>.
ASSIGN ('(SAPLME03)GT_EKET_DOC[]') TO <fs>.
IF sy-subrc = 0.
  CLEAR <fs>.
ENDIF.
```

---

## 四、增强点速查

### 交货单保存增强
| 增强类型 | 名称 | 触发点 |
|---|---|---|
| BAdI | `LE_SHP_DELIVERY_PROC` → `SAVE_AND_PUBLISH_DOCUMENT` | 保存按钮 |
| Enhancement Spot | `LE_SHP_DELIVERY_UPDATE` | 交货单更新 |
| BAdI | `LE_SHP_PRICING` | 交货单定价 |

**场景**：BAPI 创建的 DN 冲销发货报"不允许冲销分散系统相关"  
**解决**：在 `LE_SHP_DELIVERY_PROC → CHANGE_DELIVERY_HEADER` 中清空 `cs_likp-vlstk = space`

### 销售订单增强（Include程序）
| 程序 | Form/增强点 | 用途 |
|---|---|---|
| `MV45AFZB` | `USEREXIT_CHECK_VBAP` | 行项目保存检查 |
| `MV45AFZB` | `USEREXIT_SOURCE_DETERMINATION` | 存储地点确定 |
| `MV45AFZZ` | `USEREXIT_MOVE_FIELD_TO_VBAK` | 抬头字段赋值 |
| `MV45AFZZ` | `USEREXIT_MOVE_FIELD_TO_VBAP` | 行项目字段赋值 |
| `MV45AFZZ` | `USEREXIT_SAVE_DOCUMENT_PREPARE` | 保存前检查 |
| `MV50AFZ1` | `USEREXIT_SAVE_DOCUMENT` | 交货单保存（调用PRICING_COMPLETE）|

**保存报错屏幕无法编辑时** 在报错前加：
```abap
fcode = 'ENT1'.
PERFORM FOLGE_GLEICHSETZEN(SAPLV00F).
SET SCREEN SYST-DYNNR. LEAVE SCREEN.
```

### 发票到会计增强（SMOD: SDVFX001~SDVFX011）
| 出口 | 用途 |
|---|---|
| `SDVFX008` | 转移结构 SD-FI 的处理（最常用）|
| `SDVFX004` | 总分类帐行用户出口 |
| `SDVFX006` | 税行用户出口 |

### 自定义字段更新 DN（BAPI_OUTB_DELIVERY_CHANGE）
**BAdI**: `SMOD_V50B0001` → `EXIT_SAPLV50I_010`  
通过 `extension2` 参数更新 LIKP（row 0）和 LIPS（row 1-n）自定义字段

---

## 五、合作伙伴确定

### 配置路径
`SPRO → 销售与分销 → 基本功能 → 合作伙伴确定 → 设置合作伙伴确定`

### 标准合作伙伴功能
| 功能 | 说明 |
|---|---|
| `AG` | 售达方（Sold-to Party）|
| `WE` | 送达方（Ship-to Party）|
| `RE` | 收票方（Bill-to Party）|
| `RG` | 付款方（Payer）|

### 配置层级
1. **合作伙伴功能** → 定义功能代码、伙伴类型（KU/LI）
2. **合作伙伴确定过程** → 将功能分配到过程
3. **过程分配** → 绑定到客户账户组（主数据）或销售凭证类型（订单）
4. **账户组-功能分配** → 控制哪些功能可在该账户组出现

---

## 六、定价与税务

### MWST vs MWSI 核心区别
| 条件类型 | 计算类型 | 公式 | 适用场景 |
|---|---|---|---|
| `MWST` | A（百分数）| 价格 × 税率 | 价外税（不含税价）|
| `MWSI` | H（含手续费）| [价格÷(1+税率)] × 税率 | 价内税（含税价）|

**示例**（税率17%，订单金额1000）：
- MWST: 税额=170，价税合计=1170
- MWSI: 税额=145.30，不含税=854.70，价税合计=1000

### 税务配置步骤
```
OBQ1  → 维护税确定程序
OBCN  → 维护税过账码（T007B）
FTXP  → 维护税码（按国家+程序）
OB40  → 科目确定（税程序 → 科目）
VK11  → 维护税条件主数据
```

### SD税配置路径
- `OVK1`：定义税确定规则（国家维度）
- `OVK3`：维护客户税码（客户主数据 → KNVI）
- `OVK4`：维护物料税码（物料主数据 → 销售组织1）

> 订单税分类取自**送达方**客户税分类，非售达方

---

## 七、信贷管理（S/4 HANA）

### S/4 HANA FSCM 信贷管理关键变化
- ECC：OVA8 自动信贷控制
- S/4：BP 角色 `UKM000` 替代 FD32，使用信贷档案和信贷分段（`UKM_SEGMENT`）

### 配置步骤
1. 创建信贷分段（Credit Segment）
2. 创建信贷组并分配到销售凭证类型/交货类型
3. 激活 BAdI（自动信贷控制）
4. 客户主数据中分配 BP 角色 UKM000

### 信贷数据关键表
| 表名 | 内容 |
|---|---|
| `KNKK` | 信贷限额、应收总额、特别往来 |
| `S066` | 未清订单金额（信贷用）|
| `S067` | 未清交货/发票金额（信贷用）|

> ⚠️ `KNKK` 应收值可能不准 → 对比 `BSID`；S066/S067 不准 → F.28 重建

---

## 八、公司间交易

### 利润中心替代（常见场景）
**问题**：公司间销售时，利润中心需根据销售组织+产品组确定  
**方案**：利用替代出口（GGB1）实现

```
GCX2   → 定义应用区域 GBLS，分配 U204 自定义程序
GGB1   → 创建替代（应用GBLS），调用出口 ZRGGBS00（基于 RGGBS000 复制）
OKB9   → 默认利润中心分配（科目级别）
```

**自定义逻辑**：读取 ZTFIZZPRCTR（销售组织+产品组 → 利润中心映射表）

---

## 九、ATP 可用性检查

### 核心概念
- **Checking Group**（检查组）：在物料主数据销售视图维护
- **Checking Rule**：A=订单，B=交货
- **Scope of Check**：由 Checking Group + Rule 决定检查哪些库存/需求元素

### 关键事务码
| 事务码 | 用途 |
|---|---|
| `CO09` | 可用性总览/MRP元素明细 |
| `CO06` | 拖欠订单处理 |
| `V_V2` | 按物料更新拖欠订单（重新确认）|

### 排程逻辑
- **后向排程**：从需求日期往前推，计算物料可用日期
- **前向排程**：当后向排程不可行时，从今天往后推确认日期
- 关键时间点：物料可用日期 → 拣配日期 → 装载日期 → 运输计划日期 → 交货日期

---

## 十、MTO 变式可配置 BOM

### 实现步骤
```
CT04  → 创建特征（Characteristics）
CL02  → 创建分类（Classification）
CU01  → 创建依赖关系（Dependencies）
CS01  → 创建超级BOM（Super BOM，物料类型 KMAT）
CU41  → 维护配置文件（Configuration Profile）
CU50  → 测试配置
CS40  → 将普通物料与可配置物料关联
```

**物料类型**：`KMAT`（可配置物料），策略组 `25`

**依赖关系示例**：
```
条件：Z101 = 'Z1' 时选择特定 BOM 组件
```

**客户下单**：VA01 中在行项目中选择特征值，系统自动确定 BOM 组件

---

## 十一、交货业务

### 存储地点确定规则
| 规则 | 说明 |
|---|---|
| `MALA` | 工厂+发货点组合确定 |
| `RETA` | 根据情景（如 WM 转移订单）确定 |
| `MARE` | MALA 找不到时回退 |

### 发货点确定（OVL3）
路径：`SPRO → 物流执行 → 发货 → 基本发货功能 → 发货点和仓储条件`  
**关键字段**：装运条件（销售订单）+ 装载组（物料）+ 工厂

### 交货自动创建控制
字段 `TVAK-LISOF`：订单类型配置，`A` = 触发自动交货  
**增强**：`USEREXIT_SAVE_DOCUMENT_PREPARE`（MV45AFZZ）中清空 `TVAK-LISOF` 可按条件关闭

---

## 十二、科目确定（SD→FI）

### 核心配置路径
- `VKOA`：SD 科目确定（收入科目、销售折扣等）
- `OBXW`：对账科目确定（客户调节科目）

### 特殊总账标识集成
开票过账到 FI 时使用特殊 GL 标识（如预付款）：
- `ZXVVFU08`（用户出口）或 BTE `1120` 修改过账码和科目

---

## 十三、开票合并与分割

### 合并条件（标准）
同一 Payer、付款条件、开票日期、Incoterms → 合并为同一张发票

### 分割控制（VTFL 复制控制）
- VOFM 中 `DATEN_KOPIEREN_*` 例程控制哪些字段触发分割
- 字段 `VBRK-ZUKRI`：强制分割标准（如 SPART、VTWEG、WERKS）

```abap
" 自定义分割条件（KNA1-KATR7 按客户主数据字段分割）
" 在 VOFM → 数据传输例程 中添加自定义字段到 AUSNAHME_TAB
```

### 行项目数限制
标准上限 999 行，超出通过复制控制路由或限制订单行项目数控制

### 中国税务合规
每张发票需控制最大行项目数和最大金额（金税要求），通过用户出口实现
