"""One local receipt runner: safe default preflight; explicit owned-target import."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["preflight", "integrate", "verify-preview"], nargs="?", default="preflight")
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--manifest", required=True, help="Portable path from receipt root")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--fixture", action="store_true", help="Clearly synthetic demo checks, never real Part A acceptance")
    parser.add_argument("--target-marker", type=Path)
    parser.add_argument("--expected-database")
    parser.add_argument("--object-root", type=Path)
    parser.add_argument("--delivery-id")
    parser.add_argument("--registered-by")
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--database-url-file", type=Path)
    parser.add_argument("--base-url", help="Already running explicit http://127.0.0.1:port; no service is started")
    parser.add_argument("--expect-unadmitted", action="store_true", help="Check draft/admission removal stays hidden")
    args = parser.parse_args()
    from services.api.app.receiving import preflight, ReceiptError, now, write_evidence
    previous = None
    if args.output.exists():
        if not args.resume:
            print("Fresh evidence directory or explicit resume required.", file=sys.stderr)
            return 1
        try:
            previous = json.loads((args.output / "report.json").read_text())
            if previous.get("root") != str(args.receipt.resolve()):
                raise ValueError()
        except (ValueError, OSError):
            print("Resume evidence does not belong to this receipt.", file=sys.stderr)
            return 1
    try:
        report = preflight(args.receipt, args.manifest, fixture=args.fixture)
    except ReceiptError as error:
        report = {"root": str(args.receipt.resolve()), "operation": args.operation,
                  "evidence_kind": "synthetic_fixture" if args.fixture else "real_receipt",
                  "started_at": now(), "finished_at": now(), "passed": False,
                  "scientific_acceptance": False, "database_connected": False, "data_imported": False,
                  "steps": [{"step": "receipt_available", "required": True, "performed": False,
                             "passed": False, "blocked": True, "reason": error.reason, "exit_status": None}]}
    report["requested_operation"] = args.operation
    if previous and previous.get("inventory_sha256") != report.get("inventory_sha256"):
        report["passed"] = False
    if args.operation == "integrate" and report["passed"]:
        try:
            if not all((args.target_marker, args.expected_database, args.object_root, args.delivery_id, args.registered_by)):
                raise ReceiptError("explicit_owned_target_arguments_required")
            from services.api.app.receiving_db import integrate
            report = integrate(report, args.manifest, marker=args.target_marker,
                expected_database=args.expected_database, object_root=args.object_root,
                delivery_id=args.delivery_id, registered_by=args.registered_by, catalog=args.catalog,
                database_url_file=args.database_url_file, fixture=args.fixture)
            report["database_connected"] = True
            report["steps"].append({"step": "explicit_integration", "required": True, "performed": True,
                                    "passed": True, "exit_status": 0, "result": report["integration_result"]})
        except Exception as error:
            report["passed"] = False
            reason = error.reason if isinstance(error, ReceiptError) else type(error).__name__
            report["steps"].append({"step": "explicit_integration", "required": True, "performed": True,
                                    "passed": False, "exit_status": 1, "reason": reason})
    elif args.operation == "integrate":
        report["steps"].append({"step": "explicit_integration", "required": True, "performed": False,
                               "passed": False, "blocked": True, "exit_status": None,
                               "reason": "preflight_or_resume_prerequisite_failed"})
    if args.operation == "verify-preview":
        if report["passed"] and args.base_url:
            from services.api.app.receiving_http import verify_preview
            try:
                report = verify_preview(report, args.manifest, base_url=args.base_url,
                                        expect_unadmitted=args.expect_unadmitted)
            except Exception as error:
                report["passed"] = False
                report["steps"].append({"step": "explicit_http_verification", "required": True,
                    "performed": True, "passed": False, "exit_status": 1,
                    "reason": error.reason if isinstance(error, ReceiptError) else type(error).__name__})
        else:
            report["passed"] = False
            report["steps"].append({"step": "explicit_http_verification", "required": True,
                "performed": False, "passed": False, "blocked": True, "exit_status": None,
                "reason": "passing_preflight_and_explicit_loopback_url_required"})
    try:
        write_evidence(report, args.output, resume=args.resume)
    except (ValueError, OSError):
        print("Receiver evidence could not be committed safely.", file=sys.stderr)
        return 1
    print("Receiver " + args.operation + ": " + ("passed" if report["passed"] else "failed or blocked") + "; scientific approval not established.")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
