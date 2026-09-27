"""Command line entry points for mobile assurance and design-time compilation."""

import argparse
import json
from pathlib import Path
from .audit import verify_chain
from .models import Incident
from .process import compile_process
from .runtime import run, SCENARIOS


def main():
    parser = argparse.ArgumentParser(
        description="Almadar mobile assurance reference demo"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo")
    demo.add_argument("--scenario", choices=SCENARIOS, default="transport-fault")
    demo.add_argument("--incident")
    demo.add_argument("--output")
    server = sub.add_parser("serve")
    server.add_argument("--port", type=int, default=8080)
    verify = sub.add_parser("verify")
    verify.add_argument("path")
    compile_cmd = sub.add_parser("compile")
    compile_cmd.add_argument("--output")
    args = parser.parse_args()
    if args.command == "serve":
        from .server import serve

        return serve(args.port)
    if args.command == "verify":
        records = json.loads(Path(args.path).read_text(encoding="utf-8"))["audit"]
        valid = verify_chain(records)
        print("Audit chain valid" if valid else "Audit chain INVALID")
        raise SystemExit(0 if valid else 1)
    if args.command == "compile":
        result = compile_process()
    else:
        incident = (
            Incident.from_dict(
                json.loads(Path(args.incident).read_text(encoding="utf-8"))
            )
            if args.incident
            else None
        )
        result = run(incident, args.scenario)
    content = json.dumps(result, indent=2, allow_nan=False)
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content + "\n", encoding="utf-8")
        print(f"Saved {path}")
    else:
        print(content)


if __name__ == "__main__":
    main()
