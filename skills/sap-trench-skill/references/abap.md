# ABAP 开发知识库

---

## 一、增强实现体系

### 增强类型速查

| 类型 | 适用场景 | 升级风险 | 典型事务码 |
|---|---|---|---|
| 第一代：User Exit | ECC老系统，USEREXIT_开头子程序 | 低 | SE38 查 INCLUDE |
| 第二代：SMOD/CMOD | SAP预留的增强点，多组件管理 | 低 | SMOD / CMOD |
| 第三代：BAdI | 有明确接口的业务扩展点 | 低 | SE18 / SE19 |
| 第四代：BTE | FI业务事件触发 | 低 | FIBF |
| Enhancement Spot | BAdI时机不对，或需深入标准方法内部 | 中 | SE24 / SE38 |
| Modification | 最后手段，直接改标准代码 | 高（需Modification Assistant）| SE38 |

### 第二代增强 SMOD/CMOD 查找方法

**通过程序找增强点**：
1. `SE93`：由事务码找到程序名
2. `SE11` 查表 `TADIR`（PGMID=`R3TR`, OBJECT=`PROG`, OBJ_NAME=程序名）→ 找开发类
3. `SE11` 再查 `TADIR`（PGMID=`R3TR`, OBJECT=`SMOD`, DEVCLASS=开发类）→ 找增强点
4. 在 `MODSAP` 表中查增强类型（S=屏幕, C=菜单, E=功能, T=表）

**通过源代码找增强点**：
- 在标准程序中搜 `CALL CUSTOMER` → 找到增强出口调用位置 → `SE11` 查 `MODSAP`
- 前台操作时 `/H` 触发调试，设置断点，按 F8 找到 `CALL CUSTOMER` 调用

**CMOD 实施步骤**：
1. `CMOD` → 创建项目 → 增强分配（分配增强点名）→ 组件（实施具体EXIT）
2. 进入组件 → 双击EXIT FM名称 → 双击INCLUDE程序名 → 按回车创建对象
3. 编写代码，保存激活

> 出口Function参数前缀：**X** = 更改后新数据，**Y** = 更改前旧数据

**注意**：同一个EXIT函数出口不能重复建立项目，重复引用只需在INCLUDE中添加代码。

### Enhancement Spot 操作步骤
1. 在 SE24 / SE38 中定位目标代码行
2. 菜单：`Edit → Enhancement Operations → Add Enhancement`
3. 选择位置：Before / After / Replace
4. 填写 Enhancement Implementation 名称（建议：`ZENH_<对象>_<功能>`）
5. 写增强代码，保存激活，创建传输请求

**可访问的变量范围**：
- After 增强：可读写方法的局部变量（包括 `lt_features` 等内部表）
- Before 增强：可读写入参
- Replace 增强：完全替换，需复制全部原代码

### BAdI 实现步骤
1. `SE18`：查看 BAdI 定义，了解接口方法和参数
2. `SE19`：创建 BAdI 实现，选择 BAdI 名称，创建实现类
3. 实现类继承接口，实现目标方法
4. 激活，在 `SE19` 中激活 BAdI 实现

**BAdI 查找方法**：在程序中搜索 `CL_EXITHANDLER` → 找到 `IF_EX_BADI_<...>` 接口 → `SE18` 搜接口名

> BAdI里面出现 message type 为 E 会导致程序 Dump，需用 W/I 类型。

**常用 BAdI 速查**：
| BAdI | 模块 | 用途 |
|---|---|---|
| `ME_PROCESS_PO_CUST` | MM | PO 创建/修改时增强（在OData校验之后触发）|
| `ME_PROCESS_REQ_CUST` | MM | PR 增强 |
| `BADI_SD_V50_ORDER` | SD | 销售订单增强 |
| `AC_DOCUMENT` | FI | 会计凭证增强 |

---

## 二、性能优化要点

### 核心原则（14条）

```abap
" 1. 使用WHERE语句（避免全表读取后CHECK过滤）
SELECT * FROM zflight WHERE airln = 'LF' AND fligh = '222'.

" 2. 使用聚合函数（避免全表扫后逐行比较）
SELECT MAX( fligh ) FROM zflight INTO maxnu WHERE airln = 'LF'.

" 3. 使用视图替代多表Join嵌套
SELECT * FROM zcnfl WHERE cntry LIKE 'IN%' AND airln = 'LF'.

" 4. 使用INTO TABLE代替SELECT...ENDSELECT
SELECT * FROM zflight INTO TABLE int_fligh.

" 5. 批量修改内表（避免LOOP逐行MODIFY）
int_fligh-flag = 'X'.
MODIFY int_fligh TRANSPORTING flag WHERE flag IS INITIAL.

" 6. 二分法查询（READ前需SORT BY KEY）
READ TABLE int_fligh WITH KEY airln = 'LF' BINARY SEARCH.

" 7. 批量追加内表
APPEND LINES OF int_fligh1 TO int_fligh2.

" 8. FOR ALL ENTRIES替代LOOP内嵌SELECT（驱动表不能为空！）
IF lt_ekko IS NOT INITIAL.
  SELECT * FROM ekpo INTO TABLE lt_ekpo
    FOR ALL ENTRIES IN lt_ekko
    WHERE ebeln = lt_ekko-ebeln.
ENDIF.

" 9. 使用INNER JOIN（优于嵌套循环+READ TABLE）
SELECT a~airln b~fligh INTO TABLE int_airdet
  FROM zairln AS a INNER JOIN zflight AS b ON a~airln = b~airln.

" 10. 使用SORT BY代替ORDER BY（数据库层排序开销更高）
" 11. 用SORT + DELETE ADJACENT DUPLICATES替代SELECT DISTINCT
" 12. WHERE字段顺序匹配索引字段顺序
" 13. MOVE语句整行移动，避免MOVE-CORRESPONDING逐字段
" 14. Table Buffering：SELECT DISTINCT/FOR UPDATE/ORDER BY/JOIN会绕过缓存
```

### ST05 SQL 追踪（定位OData / RFC内部错误）
1. `ST05` → `Activate Trace`（选 SQL Trace）
2. 执行目标操作（OData请求、业务操作等）
3. `ST05` → `Deactivate Trace`
4. `Display Trace` → 导出Excel → 过滤目标表（如 `/IWBEP/SU_ERRLOG`）
5. 查看 INSERT 操作的 VALUES 字段，找真实错误信息

### 内表类型选择
```abap
" HASHED TABLE：用于大量 READ TABLE ... WITH KEY 操作（O(1)查找）
DATA: lt_hash TYPE HASHED TABLE OF ztype WITH UNIQUE KEY key_field.

" SORTED TABLE：用于 LOOP ... WHERE 和范围读取（自动排序，O(log n)查找）
DATA: lt_sorted TYPE SORTED TABLE OF ztype WITH NON-UNIQUE KEY key_field.
```

---

## 三、ABAP 基本语法速查

### 数据类型
| 类型 | 说明 | 示例 |
|---|---|---|
| `C` | 字符串，位数不足右补空格 | `DATA: lv_name(10) TYPE C.` |
| `D` | 日期，格式YYYYMMDD | `'19991203'`，空值=`'00000000'` |
| `F` | 浮点数，长度8 | — |
| `I` | 整数 | — |
| `N` | 数值字符串，不足补前导0 | `'011'`, `'302'` |
| `P` | 压缩十进制，用于小数 | `DATA: lv_amt TYPE P DECIMALS 2.` |
| `T` | 时间，格式HHMMSS | `'140300'` |
| `X` | 16进制 | `'1A03'` |

> 判断日期字段为空：`DEAKT = '00000000'`（8个0），不是 `''` 也不是 `IS INITIAL`

### 系统变量（SY-* / SYST结构）
| 变量 | 说明 |
|---|---|
| `SY-SUBRC` | 上一指令执行状态（0=成功）|
| `SY-UNAME` | 当前登录用户名 |
| `SY-DATUM` | 当前系统日期 |
| `SY-UZEIT` | 当前系统时间 |
| `SY-TCODE` | 当前事务码 |
| `SY-LANGU` | 当前登录语言 |
| `SY-MANDT` | 当前Client |
| `SY-INDEX` | 当前LOOP循环次数 |
| `SY-TABIX` | 当前处理内表的行号 |

### TYPES vs LIKE
- `TYPES`：定义新数据类型（抽象）；`LIKE`：参照已有变量；`TYPE`：参照数据类型

---

## 四、常用系统表

### 通用系统表
| 表名 | 内容 |
|---|---|
| `DD02L` | SAP 表定义（透明表清单）|
| `DD03L` | 字段定义 |
| `TADIR` | 版本库对象目录（查对象所属包/传输）|
| `E071` | 传输请求对象清单 |
| `TSTC` | 事务码定义表 |
| `T000` | Client 定义 |
| `MODSAP` | SAP Enhancement表（查增强点类型）|
| `T100` | 消息文本 |
| `T100C` | 用户自定义消息配置（OBA5等写入此表）|

### MM 相关表
| 表名 | 内容 |
|---|---|
| `MARA` | 物料主数据（客户端级）|
| `MARC` | 工厂级物料主数据 |
| `MARD` | 库存地点库存 |
| `MAKT` | 物料描述 |
| `EKKO` | 采购凭证抬头 |
| `EKPO` | 采购凭证行项目 |
| `EKBE` | 采购凭证历史 |
| `T161` | 采购凭证类型（BSTYP字段区分NB/UB等）|
| `MSEG` | 物料凭证行项目 |
| `MKPF` | 物料凭证抬头 |
| `MBEW` | 物料评估/库存价值 |
| `EBAN` | 采购申请 |
| `EINA` | 采购信息记录一般数据 |
| `EINE` | 采购信息记录采购组织数据 |
| `RBKP` | 发票凭证抬头 |
| `RSEG` | 发票凭证行项目 |

### SD 相关表
| 表名 | 内容 |
|---|---|
| `VBAK` | 销售凭证抬头 |
| `VBAP` | 销售凭证行项目 |
| `VBUK` | 凭证抬头状态 |
| `VBUP` | 凭证行项目状态 |
| `LIKP` | 交货单抬头 |
| `LIPS` | 交货单行项目 |

### FI 相关表
| 表名 | 内容 |
|---|---|
| `BKPF` | 会计凭证抬头 |
| `BSEG` | 会计凭证行项目 |
| `SKA1` | 总账科目（科目表级）|
| `SKB1` | 总账科目（公司代码级）|

---

## 五、消息处理

### 消息类型
| 类型 | 说明 |
|---|---|
| `I` | 信息窗口（Information）|
| `W` | 警告（Warning）|
| `E` | 错误（Error）|
| `S` | 成功（Success）|
| `A` | 终止程序（Abort）|

### 消息配置事务码（按模块）
| 模块 | 事务码 | 用途 |
|---|---|---|
| FI | `OBA5` | FI消息控制（改E→W）|
| FI | `OFMG` | FM消息控制 |
| MM | `O04C` | 采购消息控制 |
| MM | `OMRM` | 发票校验消息 |
| MM | `OMCQ` | 库存管理系统消息（M7消息）|
| MM | `OMT4` | 物料主数据系统消息 |
| SD | `OVAH` | SD定义可变消息 |
| 通用 | `SE91` | 消息维护/创建消息类 |
| 通用 | `MSW1/MSW2` | 重置警告消息 |

### 修改消息严重级别（FI模块）
1. `OBA5`：FI应用程序消息控制，可将E（Error）改为W（Warning）或空（忽略）
2. 修改后写入 `T100C` 表，可通过 `SE16N` 验证

### 读取消息配置的代码
```abap
CALL FUNCTION 'READ_CUSTOMIZED_MESSAGE'
  EXPORTING
    i_arbgb = i_arbgb
    i_dtype = i_dtype
    i_msgnr = i_msgnr
  IMPORTING
    e_msgty = l_msgty.
IF l_msgty NE '-'. " 如果没有关闭消息
```

### 自定义消息类
1. `SE91`：创建消息类（Message Class），命名Z开头，如 `ZMM_MSG`
```abap
MESSAGE e001(zmm_msg) WITH lv_param1.
" 或
MESSAGE ID 'ZMM_MSG' TYPE 'E' NUMBER '001' WITH lv_param1.
```

---

## 六、调试与时区/参数配置

### 常用调试事务码
| 事务码 | 用途 |
|---|---|
| `SE24` | Class Builder，查看和修改ABAP类 |
| `SE38` | ABAP Editor |
| `SE37` | Function Module |
| `SE18` / `SE19` | BAdI定义 / BAdI实现 |
| `SE93` | 事务码属性（找程序名）|
| `SM50` | 当前进程监控（找死循环/挂死请求）|
| `SM66` | 全系统进程监控 |
| `ST22` | ABAP Dump分析 |
| `SU53` | 权限检查失败分析 |
| `ATC` | ABAP Test Cockpit代码质量检查 |

### 时区设置
- `STZAC`：时区快捷设置（NetWeaver级，适用所有SAP系统）
- `SU01/SU3`：维护用户时区（Default → Time Zone）
- `SM30` 维护表 `TTZCU`：系统时区
- IMG路径：SAP NetWeaver → General Settings → Set Countries → Time Zone Settings

> 系统时区控制过帐期间，用户时区控制界面显示的日期时间。

### 用户参数（Parameter ID）设置
设置用户常用字段默认值（如公司代码），避免每次手动输入：
1. System → User Profile → Own Data → Parameters
2. 获取参数ID：在目标字段按 `F1` → 技术信息 → 查看 Parameter ID（如公司代码=`BUK`）
3. 在Parameters视图输入ID和默认值，保存
