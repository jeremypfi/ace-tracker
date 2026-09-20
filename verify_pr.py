#!/usr/bin/env python3
"""
PR Verification Script
=======================
Consolidates the checks that used to be run as separate ad-hoc, one-off
scripts during PR review (unit tests, a live tracker run, a module syntax
check) into a single command with one pass/fail summary.

Silent on success; prints full diagnostic output only for whichever check
failed.

Usage:
    python3 verify_pr.py             # unit tests + syntax check + full tracker run
    python3 verify_pr.py --fast      # unit tests + syntax check only (skip live tracker run)
"""

import argparse
import io
import py_compile
import subprocess
import sys
import unittest

CORE_MODULES = ["ace_data.py", "ace_html.py", "ace_tracker.py"]


def check_unit_tests():
    suite = unittest.TestLoader().discover(".", pattern="test_ace_tracker.py")
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    if result.wasSuccessful():
        return True, f"{result.testsRun} tests passed"
    return False, stream.getvalue()


def check_syntax():
    errors = []
    for module in CORE_MODULES:
        try:
            py_compile.compile(module, doraise=True)
        except py_compile.PyCompileError as e:
            errors.append(str(e))
    if errors:
        return False, "\n".join(errors)
    return True, f"{len(CORE_MODULES)} modules compiled"


def check_tracker_run():
    proc = subprocess.run(
        [sys.executable, "ace_tracker.py"],
        capture_output=True,
        text=True,
        timeout=300,
    )
    output = proc.stdout + proc.stderr
    if proc.returncode != 0:
        return False, output
    if "NaN" in output or "Traceback" in output:
        return False, output
    return True, "tracker run completed, output files generated"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fast", action="store_true",
        help="skip the live tracker run (network-dependent, slower)",
    )
    args = parser.parse_args()

    checks = [("unit tests", check_unit_tests), ("syntax check", check_syntax)]
    if not args.fast:
        checks.append(("tracker run", check_tracker_run))

    failures = []
    for name, check in checks:
        ok, detail = check()
        if not ok:
            failures.append((name, detail))

    if not failures:
        print(f"OK: {', '.join(name for name, _ in checks)} passed")
        return 0

    for name, detail in failures:
        print(f"FAILED: {name}")
        print(detail)
    return 1


if __name__ == "__main__":
    sys.exit(main())
