# SAP 集成技术知识库（PI / IDoc / Proxy / OData）

---

## 一、PI/PO 接口排查路径

### 确定接口方向（最先做）
- **Inbound**：外围系统 → SAP（SAP 是接收方）
- **Outbound**：SAP → 外围系统（SAP 是发送方）

方向搞错，排查路径完全相反。

### Inbound 排查路径（外围 → SAP）
```
Sender Channel (JDBC/HTTP/File)
  ↓ PI Integration Directory
Integrated Configuration (ICO)
  ↓ Receiver Interfaces 标签
Inbound Service Interface（名称+命名空间）
  ↓ SAP 侧
  ├── Proxy 方式：SPROXY → 搜接口名 → Implementing Class → EXECUTE 方法
  ├── IDoc 方式：WE20 → LS → Inbound Parameters → Process Code → WE42 → FM
  └── RFC 方式：检查 Channel 是否关联 RFC → SE37
```

### Outbound 排查路径（SAP → 外围）
```
已知：外围表名 / 业务操作
  ↓
PI ID → 外围 Business Component → Receiver Channel
  ↓
ICO → Inbound Processing → Sender Service Interface
  ↓ SAP 侧
  ├── Proxy 方式：SPROXY 搜 Sender Interface → Proxy Class → Where-Used List → 调用程序
  └── IDoc 方式：WE20 → LS → Outbound Parameters → Message Type → NACE / MASTER_IDOC_DISTRIBUTE
```

---

## 二、PI/ESR 与 Integration Directory（ID）的区别

| 层 | 对象 | 说明 |
|---|---|---|
| **ESR（Enterprise Service Repository）** | Service Interface | 定义接口结构（XSD/WSDL），与业务系统无关 |
| **ESR** | Message Type / Data Type | 定义消息格式 |
| **ESR** | Mapping | 定义源→目标结构转换逻辑 |
| **ID（Integration Directory）** | Business Component | 具体业务系统实例（如 SAP ECC、外围DB）|
| **ID** | Communication Channel | 技术连接配置（JDBC/HTTP/File URL等）|
| **ID** | Integrated Configuration (ICO) | 将 ESR 接口定义绑定到 ID 中的实际Channel |

> **核心区别**：ESR是"设计时"（接口定义、mapping），ID是"配置时"（谁连谁、如何传输）。排查问题先看ID里的Channel是否激活，再看ESR里的Mapping是否正确。

---

## 三、PI 监控事务码

| 事务码 | 用途 |
|---|---|
| `SXMB_MONI` / `SXI_MONITOR` | Integration Engine 消息监控（Proxy/IDoc），看 XML Payload 和 Trace |
| `SRT_UTIL` | Web Service 监控，调试 SOAP 底层传输错误 |
| `SM58` | tRFC 队列监控，看出站 RFC 是否卡住 |
| `WE02` / `WE05` | IDoc 列表，查发送/接收状态 |
| `WE20` | Partner Profile，配置 IDoc 合作伙伴 |
| `WE42` | Inbound Process Code，找处理 IDoc 的 Function Module |
| `NACE` | 输出消息控制（触发 IDoc 的入口配置）|
| `SPROXY` | Enterprise Service Repository，管理和查看 Proxy 对象 |

---

## 四、OData 服务开发和调试

### 关键事务码
| 事务码 | 用途 |
|---|---|
| `/IWFND/MAINT_SERVICE` | OData 服务注册、激活、分配系统别名 |
| `/IWFND/GW_CLIENT` | SAP 内置 OData 测试客户端（比 Postman 更能拿到真实错误）|
| `/IWFND/ERROR_LOG` | Gateway 错误日志，含完整调用堆栈 |
| `ST05` | SQL 追踪，定位 OData 框架内部真实错误（必备）|

### OData 错误定位最佳实践
1. **模糊错误（Exception raised without specific error）**：99% 需要 ST05 定位
   - 开启 ST05 → 执行 OData 请求 → 停止追踪 → 导出 Excel
   - 过滤 `/IWBEP/SU_ERRLOG` 的 INSERT 操作，查看 `ERROR_TEXT` 字段
2. **Gateway 层错误**：查 `/IWFND/ERROR_LOG`
3. **业务逻辑错误**：在 `/IWFND/GW_CLIENT` 重现后，对实现类打断点

### OData V2 vs V4（S/4HANA）
- ECC：只有 OData V2（`/IWBEP/` 框架）
- S/4HANA 1709+：引入 OData V4（RAP 框架）
- 标准 API：`API_*_SRV` 基本都是 V2，RAP 自定义服务是 V4

---

## 五、IDoc 开发要点

### IDoc 类型三要素
1. **Basic Type**（基本类型）：IDoc 结构定义，如 `ORDERS05`
2. **Message Type**（消息类型）：业务语义，如 `ORDERS`
3. **Process Code**（处理代码）：将消息类型映射到处理 FM

### Inbound IDoc 处理 FM 查找
`WE20` → Partner Type LS → Inbound Parameters → Message Type → Process Code → `WE42` → Function Module

### Outbound IDoc 触发方式
1. **消息控制（NACE）**：最常见，业务操作（如保存 PO）触发输出类型，再触发 IDoc
2. **直接调用**：程序调 `MASTER_IDOC_DISTRIBUTE` 或 `ALE_CREATE_AND_SEND_IDOC`
3. **Change Pointer**：配置变更指针，数据变更自动触发

### IDoc 状态码关键值
| 状态 | 含义 | 处理方向 |
|---|---|---|
| 03 | 已发送到应用 | 正常 |
| 12 | 成功发送给合作伙伴 | 正常 Outbound |
| 51 | 应用处理出错 | 看 Error Message，通常业务数据问题 |
| 53 | 已成功过账 | 正常 Inbound |
| 64 | 已移交给通信层（等待发送）| 查 SM58 |

---

## 六、ABAP Proxy 开发

### Proxy 对象类型
- **Service Consumer（消费方）**：SAP 调外部，生成 `CO_` 开头的类
- **Service Provider（提供方）**：外部调 SAP，生成 `CL_` 开头的接口实现类，需要实现 `EXECUTE` 方法

### 同步 vs 异步 Proxy
- **同步（Synchronous）**：调用方等待返回，方法：`call_via_destination` 或直接实例化调用
- **异步（Asynchronous）**：调用方不等，方法：`EXECUTE_ASYNCHRONOUS`，消息进 `SXMB_MONI`

### Proxy 调用的典型代码模式
```abap
DATA: lo_proxy TYPE REF TO co_<proxy_class_name>.
CREATE OBJECT lo_proxy
  EXPORTING logical_port_name = 'DEFAULT'.  " 在 SOAMANAGER 配置

DATA: ls_request TYPE <request_structure>.
CALL METHOD lo_proxy-><method_name>
  EXPORTING input  = ls_request
  IMPORTING output = ls_response.
```

---

## 七、JSON 与 XML 处理

### JSON 处理（/ui2/cl_json）

#### 基本用法
```abap
" JSON → ABAP结构（反序列化）
/ui2/cl_json=>deserialize(
  EXPORTING json = lv_json
  CHANGING  data = ls_result ).

" ABAP → JSON（序列化）
DATA(lv_json) = /ui2/cl_json=>serialize( data = ls_data ).

" 处理嵌套JSON（动态访问节点）
DATA: lr_data TYPE REF TO data.
FIELD-SYMBOLS: <data> TYPE data, <field> TYPE any.
lr_data = /ui2/cl_json=>generate( json = lv_json ).
ASSIGN lr_data->* TO <data>.
ASSIGN COMPONENT 'RESPONSE' OF STRUCTURE <data> TO <field>.
```

#### 节点名称映射（支持中文/转换大小写）
```abap
" NAME_MAPPINGS 参数：ABAP字段名 <-> JSON节点名映射表
DATA: lt_mappings TYPE /ui2/cl_json=>name_mappings,
      lv_json     TYPE string.

" 定义映射：abap = ABAP字段名，json = JSON中的节点名（支持中文/任意字符）
lt_mappings = VALUE #(
  ( abap = 'NAME'  json = '姓名' )
  ( abap = 'AGE'   json = '年龄' )
  ( abap = 'PHONE' json = '电话' )
).

" 反序列化：JSON → ABAP（带节点名映射）
/ui2/cl_json=>deserialize(
  EXPORTING json          = lv_json
            name_mappings = lt_mappings
  CHANGING  data         = ls_result ).

" 序列化：ABAP → JSON（带节点名映射）
lv_json = /ui2/cl_json=>serialize(
  data          = ls_data
  name_mappings = lt_mappings
).
```

> **重要**：`NAME_MAPPINGS` 是解决中文节点名称的原生方法，无需预处理JSON或使用动态结构

### XML ↔ 内表转换
- SAP默认最外层节点：`<DATA></DATA>`
- 内表行项目默认节点：`<item></item>`（小写）
- 使用类 `cl_xml_document`（内表→XML）和 `cl_xml_document_base`（XML→内表）

### CALL TRANSFORMATION（XSLT / Simple Transformation）
```abap
" XML → ABAP
CALL TRANSFORMATION <trans_name>
  SOURCE XML lv_xml
  RESULT obj = ls_result.

" ABAP → XML
CALL TRANSFORMATION <trans_name>
  SOURCE obj = ls_source
  RESULT XML lv_xml.

" 支持类型：
" XML ↔ XML (XSLT only)
" XML ↔ ABAP (XSLT 和 Simple Transformation)
" ABAP ↔ ABAP (XSLT only, 6.20+)
```

---

## 八、常见集成错误速查

| 现象 | 定位工具 | 可能根因 |
|---|---|---|
| Proxy 调用无响应 | `SXMB_MONI` / `SXI_MONITOR` | 消息卡在 Integration Engine，看 Error Detail |
| IDoc 状态 51（应用错误）| `WE02` → 看 Error Message | 业务数据问题（如物料不存在），按报错修数据 |
| IDoc 状态 64（等待发送）| `SM58` | tRFC 队列卡住，检查 RFC 连接和对方系统 |
| OData POST 报通用错误 | `ST05` → `/IWBEP/SU_ERRLOG` | 框架层校验失败，用 ST05 找真实错误文本 |
| JDBC Channel 消息失败 | PI Channel Monitoring | 检查 SQL语句/目标表是否存在，检查 JDBC Driver |
| Proxy 消息报 Authentication | `SOAMANAGER` | Logical Port 的认证方式或 credentials 未配置 |
| Web Service 调用超时 | `SRT_UTIL` | 对方服务无响应，或 ICF 服务未激活（`SICF`）|

> **排查总原则**：先确定接口方向（Inbound/Outbound），再确定协议类型（Proxy/IDoc/RFC/JDBC），不同组合对应完全不同的工具链。方向搞错，查找路径完全相反。
