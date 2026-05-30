#!/usr/bin/env python3
import sys
import json
import argparse
import subprocess
from pathlib import Path


def _ensure_deps():
    req_file = Path(__file__).parent / "requirements.txt"
    if not req_file.exists():
        return
    try:
        import dotenv  # noqa: F401
        import requests  # noqa: F401
    except ImportError:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", str(req_file), "-q"]
        )

_ensure_deps()

sys.path.insert(0, str(Path(__file__).parent / "lib"))

from create_sto_odata import (
    create_sto_order,
    PRODUCTION_PLANTS,
    SERVICE_PLANTS,
)

def parse_material(value: str) -> dict:
    parts = value.split(":", 2)
    if len(parts) < 2:
        raise argparse.ArgumentTypeError(
            f"物料格式无效: '{value}'，请使用 MAT:QTY 或 MAT:QTY:YYYY-MM-DD"
        )
    mat = {"material": parts[0].strip(), "quantity": float(parts[1].strip())}
    if len(parts) == 3 and parts[2].strip():
        mat["delivery_date"] = parts[2].strip()
    return mat


def cmd_preview(args):
    materials = [parse_material(m) for m in args.material]
    result = create_sto_order(
        supply_plant=args.supply_plant,
        receiving_plant=args.receiving_plant,
        materials=materials,
        batch_number=args.batch_number,
        overall_delivery_date=args.delivery_date,
        user_confirmed=False,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_create(args):
    if not args.confirmed:
        print(
            json.dumps(
                {
                    "success": False,
                    "messages": [
                        {
                            "type": "E",
                            "message": "创建需要显式传入 --confirmed 标志，请先调用 preview 命令确认订单信息，再使用 --confirmed 创建",
                        }
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        sys.exit(1)

    materials = [parse_material(m) for m in args.material]
    result = create_sto_order(
        supply_plant=args.supply_plant,
        receiving_plant=args.receiving_plant,
        materials=materials,
        batch_number=args.batch_number,
        overall_delivery_date=args.delivery_date,
        user_confirmed=True,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_plants(args):
    result = {
        "production_plants": [
            {"code": code, "name": name}
            for code, name in PRODUCTION_PLANTS.items()
        ],
        "service_plants": [
            {"code": code, "name": name}
            for code, name in SERVICE_PLANTS.items()
        ],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def _add_order_args(p):
    p.add_argument("--supply-plant", required=True, metavar="PLANT")
    p.add_argument("--receiving-plant", required=True, metavar="PLANT")
    p.add_argument("--material", required=True, action="append", metavar="MAT:QTY[:DATE]")
    p.add_argument("--delivery-date", metavar="YYYY-MM-DD")
    p.add_argument("--batch-number", required=True, metavar="BATCH_NO",
                   help="业务批次号（唯一标识，最多14位）")


def build_parser():
    parser = argparse.ArgumentParser(prog="sap_sto_cli.py")
    subparsers = parser.add_subparsers(dest="command", required=True)

    preview_parser = subparsers.add_parser("preview")
    _add_order_args(preview_parser)

    create_parser = subparsers.add_parser("create")
    _add_order_args(create_parser)
    create_parser.add_argument("--confirmed", action="store_true")

    subparsers.add_parser("plants")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "preview": cmd_preview,
        "create": cmd_create,
        "plants": cmd_plants,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
