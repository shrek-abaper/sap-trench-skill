# SAP 打印设计知识库（SmartForms / SAPscript / Adobe Forms）

---

## 一、打印技术选型

| 技术 | 适用场景 | 备注 |
|---|---|---|
| **SmartForms** | ECC 主流表单技术，推荐 | 图形化设计器，ABAP 代码嵌入 |
| **SAPscript** | 旧系统遗留，维护场景 | 基于 SE71，语法复杂，避免新建 |
| **Adobe Forms** | S/4HANA 交互式表单 | SFP 维护，PDF 输出，支持签名 |

> 新开发优先选 SmartForms（ECC）或 Adobe Forms（S/4HANA）。SAPscript 只在老项目维护。

---

## 二、SmartForms 打印程序标准模板

### 数据声明
```abap
DATA: lv_ssf_name  TYPE tdsfname VALUE 'ZMM_FORM_NAME',
      lv_fm_name   TYPE rs38l_fnam.

DATA: lw_control  TYPE ssfctrlop.
DATA: lw_options  TYPE ssfcompop.
```

### Step 1 — 获取 SmartForms 对应函数名
```abap
CALL FUNCTION 'SSF_FUNCTION_MODULE_NAME'
  EXPORTING  formname = lv_ssf_name
  IMPORTING  fm_name  = lv_fm_name.   " 动态生成的函数名
```

### Step 2 — SSF_OPEN：初始化打印会话
```abap
CALL FUNCTION 'SSF_OPEN'
  EXPORTING
    user_settings      = space          " 必须传 space，否则网络打印机无效
    output_options     = lw_options
    control_parameters = lw_control
  EXCEPTIONS
    formatting_error = 1
    internal_error   = 2
    send_error       = 3
    user_canceled    = 4
    OTHERS           = 5.

IF sy-subrc <> 0.
  MESSAGE ID sy-msgid TYPE sy-msgty NUMBER sy-msgno
    WITH sy-msgv1 sy-msgv2 sy-msgv3 sy-msgv4.
ENDIF.
```

### Step 3 — 调用 SmartForms 函数（循环打印主体）
```abap
CALL FUNCTION lv_fm_name
  EXPORTING
    control_parameters = lw_control
    output_options     = lw_options
    " ... 业务数据参数
  EXCEPTIONS
    formatting_error = 1
    internal_error   = 2
    send_error       = 3
    user_canceled    = 4
    OTHERS           = 5.
```

### Step 4 — SSF_CLOSE：提交打印
```abap
CALL FUNCTION 'SSF_CLOSE'
  EXCEPTIONS
    formatting_error = 1
    internal_error   = 2
    send_error       = 3
    user_canceled    = 4
    OTHERS           = 5.
```

---

## 三、打印控制参数详解（TYPE ssfctrlop）

| 参数 | 预览模式 | 网络打印 | 说明 |
|---|---|---|---|
| `no_dialog` | `''` | `'X'` | `'X'` = 不弹出打印对话框 |
| `preview` | `'X'` | `''` | `'X'` = 显示打印预览 |
| `no_open` | `'X'` | `'X'` | 通常置 `'X'`，由程序自己调 SSF_OPEN |
| `no_close` | `'X'` | `'X'` | 多页合并打印时置 `'X'`，循环完再 CLOSE |
| `langu` | `'1'` | `'1'` | 语言代码（`'1'`=中文，`'E'`=英文）|

```abap
" 预览模式（开发调试用）
lw_control-no_dialog = ''.
lw_control-preview   = 'X'.
lw_control-no_open   = 'X'.
lw_control-no_close  = 'X'.
lw_control-langu     = '1'.

" 网络打印机静默打印
lw_control-no_dialog = 'X'.
lw_control-preview   = ''.
lw_control-no_open   = 'X'.
lw_control-no_close  = 'X'.
lw_control-langu     = '1'.
```

---

## 四、输出选项参数详解（TYPE ssfcompop）

| 参数 | 说明 |
|---|---|
| `tddest` | 打印设备短名（如 `'ZIHP'`），对应 SPAD 中的设备名 |
| `tdprinter` | 设备类型名（如 `'HP5100'`）|
| `tdimmed` | `'X'` = 立即打印（不进假脱机队列）|
| `tddelete` | `'X'` = 打印后删除假脱机请求 |
| `tdnewid` | `'X'` = 每次创建新的假脱机请求 |
| `tdnoprev` | `'X'` = 无打印预览（与 `no_dialog` 配合）|
| `tdfinal` | `'X'` = 假脱机请求完成标记 |

```abap
" 网络打印机典型配置
lw_options-tddest    = 'ZIHP'.
lw_options-tdprinter = 'HP5100'.
lw_options-tdimmed   = 'X'.
lw_options-tddelete  = 'X'.
lw_options-tdnewid   = 'X'.
```

---

## 五、多数据/多页合并打印模式

```abap
" 初始化一次打印会话
CALL FUNCTION 'SSF_OPEN' ...

" 循环调用多次（每次处理一条数据）
LOOP AT lt_orders INTO ls_order.
  lw_control-no_close = 'X'.   " 保持会话开放
  CALL FUNCTION lv_fm_name
    EXPORTING ...
ENDLOOP.

" 全部完成后关闭会话
CALL FUNCTION 'SSF_CLOSE' ...
```

---

## 六、NACE 输出控制配置

NACE 是 SAP 输出确定（消息控制）的核心事务码，控制何时触发打印。

### 配置路径
`NACE` → 选择应用（如 `EF` = 采购订单）→ 输出类型 → 处理程序/表单

### 关键配置表
| 表名 | 内容 |
|---|---|
| `TNAPR` | 程序和表单配置（SAPscript/SmartForms 绑定）|
| `T682` | 输出条件过程 |
| `T685` | 输出类型定义 |

### 调试技巧
1. 先在 `NACE` 确认输出类型和对应打印程序
2. `SE38` 直接打开打印程序设断点
3. 临时改 `lw_control-preview = 'X'` 查看预览，调完改回

---

## 七、常见错误与处理

| 错误 / sy-subrc | 原因 | 解决方向 |
|---|---|---|
| `send_error = 3` | 网络打印机不通或设备名错 | 查 SPAD，确认 tddest 存在且联通 |
| `formatting_error = 1` | SmartForms 布局问题 | 进 SmartForms 事务检查日志 |
| 预览弹窗关不掉 | `no_close='X'` + `SSF_CLOSE` 未调用 | 确认循环外调用了 SSF_CLOSE |
| 网络打印无效果 | `user_settings` 未传 `space` | SSF_OPEN 中加 `user_settings = space` |

---

## 八、相关事务码

| 事务码 | 用途 |
|---|---|
| `SMARTFORMS` | SmartForms 设计器 |
| `SFP` | Adobe Forms 设计器 |
| `SE71` | SAPscript 表单维护 |
| `SE78` | SAPscript 图形管理 |
| `NACE` | 输出消息配置（触发打印的入口）|
| `SPAD` | 假脱机管理/打印机配置 |
| `SP01` | 假脱机请求监控（查打印结果）|
| `SO10` | 标准文本维护 |

---

> **调试快捷方法**：开发时临时设置 `lw_control-preview = 'X'`（预览模式），可在不连接打印机的情况下验证表单布局。验证完成后改回静默打印配置。针式打印机场景注意在 SPAD 中配置正确的设备类型（Device Type），格式不匹配会导致字符错位。
