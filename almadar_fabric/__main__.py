import argparse
import json
from pathlib import Path
from .audit import verify_chain
from .models import Order
from .runtime import SCENARIOS, run


def main():
    parser = argparse.ArgumentParser(description="Almadar enterprise service fulfilment sandbox")
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="Run a fulfilment scenario")
    demo.add_argument("--scenario", choices=SCENARIOS, default="ready")
    demo.add_argument("--order", type=Path)
    demo.add_argument("--output", type=Path)
    serve = sub.add_parser("serve", help="Open the local walkthrough server")
    serve.add_argument("--port", type=int, default=8080)
    verify = sub.add_parser("verify", help="Verify a saved run's audit chain")
    verify.add_argument("path", type=Path)
    args = parser.parse_args()
    if args.command == "serve":
        from .server import serve as start_server
        start_server(args.port)
        return
    if args.command == "verify":
        result = json.loads(args.path.read_text(encoding="utf-8"))
        records = result["audit"]
        valid = bool(records) and verify_chain(records) and result.get("audit_head") == records[-1]["hash"]
        print("Audit chain verified" if valid else "Audit chain verification failed")
        raise SystemExit(0 if valid else 1)
    try:
        order = Order.from_dict(json.loads(args.order.read_text(encoding="utf-8"))) if args.order else None
        result = run(order, args.scenario)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    payload = json.dumps(result, indent=2, ensure_ascii=True, allow_nan=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(f"{result['order']['order_id']}  |  {result['status']}")
    print(result["reason"])
    for record in result["audit"]:
        print(f"{record['sequence']:02}  {record['kind']:11}  {record['agent']:14}  {record['summary']}")
    print(f"Audit: {'verified' if result['audit_valid'] else 'invalid'} | {result['audit_head'][:16]}")


if __name__ == "__main__":
    main()
