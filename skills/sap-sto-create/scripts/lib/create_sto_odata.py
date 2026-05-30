#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SAP STO 订单创建脚本 - OData 版本
通过 S/4HANA OData API 创建量产工厂与售后工厂之间的调拨订单
"""

import os
import json
import uuid
import logging
import platform
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Tuple, Optional, Any
from urllib.parse import urljoin
import requests
from requests.auth import HTTPBasicAuth

# 配置日志
log_level = os.environ.get("SAP_STO_LOG_LEVEL", "CRITICAL").upper()
logging.basicConfig(level=getattr(logging, log_level, logging.CRITICAL))
logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv

    # 尝试加载 .env 文件
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

# 工厂定义
PRODUCTION_PLANTS = {
    "P001": "量产工厂 P001",
    "P002": "量产工厂 P002",
    "P003": "量产工厂 P003",
    "P004": "量产工厂 P004",
    "P005": "量产工厂 P005",
}

SERVICE_PLANTS = {
    "A001": "售后工厂 A001",
    "A002": "售后工厂 A002",
}

# 库位默认值
DEFAULT_SERVICE_LOCATION = "0001"

# S/4HANA OData 服务路径
ODATA_PO_SRV = "/sap/opu/odata/sap/API_PURCHASEORDER_PROCESS_SRV/"
ODATA_PRODUCT_SRV = "/sap/opu/odata/sap/API_PRODUCT_SRV/"

# 一次性确认标识文件（用户级，跨进程共享）
# 每次 preview 生成，create 时立即消耗（无论成败），确保每次提交都需重新确认
TOKEN_FILE = Path.home() / ".sap_sto_confirm_token.json"


def validate_batch_number(batch_number: str) -> Tuple[bool, str]:
    if not batch_number or not batch_number.strip():
        return False, "批次号（--batch-number）不能为空，请提供本次创建 STO 的业务批次号"
    if len(batch_number.strip()) > 14:
        return False, (
            f"批次号长度不能超过14位，当前长度 {len(batch_number.strip())} 位：'{batch_number}'"
        )
    return True, ""


def _generate_confirmation_token() -> Tuple[bool, str]:
    if TOKEN_FILE.exists():
        try:
            existing = json.loads(TOKEN_FILE.read_text())
            created_at = datetime.fromisoformat(existing["created_at"])
            age_minutes = (datetime.now() - created_at).total_seconds() / 60
            if age_minutes <= 30:
                return False, (
                    "检测到另一个会话的 preview 操作尚未完成（确认标识仍有效），"
                    "不建议同一用户同时处理多个 STO 创建。"
                    "请等待其他会话完成后再操作，"
                    f"或手动删除 {TOKEN_FILE} 后重试。"
                )
        except Exception:
            pass  # 标识文件损坏，允许覆盖

    token_data = {
        "token": str(uuid.uuid4()),
        "created_at": datetime.now().isoformat(),
    }
    try:
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(json.dumps(token_data))
    except Exception as e:
        logger.warning(f"写入确认标识文件失败: {e}")
    return True, ""


def _validate_and_consume_confirmation_token() -> Tuple[bool, str]:
    """必须在调用 SAP OData 之前执行。无论后续成败，标识均已消耗。"""
    if not TOKEN_FILE.exists():
        return False, (
            "未找到有效的确认标识——请先运行 preview 命令预览订单信息，"
            "经用户明确确认后再执行 create"
        )
    try:
        token_data = json.loads(TOKEN_FILE.read_text())
        # 立即消耗：先删除，确保无论后续发生什么都不可再用
        try:
            TOKEN_FILE.unlink()
        except FileNotFoundError:
            pass
        except Exception as del_err:
            logger.warning(f"删除确认标识文件失败（继续执行）: {del_err}")

        created_at = datetime.fromisoformat(token_data["created_at"])
        age_minutes = (datetime.now() - created_at).total_seconds() / 60
        if age_minutes > 30:
            return False, (
                "确认标识已过期（超过30分钟），请重新运行 preview 命令生成新的预览"
            )
        return True, ""
    except Exception as e:
        try:
            TOKEN_FILE.unlink()
        except Exception:
            pass
        return False, f"确认标识验证失败: {e}"


class S4HanaODataClient:
    """S/4HANA OData 客户端"""

    def __init__(self):
        self.base_url = os.environ.get("SAP_URL", "").rstrip("/")
        self.username = os.environ.get("SAP_USER", "")
        self.password = os.environ.get("SAP_PASSWORD", "")
        self.client = os.environ.get("SAP_CLIENT", "800")
        self.language = os.environ.get("SAP_LANG", "EN")
        self.csrf_token = None
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(self.username, self.password)

        if not self.base_url or not self.username or not self.password:
            missing = [
                name for name, val in [
                    ("SAP_URL", self.base_url),
                    ("SAP_USER", self.username),
                    ("SAP_PASSWORD", self.password),
                ] if not val
            ]
            raise ValueError(f"缺少必要环境变量: {', '.join(missing)}")

        self.auth = HTTPBasicAuth(self.username, self.password)
        logger.info(f"S/4HANA OData 客户端已初始化: {self.base_url}")

    def _get_csrf_token(self, service_path: str) -> str:
        """获取 CSRF Token"""
        url = urljoin(self.base_url, service_path)
        headers = {"x-csrf-token": "fetch", "Accept": "application/json"}

        response = self.session.get(
            url,
            headers=headers,
            verify=False,
            params={"sap-client": self.client, "sap-language": self.language},
        )
        response.raise_for_status()
        return response.headers.get("x-csrf-token", "")

    def _get(self, service_path: str, params: Optional[Dict] = None) -> Dict:
        """GET 请求"""
        url = urljoin(self.base_url, service_path)
        headers = {"Accept": "application/json"}

        if params is None:
            params = {}
        params.update({"sap-client": self.client, "sap-language": self.language})

        response = self.session.get(url, headers=headers, verify=False, params=params)
        response.raise_for_status()
        return response.json()

    def _post(self, service_path: str, data: Dict) -> Dict:
        """POST 请求"""
        csrf_token = self._get_csrf_token(service_path)
        url = urljoin(self.base_url, service_path)
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-csrf-token": csrf_token,
        }

        response = self.session.post(
            url,
            headers=headers,
            json=data,
            verify=False,
            params={"sap-client": self.client},
        )

        # 不使用 raise_for_status()，统一处理错误
        if response.status_code not in [200, 201]:
            error_msg = f"HTTP {response.status_code} Error"

            # 尝试解析错误响应
            try:
                error_data = response.json()
                logger.error(f"完整响应数据: {error_data}")
                if "error" in error_data:
                    error_msg = (
                        error_data["error"].get("message", {}).get("value", error_msg)
                    )

                # 尝试获取更详细的错误信息
                if "d" in error_data and "Result" in error_data["d"]:
                    result_data = error_data["d"]
                    if result_data.get("Message"):
                        error_msg = result_data["Message"]

                # 提取详细的业务错误信息
                if "error" in error_data and "innererror" in error_data["error"]:
                    inner_error = error_data["error"]["innererror"]
                    if "errordetails" in inner_error:
                        error_details = inner_error["errordetails"]
                        detailed_errors = []
                        for detail in error_details:
                            code = detail.get("code", "")
                            message = detail.get("message", "")
                            severity = detail.get("severity", "error")
                            if message:
                                detailed_errors.append(
                                    {
                                        "code": code,
                                        "message": message,
                                        "severity": severity,
                                    }
                                )

                        if detailed_errors:
                            # 构建详细的错误消息
                            error_messages = []
                            for detail in detailed_errors:
                                severity_icon = (
                                    "❌" if detail["severity"] == "error" else "⚠️"
                                )
                                error_messages.append(
                                    f"{severity_icon} [{detail['code']}] {detail['message']}"
                                )
                            error_msg = "\\n".join(error_messages)

            except Exception as parse_error:
                logger.error(f"解析错误响应失败: {parse_error}")
                logger.error(f"原始响应文本: {response.text[:500]}")
                pass

            raise Exception(error_msg)

        # 检查业务错误
        try:
            json_response = response.json()
            if "error" in json_response:
                raise Exception(json_response["error"]["message"]["value"])

            # 检查是否有业务消息
            if "d" in json_response:
                d_data = json_response["d"]
                if "Message" in d_data and d_data["Message"]:
                    logger.warning(f"业务消息: {d_data['Message']}")
        except Exception as check_error:
            logger.warning(f"检查业务错误失败: {check_error}")

        return response.json()

    def get_material_unit(self, material: str) -> Optional[str]:
        """
        获取物料单位
        使用 API_PRODUCT_SRV 服务
        """
        try:
            # 过滤产品: Product eq '物料编码'
            filter_param = f"Product eq '{material}'"
            result = self._get(
                ODATA_PRODUCT_SRV + "A_Product",
                params={"$filter": filter_param, "$select": "BaseUnit"},
            )

            if (
                "d" in result
                and "results" in result["d"]
                and len(result["d"]["results"]) > 0
            ):
                return result["d"]["results"][0]["BaseUnit"]

        except Exception as e:
            logger.warning(f"获取物料 {material} 单位失败: {e}")

        return None

    def get_material_units_batch(self, materials: List[str]) -> Dict[str, str]:
        units = {}
        for material in materials:
            unit = self.get_material_unit(material)
            if unit:
                units[material] = unit
            else:
                units[material] = "EA"
                logger.warning(f"物料 {material} 使用默认单位 EA")
        return units

    def check_batch_number_exists(self, batch_number: str) -> Tuple[bool, List[str]]:
        filter_param = f"SupplierRespSalesPersonName eq '{batch_number}'"
        result = self._get(
            ODATA_PO_SRV + "A_PurchaseOrder",
            params={
                "$filter": filter_param,
                "$select": "PurchaseOrder",
                "$top": "5",
            },
        )
        if "d" in result and "results" in result["d"]:
            existing = result["d"]["results"]
            if existing:
                po_numbers = [r.get("PurchaseOrder", "") for r in existing]
                return True, [p for p in po_numbers if p]
        return False, []

    def create_purchase_order(self, order_data: Dict) -> Dict:
        try:
            doc_type = order_data["doc_type"]
            supplier = (
                f"000000{order_data['supply_plant']}" if doc_type == "ZSTO_T1" else ""
            )

            po_data = {
                "PurchaseOrderType": doc_type,
                "Supplier": supplier,
                "SupplyingPlant": order_data["supply_plant"],
                "CompanyCode": order_data["company_code"],
                "PurchasingOrganization": "C002",
                "PurchasingGroup": "001",
                "SupplierRespSalesPersonName": order_data.get("batch_number", ""),
                "to_PurchaseOrderItem": {"results": []},
            }

            # 添加行项目
            for idx, item in enumerate(order_data["items"], 1):
                po_item = {
                    "PurchaseOrderItem": str(idx * 10),
                    "Material": item["material"],
                    "OrderQuantity": str(item["quantity"]),
                    "PurchaseOrderQuantityUnit": item["unit"],
                    "Plant": item.get("plant", "A001"),
                }

                # 交货日期通过日程行传递
                if item.get("delivery_date"):
                    po_item["to_ScheduleLine"] = {
                        "results": [
                            {
                                "ScheduleLine": "1",
                                "DelivDateCategory": "1",
                                "ScheduleLineDeliveryDate": to_sap_odata_date(
                                    item["delivery_date"]
                                ),
                                "ScheduleLineOrderQuantity": str(item["quantity"]),
                            }
                        ]
                    }

                # 接收工厂是售后工厂需要库位
                if item.get("storage_location"):
                    po_item["StorageLocation"] = item["storage_location"]

                po_data["to_PurchaseOrderItem"]["results"].append(po_item)

            # 发送请求
            result = self._post(ODATA_PO_SRV + "A_PurchaseOrder", po_data)

            # 返回采购订单号
            if "d" in result and "PurchaseOrder" in result["d"]:
                return {
                    "success": True,
                    "po_number": result["d"]["PurchaseOrder"],
                    "messages": [],
                }

        except Exception as e:
            logger.error(f"创建采购订单失败: {e}")
            error_message = str(e)

            # 分析错误消息并给出具体的处理建议
            suggest = "请检查 S/4HANA OData 服务配置和权限"

            if "not maintained in plant" in error_message:
                suggest = "物料在供应工厂中没有维护主数据，请：1) 确认物料在供应工厂中已创建主数据；2) 使用该物料有主数据的工厂作为供应工厂"
            elif "No sales and distribution data" in error_message:
                suggest = "物料缺少销售与分销数据，请在物料主数据中维护销售视图数据"
            elif "special procurement type" in error_message:
                suggest = "物料使用特殊采购类型，请检查物料的MRP类型和特殊采购类型配置"
            elif "Purchase order still contains faulty items" in error_message:
                suggest = "采购订单包含有问题的行项目，请检查物料的可用性配置"
            elif "Supplier" in error_message:
                suggest = "供应商数据存在问题，请检查供应商主数据和工厂分配"

            return {
                "success": False,
                "po_number": None,
                "messages": [{"type": "E", "message": error_message}],
                "suggest": suggest,
            }

        return {
            "success": False,
            "po_number": None,
            "messages": [{"type": "E", "message": "未知错误"}],
        }


# 工厂类型判断函数
def get_plant_type(plant_code: str) -> Optional[str]:
    """判断工厂类型: 'production' 或 'service'，返回None表示无效"""
    if plant_code in PRODUCTION_PLANTS:
        return "production"
    elif plant_code in SERVICE_PLANTS:
        return "service"
    return None


def _resolve_jco_lib_dir(java_dir: Path) -> Path:
    """解析 JCo 本地库目录，按优先级选取：

    1. SAP_JCO_LIB_PATH 环境变量（显式覆盖）
    2. lib/<platform>/ 平台子目录（linux / macos / windows）
    3. lib/ 平底目录（向后兼容）
    """
    env_lib = os.environ.get("SAP_JCO_LIB_PATH", "").strip()
    if env_lib:
        p = Path(env_lib)
        if not p.is_absolute():
            skill_root = Path(__file__).parent.parent.parent
            p = skill_root / p
        return p

    system = platform.system().lower()
    if system == "darwin":
        system = "macos"
    platform_dir = java_dir / "lib" / system
    if platform_dir.exists():
        return platform_dir

    return java_dir / "lib"


def create_outbound_delivery(po_number: str) -> Tuple[bool, str, Optional[str]]:
    java_dir = Path(__file__).parent / "java"
    source_file = java_dir / "SapDeliveryCreator.java"
    class_file = java_dir / "SapDeliveryCreator.class"
    jar_file = java_dir / "sapjco3.jar"
    lib_dir = _resolve_jco_lib_dir(java_dir)
    cp_sep = ";" if platform.system() == "Windows" else ":"
    classpath = f"{java_dir}{cp_sep}{jar_file}"

    if not source_file.exists():
        logger.warning("Java 交货单创建脚本不存在，跳过交货单创建")
        return False, "Java 脚本不存在", None

    if not class_file.exists():
        logger.info("Java 类文件不存在，尝试编译...")
        try:
            subprocess.run(
                ["javac", "-classpath", classpath, str(source_file)],
                check=True, capture_output=True, text=True
            )
            logger.info("Java 脚本编译成功")
        except subprocess.CalledProcessError as e:
            logger.error(f"Java 脚本编译失败: {e.stderr}")
            return False, f"Java 脚本编译失败: {e.stderr}", None
        except FileNotFoundError:
            logger.warning("javac 不可用，跳过编译")
            return False, "JDK 未安装，无法编译 Java 脚本", None

    env_file = Path(__file__).parent.parent.parent / ".env"
    env = os.environ.copy()
    if env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
            env = os.environ.copy()
        except ImportError:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env[key.strip()] = value.strip()

    try:
        logger.info(f"正在为采购订单 {po_number} 创建外向交货单...")
        result = subprocess.run(
            [
                "java",
                "-classpath", classpath,
                f"-Djava.library.path={lib_dir}",
                "SapDeliveryCreator",
                po_number,
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(java_dir),
        )

        if result.returncode == 0:
            output = result.stdout
            logger.debug(f"Java 输出: {output}")
            delivery_number = None
            for line in output.split('\n'):
                if '交货单号:' in line:
                    parts = line.split('交货单号:')
                    if len(parts) > 1:
                        delivery_number = parts[1].strip()
                        break
            if not delivery_number:
                lines = [line.strip() for line in output.split('\n') if line.strip()]
                for line in reversed(lines):
                    if (line.isdigit() or len(line) == 10) and '交货单号' not in line and '===' not in line:
                        delivery_number = line
                        break
            if delivery_number:
                logger.info(f"外向交货单创建成功: {delivery_number}")
                return True, "外向交货单创建成功", delivery_number
            else:
                logger.info("Java 执行成功（未解析到交货单号）")
                return True, "外向交货单创建成功", None
        else:
            error_msg = result.stderr.strip() if result.stderr else "未知错误"
            logger.error(f"Java 执行失败: {error_msg}")
            return False, f"Java 执行失败: {error_msg}", None

    except subprocess.TimeoutExpired:
        logger.error("Java 执行超时")
        return False, "Java 执行超时", None
    except FileNotFoundError:
        logger.warning("java 命令不可用，跳过外向交货单创建")
        return False, "JRE 未安装，无法运行 JCo 交货单", None
    except Exception as e:
        logger.error(f"调用 Java 时发生异常: {e}")
        return False, f"调用 Java 异常: {str(e)}", None


def should_create_delivery(supply_plant: str) -> bool:
    """
    判断是否需要创建外向交货单
    仅当发出工厂为售后工厂时返回 true
    """
    return get_plant_type(supply_plant) == "service"


def get_company_code(receiving_plant: str) -> Optional[str]:
    """
    根据接收工厂代码获取公司代码
    """
    _map = {
        "A001": "C001", "A002": "C001",
        "P001": "C002",
        "P002": "C003", "P003": "C003",
        "P004": "C004",
        "P005": "C005",
    }
    return _map.get(receiving_plant)


def get_document_type(supply_plant: str, receiving_plant: str) -> str:
    """
    根据工厂代码获取订单类型
    """
    if supply_plant in ["P005", "P001"] or receiving_plant in ["P005", "P001"]:
        return "ZSTO_T1"
    return "ZSTO_T2"


def normalize_delivery_date(delivery_date: str) -> str:
    """规范化交货日期为 YYYY-MM-DD"""
    if not delivery_date:
        raise ValueError("交货日期不能为空")

    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(delivery_date, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    raise ValueError(f"交货日期格式无效: {delivery_date}，支持格式: YYYY-MM-DD")


def to_sap_odata_date(delivery_date: str) -> str:
    """将 YYYY-MM-DD 转换为 SAP OData /Date(ms)/ 格式"""
    date_obj = datetime.strptime(delivery_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    milliseconds = int(date_obj.timestamp() * 1000)
    return f"/Date({milliseconds})/"


def validate_and_fill_delivery_dates(
    materials: List[Dict[str, Any]], overall_delivery_date: Optional[str] = None
) -> Tuple[bool, str, List[Dict[str, Any]]]:
    """验证并填充交货日期（支持整体日期或逐行日期）"""
    filled_materials: List[Dict[str, Any]] = []

    normalized_overall_date: Optional[str] = None
    if overall_delivery_date:
        try:
            normalized_overall_date = normalize_delivery_date(overall_delivery_date)
        except ValueError as e:
            return False, str(e), []

    for idx, item in enumerate(materials, 1):
        current_item = dict(item)
        line_date = current_item.get("delivery_date") or normalized_overall_date

        if not line_date:
            return (
                False,
                f"物料清单第{idx}项缺少交货日期，请为每行提供 delivery_date 或提供整体交货日期",
                [],
            )

        try:
            current_item["delivery_date"] = normalize_delivery_date(str(line_date))
        except ValueError as e:
            return False, f"物料清单第{idx}项交货日期错误: {e}", []

        filled_materials.append(current_item)

    return True, "", filled_materials


def validate_plants(supply_plant: str, receiving_plant: str) -> Tuple[bool, str]:
    """验证工厂代码是否合法以及组合是否有效"""
    supply_type = get_plant_type(supply_plant)
    receiving_type = get_plant_type(receiving_plant)

    if supply_type is None:
        return False, f"发出工厂 '{supply_plant}' 不在允许的工厂清单中"

    if receiving_type is None:
        return False, f"接收工厂 '{receiving_plant}' 不在允许的工厂清单中"

    if supply_type == receiving_type:
        return False, f"发出工厂与接收工厂不能同属于{supply_type}工厂"

    return True, ""


def validate_material_quantities(materials: List[Dict[str, any]]) -> Tuple[bool, str]:
    """验证物料清单格式"""
    if not materials:
        return False, "物料清单不能为空"

    for idx, item in enumerate(materials, 1):
        if "material" not in item or not item["material"]:
            return False, f"物料清单第{idx}项缺少物料编码"
        if "quantity" not in item or item["quantity"] is None:
            return False, f"物料清单第{idx}项缺少数量"
        if not isinstance(item["quantity"], (int, float)) or item["quantity"] <= 0:
            return False, f"物料清单第{idx}项的数量必须为正数"

    return True, ""


def get_confirmation_summary(
    supply_plant: str,
    receiving_plant: str,
    materials: List[Dict[str, any]],
    material_units: Optional[Dict[str, str]] = None,
    overall_delivery_date: Optional[str] = None,
    batch_number: str = "",
) -> str:
    all_plants = {**PRODUCTION_PLANTS, **SERVICE_PLANTS}
    supply_desc = all_plants.get(supply_plant, "未知工厂")
    receiving_desc = all_plants.get(receiving_plant, "未知工厂")

    doc_type = get_document_type(supply_plant, receiving_plant)
    company_code = get_company_code(receiving_plant)
    vendor = f"000000{supply_plant}"

    supply_type = get_plant_type(supply_plant)
    receiving_type = get_plant_type(receiving_plant)

    lines = [
        "=== STO 订单信息确认 ===",
        f"批次号: {batch_number}",
        f"订单类型: {doc_type}",
        f"采购组织: C002",
        f"采购组: 001",
        f"公司代码: {company_code}",
    ]

    if doc_type == "ZSTO_T1":
        lines.append(f"供应商: {vendor}")
    else:
        lines.append("供应商: (留空)")
    lines.append(f"供应工厂: {supply_plant}")

    lines.extend(
        [
            "",
            f"发出工厂: {supply_plant} - {supply_desc}",
        ]
    )

    if supply_type == "service":
        lines.append("发出库位: 0001")

    lines.append(f"接收工厂: {receiving_plant} - {receiving_desc}")

    if receiving_type == "service":
        lines.append("接收库位: 0001")

    lines.append("")
    lines.append("物料明细:")

    for mat in materials:
        material = mat["material"]
        quantity = mat["quantity"]
        line_delivery_date = mat.get("delivery_date") or overall_delivery_date
        if material_units and material in material_units:
            if line_delivery_date:
                lines.append(
                    f"- {material}: {quantity} {material_units[material]} (交货日期: {line_delivery_date})"
                )
            else:
                lines.append(f"- {material}: {quantity} {material_units[material]}")
        else:
            if line_delivery_date:
                lines.append(
                    f"- {material}: {quantity} (交货日期: {line_delivery_date})"
                )
            else:
                lines.append(f"- {material}: {quantity}")

    if overall_delivery_date:
        lines.append("")
        lines.append(f"整体交货日期: {overall_delivery_date}")

    lines.append("")
    lines.append("请确认以上信息是否正确?(Y/N)")

    return "\\n".join(lines)


def create_sto_order(
    supply_plant: str,
    receiving_plant: str,
    materials: List[Dict[str, any]],
    batch_number: str = "",
    overall_delivery_date: Optional[str] = None,
    user_confirmed: bool = False,
) -> Dict[str, any]:
    result = {"success": False, "po_number": None, "messages": [], "suggest": None}

    try:
        is_valid, error_msg = validate_batch_number(batch_number)
        if not is_valid:
            result["messages"].append({"type": "E", "message": error_msg})
            return result
        batch_number = batch_number.strip()

        is_valid, error_msg = validate_plants(supply_plant, receiving_plant)
        if not is_valid:
            result["messages"].append({"type": "E", "message": error_msg})
            return result

        is_valid, error_msg = validate_material_quantities(materials)
        if not is_valid:
            result["messages"].append({"type": "E", "message": error_msg})
            return result

        is_valid, error_msg, materials_with_dates = validate_and_fill_delivery_dates(
            materials, overall_delivery_date
        )
        if not is_valid:
            result["messages"].append({"type": "E", "message": error_msg})
            return result

        supply_type = get_plant_type(supply_plant)
        receiving_type = get_plant_type(receiving_plant)
        doc_type = get_document_type(supply_plant, receiving_plant)
        company_code = get_company_code(receiving_plant)
        if not company_code:
            result["messages"].append(
                {
                    "type": "E",
                    "message": f"无法根据接收工厂 '{receiving_plant}' 确定公司代码",
                }
            )
            return result

        client = S4HanaODataClient()

        material_codes = [item["material"] for item in materials_with_dates]
        material_units = client.get_material_units_batch(material_codes)

        order_data = {
            "doc_type": doc_type,
            "company_code": company_code,
            "supply_plant": supply_plant,
            "batch_number": batch_number,
            "items": [],
        }

        if doc_type == "ZSTO_T1":
            order_data["vendor"] = f"000000{supply_plant}"

        for mat in materials_with_dates:
            item = {
                "material": mat["material"],
                "quantity": mat["quantity"],
                "unit": material_units.get(mat["material"], "EA"),
                "delivery_date": mat["delivery_date"],
                "plant": receiving_plant,
            }
            if receiving_type == "service":
                item["storage_location"] = DEFAULT_SERVICE_LOCATION
            order_data["items"].append(item)

        normalized_overall_delivery_date = (
            normalize_delivery_date(overall_delivery_date)
            if overall_delivery_date
            else None
        )

        confirmation_summary = get_confirmation_summary(
            supply_plant,
            receiving_plant,
            materials_with_dates,
            material_units,
            normalized_overall_delivery_date,
            batch_number=batch_number,
        )

        if not user_confirmed:
            token_ok, token_err = _generate_confirmation_token()
            if not token_ok:
                result["messages"].append({"type": "E", "message": token_err})
                return result
            result["messages"].append(
                {
                    "type": "I",
                    "message": "请先确认订单信息，确认后再创建STO订单。",
                }
            )
            result["requires_confirmation"] = True
            result["confirmation_summary"] = confirmation_summary
            result["order_data_preview"] = order_data
            return result

        token_valid, token_error = _validate_and_consume_confirmation_token()
        if not token_valid:
            result["messages"].append({"type": "E", "message": token_error})
            return result

        try:
            batch_exists, existing_pos = client.check_batch_number_exists(batch_number)
            if batch_exists:
                po_list = "、".join(existing_pos[:3])
                result["messages"].append(
                    {
                        "type": "E",
                        "message": (
                            f"批次号 '{batch_number}' 已存在于采购订单 {po_list} 中，"
                            "禁止重复创建 STO。如确认业务需要重新创建，"
                            "请更换批次号后重新运行 preview 并确认。"
                        ),
                    }
                )
                return result
        except Exception as e:
            result["messages"].append(
                {
                    "type": "E",
                    "message": f"批次号唯一性检查失败（{e}），请检查 SAP OData 连接后重试",
                }
            )
            return result

        po_result = client.create_purchase_order(order_data)

        if po_result["success"]:
            result["success"] = True
            result["po_number"] = po_result["po_number"]
            result["order_data"] = order_data

            if should_create_delivery(supply_plant):
                logger.info(f"发出工厂 {supply_plant} 为售后工厂，尝试创建外向交货单...")
                delivery_success, delivery_message, delivery_number = create_outbound_delivery(
                    po_result["po_number"]
                )
                result["delivery_created"] = delivery_success
                result["delivery_message"] = delivery_message
                result["delivery_number"] = delivery_number

                if delivery_success:
                    logger.info(f"外向交货单创建成功: {delivery_number or '(未返回号码)'}")
                else:
                    logger.warning(f"外向交货单创建失败: {delivery_message}")
            else:
                result["delivery_created"] = False
                result["delivery_message"] = "非售后工厂发出，不创建外向交货单"
        else:
            result["success"] = False
            result["messages"] = po_result["messages"]
            result["suggest"] = po_result.get("suggest")

    except Exception as e:
        result["messages"].append(
            {"type": "E", "message": f"创建STO订单时发生异常: {str(e)}"}
        )
        err_str = str(e)
        if "缺少必要环境变量" in err_str:
            result["suggest"] = (
                f"{err_str}。请在技能根目录将 .env.example 复制为 .env，"
                "填入 SAP_URL / SAP_USER / SAP_PASSWORD，然后重试。"
            )
        else:
            result["suggest"] = "请检查SAP OData连接配置或联系系统管理员"

    return result


def format_sto_success(
    po_number: str,
    doc_type: str,
    supply_plant: str,
    receiving_plant: str,
    materials: List[Dict],
    delivery_date: str,
    company_code: str = "C001",
    delivery_number: str = None,
    delivery_created: bool = False,
    batch_number: str = "",
) -> str:
    all_plants = {**PRODUCTION_PLANTS, **SERVICE_PLANTS}

    supply_type = get_plant_type(supply_plant)
    receiving_type = get_plant_type(receiving_plant)

    supply_desc = all_plants.get(supply_plant, "未知工厂")
    receiving_desc = all_plants.get(receiving_plant, "未知工厂")

    vendor = f"000000{supply_plant}" if doc_type == "ZSTO_T1" else "(留空)"

    output = ["\\n### ✅ STO 订单创建成功\\n"]

    output.append("#### 订单抬头信息\\n")
    output.append("| 字段 | 值 |")
    output.append("|------|-----|")
    output.append(f"| **采购订单号** | **_{po_number}_** |")
    output.append(f"| 订单类型 | {doc_type} |")
    output.append(f"| 公司代码 | {company_code} |")
    output.append(f"| 采购组织 | C002 |")
    output.append(f"| 采购组 | 001 |")
    output.append(f"| 供应商 | {vendor} |")
    output.append(f"| 批次号 | {batch_number} |")
    output.append(f"| 供应工厂 | {supply_plant} - {supply_desc} |")
    if supply_type == "service":
        output.append(f"| 供应库位 | 0001 |")
    output.append(f"| 接收工厂 | {receiving_plant} - {receiving_desc} |")
    if receiving_type == "service":
        output.append(f"| 接收库位 | 0001 |")
    output.append(f"| 整体交货日期 | {delivery_date} |")
    output.append(f"| 物料行数 | {len(materials)} |")

    output.append("\\n#### 物料明细\\n")
    output.append("| 行号 | 物料编号 | 数量 | 单位 | 交货日期 |")
    output.append("|------|----------|------|------|----------|")

    for idx, item in enumerate(materials, 1):
        material = item.get("material", "")
        quantity = item.get("quantity", "")
        line_date = item.get("delivery_date", delivery_date)
        output.append(f"| {idx} | {material} | {quantity} | EA | {line_date} |")


    # 售后工厂发出时，显示外向交货单信息
    if supply_type == "service":
        output.append("\\\\n#### 📦 外向交货单\\\\n")
        if delivery_created and delivery_number:
            output.append("| 字段 | 值 |")
            output.append("|------|-----|")
            output.append(f"| **交货单号** | **_{delivery_number}_** |")
            output.append("交货单状态 | 已创建")
        elif delivery_created:
            output.append("ℹ️ 外向交货单 已创建（未返回交货单号）")
        elif delivery_number is not None:
            output.append(f"| 交货单号 | {delivery_number} |")
            output.append("交货单状态 | 存在（已存在或创建失败）")
        else:
            output.append("⚠️ 外向交货单创建失败或未创建")
    return "\\n".join(output)


def format_sto_error(
    messages: List[Dict],
    suggest: Optional[str] = None,
    order_data: Optional[Dict] = None,
) -> str:
    output = ["\\n### ❌ STO 订单创建失败\\n"]

    output.append("#### 错误信息\\n")
    output.append("| 类型 | 消息 |")
    output.append("|------|------|")

    for msg in messages:
        msg_type = msg.get("type", "E")
        msg_text = msg.get("message", "")
        type_desc = {"E": "❌ 错误", "W": "⚠️ 警告", "I": "ℹ️ 信息", "S": "✅ 成功"}.get(
            msg_type, msg_type
        )

        if msg_type == "E":
            output.append(f"| **{type_desc}** | **_{msg_text}_** |")
        else:
            output.append(f"| {type_desc} | {msg_text} |")

    if suggest:
        output.append("\\n#### 💡 处理建议\\n")
        suggestions = suggest.split("; ") if ";" in suggest else [suggest]
        for i, suggestion in enumerate(suggestions, 1):
            output.append(f"{i}. {suggestion}")

    if order_data:
        output.append("\\\\n#### 📋 订单数据快照\\\\n")
        output.append("```")
        output.append(f"订单类型: {order_data.get('doc_type', 'N/A')}")
        output.append(f"公司代码: {order_data.get('company_code', 'N/A')}")
        output.append(f"供应工厂: {order_data.get('supply_plant', 'N/A')}")
        output.append(f"供应商: {order_data.get('vendor', 'N/A')}")
        output.append(f"供应商销售员（批次号）: {order_data.get('batch_number', '')}")
        output.append(f"物料行数: {len(order_data.get('items', []))}")

        items = order_data.get("items", [])
        if items:
            output.append("\\n物料明细:")
            for item in items:
                output.append(
                    f"  - {item.get('material', 'N/A')} × {item.get('quantity', 0)} EA"
                )

        output.append("```")

    output.append("\\n#### 🔍 诊断步骤\\n")
    output.append("1. 检查SAP系统连接配置（.env文件中的SAP_URL等）")
    output.append("2. 验证工厂代码是否在允许的列表中")
    output.append("3. 确认物料编码在SAP中存在且可用")
    output.append("4. 检查交货日期是否为有效的工作日")
    output.append("5. 验证订单类型（ZSTO_T1/ZSTO_T2）与工厂组合是否匹配")
    output.append("6. 确认用户账号具有创建采购订单的权限")

    return "\\n".join(output)


if __name__ == "__main__":
    # 测试用例
    print("SAP STO 订单创建脚本 (OData 版本) 已加载")
    print(f"量产工厂: {list(PRODUCTION_PLANTS.keys())}")
    print(f"售后工厂: {list(SERVICE_PLANTS.keys())}")

    # 测试 OData 连接
    try:
        client = S4HanaODataClient()
        print("\nS/4HANA OData 连接测试通过")

        demo_materials = [{"material": "MAT-001", "quantity": 1}]
        preview = create_sto_order(
            supply_plant="P005",
            receiving_plant="A002",
            materials=demo_materials,
            overall_delivery_date="2026-05-20",
            user_confirmed=False,
        )
        if preview.get("requires_confirmation"):
            print("\n=== 预览模式（待人工确认）===")
            print(preview.get("confirmation_summary", ""))
            print("\n说明: 仅预览，未调用SAP创建。")
    except Exception as e:
        print(f"\nS/4HANA OData 连接测试失败: {e}")
