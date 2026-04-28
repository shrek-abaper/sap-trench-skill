# SAP VMS（车辆管理系统）知识库

VMS 是 SAP IS-AUTO（汽车行业解决方案）的车辆管理模块，用于管理车辆全生命周期。

---

## 一、VELO 系统关键对象

| 对象 | 说明 |
|---|---|
| Package | `ISAUTO_VLC` |
| 函数组 | `VELO09` |
| Action 配置 | `CVLC03`（配置 Action 对应的标准程序操作）|
| IDoc 分配 | `VLCIDGU`（VELO: Vehicle to IDoc Number Assignment）|

---

## 二、VLC_VEHICLE_IDOC BAdI 实现

**用途**：通过 IDoc 附加字段更新车辆主数据表 `VEHICLE`

**BAdI 名称**：`VLC_VEHICLE_IDOC`

**两个方法实现顺序**：

### 方法 1：GET_ADDITIONAL_SEGMENTS

将 segments 传入参数 `data_iv` 复制（Append）给 `velo_data_ct`

```abap
" 示意：在 GET_ADDITIONAL_SEGMENTS 实现中
APPEND iv_data TO ct_velo_data.
```

### 方法 2：GET_ADDITIONAL_CHANGES

将 `velo_data_ct` 传入参数值赋给 `vehicle_idoc_ct`

```abap
" 示意：在 GET_ADDITIONAL_CHANGES 实现中
ct_vehicle_idoc = ct_velo_data.
```

---

## 三、附加数据增强配置路径

```
SPRO → 后勤执行 → VMS → 增强 → 定义车辆附加数据
```

用于定义 Action 可更新的车辆附加字段（对应数据库表 `VEHICLE` 中的扩展字段）。

---

## 四、关键说明

- VMS Action 通过 `CVLC03` 配置，Action 编号与标准程序操作一一对应
- IDoc 增强需同时实现 `GET_ADDITIONAL_SEGMENTS`（读 IDoc → 内表）和 `GET_ADDITIONAL_CHANGES`（内表 → 更新车辆主数据）两个方法，缺一不可
- 附加数据字段需先在 SPRO 定义后，BAdI 方法才能正确传递
