# SAP 实战排查知识库

> 本文件收录从真实项目中提炼的问题排查案例，每条遵循「现象→根因→解决→经验总结」结构。
> 标签格式：`#模块 #关键词`

---

## CASE-001：OData API 创建工厂间 STO 报 "Exception raised without specific error"

**标签**：`#MM` `#OData` `#STO` `#S4HANA` `#增强`

**现象**
通过 Python 调用 `API_PURCHASEORDER_PROCESS_SRV` 创建采购订单，ZD30（公司间调拨，基于NB）成功，ZD06（工厂间调拨，基于UB）始终报 `Exception raised without specific error`，错误模糊无法定位。

**根本原因**
`API_PURCHASEORDER_PROCESS_SRV` 在 OData 框架层（`CL_MM_PUR_PO_CTR_ODATA_API`）内置了一个**前置校验**：只允许创建基于 **NB（标准采购订单）** 复制定义的订单类型。ZD06 基于 UB（调拨单），BSTYP = 'U'，触发消息 `APPL_MM_PUR_PO / 064`。

关键调用链：
```
OData POST → /IWBEP/框架 → CL_MM_PUR_PO_CTR_ODATA_API ← ★此处抛出064错误
                                                         ↓（通过后才到）
                                               ME_PROCESS_PO_CUST BAdI
```
**重要**：BAdI `ME_PROCESS_PO_CUST` 在校验通过后才触发，无法在此 BAdI 里绕过限制。

**定位方法**
- 通用 OData 错误信息往往被框架包装，真实错误藏在 `/IWBEP/SU_ERRLOG` 的 INSERT 操作里
- 开启 **ST05（SQL Trace）**，在 Python 执行 POST 期间记录，导出 Excel 后过滤 `/IWBEP/SU_ERRLOG` 的 INSERT 行，查看 `ERROR_TEXT` 字段即可看到真实错误消息

**解决方案（推荐顺序）**

★ **方案一：Enhancement Spot 隐式增强**（推荐，升级安全）

切入点：`CL_MM_PO_FEATURE_ENGINE` 类的 `IF_MM_PO_FEATURE_ENGINE~EXECUTE` 方法，在第38行 `ENDIF.` 之后加 After 增强：

```abap
" 如果是基于 UB 的工厂间调拨订单类型（如 ZD06），跳过 NB 类型校验
DATA: lv_bstyp   TYPE t161-bstyp,
      lv_doc_type TYPE bsart.
lv_doc_type = ms_purchase_order-data-bsart.
SELECT SINGLE bstyp INTO lv_bstyp FROM t161 WHERE bsart = lv_doc_type.
IF lv_bstyp = 'U'.
  DELETE lt_features WHERE feature_id = '<C_DT_NC_NB的实际常量值>'.
  IF lt_features IS INITIAL.
    RETURN.
  ENDIF.
ENDIF.
```
> ⚠️ `C_DT_NC_NB` 是类内私有常量，需在 SE24 Attributes 标签查看实际值，代码中用字面量。

方案二：新建自定义 OData 服务 `ZMMO_PO_SRV`，底层调 `BAPI_PO_CREATE1`（支持所有订单类型），Python 按订单类型路由不同服务 URL。

方案三：SPRO 修改 ZD06 参考凭证类型（有业务风险，需 MM 顾问验证）。

**经验总结**
1. OData 的 `Exception raised without specific error` 几乎必须用 ST05 定位，不要在 Python 层加日志，那拿不到真实错误
2. BAdI 触发时机决定了能否作为切入点——分析调用链是关键的第一步
3. 通过 `T161.BSTYP` 动态判断订单类型，比硬编码订单类型代码健壮，未来扩展免维护

---

## CASE-002：PI JDBC 接口排查方法论

**标签**：`#PI` `#集成` `#JDBC` `#IDoc` `#Proxy`

**现象**
PI JDBC 接口出问题，不知道从哪里入手找到 SAP 侧对应的 ABAP 程序或接口。

**根本原因**
PI 接口涉及多层对象（Channel → ICO → Interface → ABAP Program），方向不同（Inbound/Outbound）查找路径不同，需要系统性的反查方法。

**解决方案**

**场景 A：Inbound（外围 → SAP），已知 Sender JDBC Channel，找 ABAP 程序**
1. 在 PI Integration Directory 找到该 Channel 对应的 ICO
2. 查看 ICO 的 Receiver Interfaces 标签，获取 Inbound Service Interface 名称
3. SAP 侧：
   - Proxy 方式：`SPROXY` → 搜接口名 → 找 Implementing Class → 看 `EXECUTE` 方法
   - IDoc 方式：`WE20` → Partner Type LS → Inbound Parameters → Process Code → `WE42` 找 Function Module

**场景 B：Outbound（SAP → 外围），已知外围表名，找 PI 配置**
1. 在 PI ID 找到外围数据库的 Business Component
2. 查找 Receiver JDBC Channel，检查 SQL Statement 或 Table Name
3. 找到 ICO 后，从 Sender Interface 反查 SAP 侧 Proxy Class，再用 Where-Used List 找调用程序

**PI 监控事务码速查**
| 场景 | 事务码 | 用途 |
|---|---|---|
| Proxy/IDoc 消息监控 | SXMB_MONI / SXI_MONITOR | 查看 XML 消息状态、Payload、Trace |
| Web Service 底层传输 | SRT_UTIL | SOAP 接口底层错误 |
| tRFC 队列卡住 | SM58 | 出站 RFC 是否卡队列 |
| IDoc 状态 | WE02 / WE05 | IDoc 发送/接收状态 |

**经验总结**
先确定 Inbound 还是 Outbound，方向搞错查找路径完全不同。Proxy 方式是最常见的 SAP PI 接口模式，`SPROXY` + Where-Used List 是最快的反查路径。

---

## CASE-003：OData 接口报通用错误，/IWFND/ERROR_LOG 看不到真实原因

**标签**：`#OData` `#Gateway` `#调试` `#ST05`

**现象**
调用 SAP OData 服务（Python/Postman 等），返回通用错误如 "Exception raised without specific error" 或 "Internal Server Error"，查看 `/IWFND/ERROR_LOG` 只看到框架级别的包装异常，无法定位真实业务原因。

**根本原因**
SAP OData 框架（`/IWBEP/`）在抛出异常时，**真实业务错误被写入数据库表 `/IWBEP/SU_ERRLOG`**，而 `/IWFND/ERROR_LOG` 只记录了框架层面的外层包装错误，信息不足。所有框架内部校验失败（如业务规则、权限、数据一致性）都以这种方式被掩盖。

**定位方法**
ST05 SQL Trace 是定位 OData 框架内部错误的最可靠手段：
1. 打开 `ST05` → 勾选 SQL Trace → 开始追踪
2. 在外部客户端执行 OData 请求
3. 回到 `ST05` → 停止追踪 → 导出 Excel
4. 过滤 Table = `/IWBEP/SU_ERRLOG` 的 **INSERT** 操作
5. 查看 `ERROR_TEXT` 字段 — 这里是原始业务错误消息

**解决方案**
| 排查工具 | 用途 |
|---|---|
| `/IWFND/GW_CLIENT` | SAP 内置 OData 测试客户端，比外部工具能拿到更完整的响应 |
| `ST05` → `/IWBEP/SU_ERRLOG` | **定位真实错误的关键**，看 INSERT 行的 ERROR_TEXT |
| `/IWFND/ERROR_LOG` | 框架层异常，配合 ST05 交叉验证 |
| `/IWFND/MAINT_SERVICE` | 确认服务已激活并绑定正确系统别名 |

**经验总结**
OData 的 "Exception without specific error" 几乎必须用 ST05 + `/IWBEP/SU_ERRLOG` 定位，不要在客户端侧加日志（只能看到包装错误）。先用 `/IWFND/GW_CLIENT` 重现，再用 ST05 找根因。

---

## CASE-004：SAP 消息内容修改（T100 / OBA5 / OFMG）

**标签**：`#FI` `#消息控制` `#T100` `#ABAP`

**现象**
SAP 某功能执行时报错（Error 类消息），需要改为警告（Warning）使流程可继续；或标准消息文本不符合业务语言要求，需要修改。

**根本原因**
SAP 消息有三个独立维度：消息文本（T100）、消息严重级别（可通过配置覆盖，不修改代码）、是否触发消息（消息控制配置）。修改路径取决于目标：改文字 vs 改严重级别 vs 关闭消息，操作完全不同。

**定位方法**
1. 触发报错后，看消息弹窗左下角或按 F1 查看消息的"消息类"（Message Class）和"消息号"
2. 进 `SE91` 用消息类+消息号确认消息归属模块
3. 根据模块选择对应配置事务码

**解决方案**
| 目标 | 方法 |
|---|---|
| 改严重级别 E→W（FI 模块）| `OBA5` → 找消息类 → Online 列改为 W |
| 改严重级别（其他 FI 消息）| `OFMG` |
| 改消息文本 | `SE91` → 消息类/号 → 修改文本（改标准消息需 SAP 修改权限）|
| 关闭特定消息 | `OMRM`（MM发票校验）/`OMCQ`（库存管理）→ 消息号 → Online 选 `-` |
| 查消息文本存储 | `T100` 表（所有消息文本）、`T100C`（用户自定义覆盖）|

**经验总结**
FI 消息通过 OBA5 改严重级别是最安全的方式（配置，非代码），不要轻易修改 T100 中标准消息文本，升级时会被覆盖。

---

## CASE-005：Enhancement Spot 增强激活后无效果，或变量修改被后续代码覆盖

**标签**：`#ABAP` `#增强` `#Enhancement-Spot`

**现象**
在 SE24/SE38 中成功创建 Enhancement Spot 隐式增强并激活，但业务执行时增强逻辑没有生效；或增强代码对变量的修改在方法执行完成后被还原。

**根本原因**
有三种常见原因：
1. **位置选错**：After 增强可以访问和修改局部变量（局部变量在其作用域内仍有效），Before 增强只能读取/修改入参，对局部变量无效
2. **时机太晚**：标准代码在增强点**之后**对同一变量做了重新赋值，覆盖了增强的修改
3. **Replace 增强逻辑不完整**：Replace 完全替换原代码，如果没有在替换代码中完整复制并修改原始逻辑，方法行为残缺

**定位方法**
1. 先在标准代码中**直接修改**验证逻辑（仅开发/QAS环境，绝不上生产），确认逻辑本身正确
2. 在标准代码中打断点，追踪增强点前后变量的实际值变化
3. 找到变量被覆盖的具体位置，选择更合适的增强插入点

**解决方案**
- **After 增强**：适合在方法执行完后修改结果集（如修改 lt_features 等返回值）
- **Before 增强**：适合修改入参，在标准逻辑执行前影响处理
- **Replace 增强**：风险最高，避免使用；若必须，需完整复制原始逻辑再修改
- 命名规范：`ZENH_<对象名>_<功能描述>`，必须通过 CTS 传输（禁止直接在生产创建）

**经验总结**
选增强点之前，先把标准代码的执行流程看清楚——增强点之后是否还有代码覆盖目标变量？After 增强能访问局部变量，但前提是在局部变量作用域未退出时插入。

---

## CASE-006：寄售库存 MRKO 结算报消息错误

**标签**：`#MM` `#库存` `#寄售` `#消息控制`

**现象**
执行 `MRKO` 对寄售库存进行结算时，系统报错：
- `"没有发现税务信息"` 导致无法结算
- `"寄售结算: 未发现合作伙伴 &1/公司代码 &2 的消息"` 导致流程中断

**根本原因**
1. 第一个错误：采购信息记录（PIR）中未维护税码，MRKO 结算需要税码
2. 第二个错误：MRKO 结算时系统尝试向供应商发送 M8 443 号消息通知，但系统没有配置如何处理该消息

**解决方案**
1. 税务信息缺失 → `ME12` 打开采购信息记录，维护税码
2. M8-443 消息问题 → `OMRM` 新增一行：消息号=443，Online选择 `-`（关闭消息），Batch Input同样设置
   - 如只针对特定用户放行：在User字段指定用户名，其他人仍受限

**经验总结**
寄售业务是 MM 中的特殊库存场景，物权未转移前不需要发票校验；消息配置类问题用 `OMRM` 解决是标准方式，不要修改代码。

---

## CASE-007：MB_DOCUMENT_BADI 增强写入自建表数据无效

**标签**：`#MM` `#ABAP` `#BAdI` `#货物移动` `#增强`

**现象**
在 BAdI `MB_DOCUMENT_BADI` 的方法 `MB_DOCUMENT_BEFORE_UPDATE` 中编写逻辑，代码能执行，但数据没有写入自建表；或者在该方法中写了 `COMMIT WORK`，导致程序 Dump。

**根本原因**
`MB_DOCUMENT_BADI` 有两个关键方法，调用时机和用途不同：
- `MB_DOCUMENT_BEFORE_UPDATE`：在 UPDATE TASK 之前触发，**可以调试**（可打断点），但此时物料凭证号已确定，**不能写 COMMIT WORK**
- `MB_DOCUMENT_UPDATE`：实际写数据到数据库的方法，**无法打断点**，但数据修改在此提交

**解决方案**
1. 在 `MB_DOCUMENT_BEFORE_UPDATE` 中调试，验证逻辑正确
2. 将实际写入自建表的代码放到 `MB_DOCUMENT_UPDATE` 中（两个方法参数完全相同，直接复制代码）
3. 删除 `MB_DOCUMENT_BEFORE_UPDATE` 中的任何 `COMMIT WORK`

**经验总结**
`BEFORE_UPDATE` 用于调试，`UPDATE` 用于实际写数据——这是 SAP update task 机制决定的。两个方法参数相同是 SAP 刻意设计，方便调试后迁移代码。

---

## CASE-008：ME_INFORECORD_MAINTAIN 净价写入失败

**标签**：`#MM` `#BAPI` `#采购信息记录` `#PIR`

**现象**
调用函数模块 `ME_INFORECORD_MAINTAIN` 创建或修改采购信息记录（PIR）时，传入了 `i_eine-net_price`，但保存后查看 ME13，净价字段仍为空或未更新。

**根本原因**
维护采购视图的净价（`NET_PRICE`）字段时，SAP 要求必须**同时维护价格条件数据**，仅传 `i_eine-net_price` 参数是不够的。净价和价格条件记录（`KONP` 条件类型 `PB00`）是联动关系。

**解决方案**
同时传入以下三组参数：
1. `i_eine-net_price`、`price_unit`、`currency`、`orderpr_un`
2. `cond_validity`：包含工厂、有效期起止（`valid_to='99991231'`）
3. `condition`：条件记录（`cond_type='PB00'`, `cond_value=净价`）

**判断新建还是修改**：
- 抬头：查 `EINA`（供应商+物料），找到 `INFNR`（信息记录号）则为修改
- 采购组织数据：查 `EINE`（采购组织+工厂+info_type），找到 `INFNR` 则为修改

**经验总结**
SAP 的 BAPI/FM 很多隐含"联动参数"的设计，净价+条件是典型案例。遇到写入无效时，先查 SAP 文档或 SCN，看是否有这类隐性依赖。

---

---

## CASE-009：BAPI_OUTB_DELIVERY_CHANGE 修改后 BAdI 不触发
**标签**：`#SD` `#BAdI` `#交货单` `#BAPI`

**现象**  
调用 `BAPI_OUTB_DELIVERY_CHANGE` 修改交货单数据后，期望由 BAdI `LE_SHP_DELIVERY_UPDATE` 触发后续逻辑（如同步自定义表），但增强完全不执行。

**根本原因**  
该 BAdI 依赖 Business Function `LOG_LE_INTEGRATION` 的激活状态。未激活时，`BAPI_OUTB_DELIVERY_CHANGE` 走旧代码路径，不经过该 BAdI。

**解决方案**  
1. `SFW5` → 业务功能集 → 找到 `LOG_LE_INTEGRATION`
2. 激活该 Business Function（不可逆，须在测试系统验证后再做生产）
3. 激活后 `BAPI_OUTB_DELIVERY_CHANGE` 将触发 `LE_SHP_DELIVERY_UPDATE`

**经验总结**  
SD 物流增强 BAdI 很多依赖 Business Function 是否激活，出现增强不触发时先检查 `SFW5`，而非直接怀疑增强配置或断点位置。

---

## CASE-010：BAPI 创建 DN 后冲销发货报"不允许冲销分散系统相关"
**标签**：`#SD` `#BAdI` `#交货单` `#冲销`

**现象**  
通过 BAPI 批量创建的外向交货单（DN），在 `VL09` 冲销发货过账时报错：  
`不允许冲销分散系统相关` / `Reversal not allowed for decentralized-relevant items`

**根本原因**  
BAPI 创建 DN 时，内部程序设置了 `LIKP-VLSTK`（分散系统标识），使该交货单标记为"与分散 WM 系统相关"，冲销时系统校验此字段并拒绝。

**解决方案**  
在 BAdI `LE_SHP_DELIVERY_PROC` 的方法 `CHANGE_DELIVERY_HEADER` 中清空该标识：

```abap
METHOD change_delivery_header.
  " 清空分散系统标识，允许后续冲销
  cs_likp-vlstk = space.
ENDMETHOD.
```

**经验总结**  
BAPI 创建的 DN 与 VL01N 手工创建存在细微差异，部分标识字段（如 `VLSTK`）在 BAPI 路径下会被赋值，而手工路径不会。遇到 BAPI 创建数据后续操作报错时，对比手工路径的字段值。

---

## CASE-011：紧接 BAPI 创建 PO 后调用交货 BAPI 出错
**标签**：`#SD` `#MM` `#BAPI` `#STO` `#全局变量`

**现象**  
连续调用 BAPI：先 `BAPI_PO_CREATE1`（或 MM 采购订单），立即调用 `BAPI_OUTB_DELIVERY_CREATE_STO` 创建 STO 交货单，后者报错（数据异常/dump）。

**根本原因**  
`BAPI_PO_CREATE1` 调用后，SAP 内部全局变量 `GT_EKET_DOC[]`（采购订单交货计划行缓存）仍持有上一次调用的数据，未被清空。下一个 BAPI 调用时读到脏数据，产生逻辑错误。

**解决方案**  
在调用 `BAPI_OUTB_DELIVERY_CREATE_STO` 前，通过动态访问清空该全局变量：

```abap
" 清除前序 BAPI 残留全局变量
FIELD-SYMBOLS: <fs> TYPE ANY TABLE.
ASSIGN ('(SAPLME03)GT_EKET_DOC[]') TO <fs>.
IF sy-subrc = 0.
  CLEAR <fs>.
ENDIF.

" 使用 DESTINATION 'NONE' 保证 RFC 在同一 LUW 内
CALL FUNCTION 'BAPI_OUTB_DELIVERY_CREATE_STO'
  DESTINATION 'NONE'
  ...
```

**经验总结**  
SAP BAPI 之间存在全局变量污染问题，尤其是同一 LUW 内连续调用多个 BAPI 时。遇到第二个 BAPI 莫名出错，先排查全局变量残留；`DESTINATION 'NONE'` 可强制同一进程执行，减少 RFC 跨进程问题。

---

## CASE-012：GGB1 替换传输覆盖生产系统已有配置
**标签**：`#FI` `#替换` `#传输` `#配置风险`

**现象**  
将 FI 替换（Substitution）从配置系统传输到生产系统后，生产系统中其他团队维护的替换逻辑消失，相关功能异常。

**根本原因**  
在 `GGB1 → 替换 → 运输` 时，默认勾选了**"传输组"**选项。该选项会将配置系统中该应用区域的**整个集合**覆盖目标系统，而非只传输当前替换。

**解决方案**  
1. `GGB1` → 选择目标替换 → 菜单：替换 → 运输
2. 在弹出的传输对话框中，**取消勾选"传输组（Transport Group）"**
3. 仅传输当前替换，不影响目标系统其他集合成员

**经验总结**  
GGB1 的替换、验证均通过 Workbench 请求传输（非 Customizing 请求）。"传输组"选项默认打开，极易误操作覆盖生产配置。同类风险也存在于 `GB01`（验证）配置传输。团队内务必形成规范：传输前确认勾选状态。

---

## CASE-013：COPA 必输字段 BAPI 过账时不校验导致数据缺失
**标签**：`#FI` `#COPA` `#BAPI` `#增强`

**现象**  
在 KEPA/KE4G 将某 COPA 特征设为必输，前台 VA01/VF01 过账时正常报错拦截，但通过 BAPI（如 `BAPI_ACC_DOCUMENT_POST`）批量过账时不报错，导致 COPA 行项目中该特征值为空。

**根本原因**  
COPA 必输字段校验依赖**前台屏幕逻辑**，只有字段在屏幕上可见时才触发。BAPI 后台调用不经过屏幕逻辑，因此跳过必输检查。

**解决方案**  
在 COPA 增强出口 `EXIT_SAPLKEAB_001`（增强实现 `COPA0001`）中，对该特征值进行自行校验：

```abap
" 检查必填特征，防止 BAPI 绕过前台校验
IF ls_char_values-copa_value IS INITIAL.
  MESSAGE e001(zmsg) WITH '必填COPA特征值不可为空'.
ENDIF.
```

**经验总结**  
SAP 增强的必输校验很多依赖前台屏幕，BAPI 路径全部绕开。批量接口项目上线前必须针对 BAPI 路径单独测试每一个必输字段的校验逻辑，不能依赖配置层的必输设置。

---

## CASE-014：FBL1N 净付款到期日字段无法显示
**标签**：`#FI` `#FBL1N` `#用户参数` `#到期日`

**现象**  
在 FBL1N（供应商行项目）或 FBL5N（客户行项目）中，在布局中添加"净付款到期日（Net Due Date）"字段后，该列显示为空或无法选中，无数据。

**根本原因**  
SAP 通过用户参数 ID `FIT_DUE_DATE_SEL` 控制是否计算并显示净到期日。该参数默认未设置，系统不计算净到期日字段。

**解决方案**  
1. `SU3`（或 `SU01`）→ 参数标签页
2. 新增参数：
   - 参数ID：`FIT_DUE_DATE_SEL`
   - 值：`X`
3. 保存 → 重新执行 FBL1N/FBL5N

**经验总结**  
SAP 中不少字段的显示受用户参数控制（而非字段状态或权限），遇到字段存在但始终为空的情况，应检查 `SU3` 中的相关参数 ID。常见类似参数还有 `BUS_EXT`（业务合作伙伴扩展显示）等。

---

## CASE-015：MIGO 移动类型 309 序列号重复报错

**标签**：`#PM` `#序列号` `#MIGO` `#库存管理`

**现象**  
MIGO 执行物料间调拨（移动类型 309，含序列号）时，系统报错：  
`Serial number X already exists for material Y`  
过账被拒绝，无法完成物料调拨。

**根本原因**  
移动类型 309 将序列号随库存一起转移到目标物料。若目标物料下已存在相同序列号（即使状态为已存档），系统认为序列号重复，禁止过账。

**解决方案**  
方案一（归档冲突序列号）：
1. `IQ03` 查看目标物料下的冲突序列号状态
2. `IQ04` 将冲突序列号归档（状态变为 IACT）
3. 重新执行 MIGO 过账

方案二（修改序列号归属）：
1. `IQ02` 打开冲突序列号
2. 菜单 → Edit → Special serial no. functions
3. 修改序列号编号或所属物料号，消除冲突
4. 重新执行 MIGO 过账

**经验总结**  
移动类型 309 不同于普通库存移动，带序列号时会严格校验目标物料下序列号唯一性。排查时先用 `IQ09`（序列号清单）确认冲突序列号所在物料及状态，再选择归档或变更两种解法。序列号归档（IACT 状态）不影响历史记录，是最安全的处理方式。

---

> **贡献新案例格式**：
> ```
> ## CASE-NNN：问题标题
> **标签**：`#模块` `#关键词`
> **现象**：用户操作什么，系统报什么
> **根本原因**：为什么（最核心）
> **解决方案**：可执行步骤
> **经验总结**：规律性认识
> ```
