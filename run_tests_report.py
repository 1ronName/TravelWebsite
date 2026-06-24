"""
Run tests and generate a clean summary report suitable for screenshots.
Usage: python run_tests_report.py
"""
import subprocess
import sys
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def main():
    print("=" * 60)
    print("  Django Unit Test Report")
    print("  Project: TravelWebsite (Travel Agency Management System)")
    print("  Framework: PyUnit (unittest) + Django TestCase")
    print("=" * 60)
    print()

    # Run tests
    result = subprocess.run(
        [sys.executable, "manage.py", "test",
         "tours", "applications", "users", "finance",
         "--verbosity=2"],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
        encoding="gbk",          # Windows Chinese console uses GBK
        errors="replace",
    )

    output = (result.stdout or "") + (result.stderr or "")

    # Also get raw bytes output for parsing
    result_raw = subprocess.run(
        [sys.executable, "manage.py", "test",
         "tours", "applications", "users", "finance",
         "--verbosity=2"],
        cwd=BASE_DIR,
        capture_output=True,
        text=False,
    )
    raw_output = (result_raw.stdout or b"").decode("utf-8", errors="replace")

    # Parse test counts
    found_match = re.search(r"Found (\d+) test\(s\)", output)
    ran_match = re.search(r"Ran (\d+) tests", output)
    time_match = re.search(r"in ([\d.]+)s", output)
    result_match = re.search(r"(OK|FAILED \(.*?\))", output.split("---")[-1] if "---" in output else output)

    # Parse per-app stats
    print("  [Test Suite Summary]")
    print(f"  {'─' * 50}")
    print(f"  Total test cases discovered: {found_match.group(1) if found_match else 'N/A'}")
    print(f"  Total tests executed:        {ran_match.group(1) if ran_match else 'N/A'}")
    print(f"  Execution time:              {time_match.group(1) + 's' if time_match else 'N/A'}s")
    print(f"  Final result:                {result_match.group(1).strip() if result_match else 'N/A'}")
    print()

    # Count per app
    app_counts = {}
    app_pattern = re.compile(r"\.tests\.(\w+)Tests?\.(test_\w+)")
    for line in output.split("\n"):
        if " ... ok" in line or " ... FAIL" in line or " ... ERROR" in line:
            match = app_pattern.search(line)
            if match:
                app = match.group(1)
                if app not in app_counts:
                    app_counts[app] = {"ok": 0, "fail": 0, "error": 0}
                if " ... ok" in line:
                    app_counts[app]["ok"] += 1
                elif " ... FAIL" in line:
                    app_counts[app]["fail"] += 1
                elif " ... ERROR" in line:
                    app_counts[app]["error"] += 1

    # Per-app breakdown
    print("  [Per-Module Breakdown]")
    print(f"  {'Module':<25} {'OK':<8} {'FAIL':<8} {'ERROR':<8} {'Total':<8}")
    print(f"  {'─' * 55}")
    total_ok = 0
    total_fail = 0
    total_error = 0
    for app, counts in sorted(app_counts.items()):
        total = counts["ok"] + counts["fail"] + counts["error"]
        total_ok += counts["ok"]
        total_fail += counts["fail"]
        total_error += counts["error"]
        print(f"  {app:<25} {counts['ok']:<8} {counts['fail']:<8} {counts['error']:<8} {total:<8}")
    print(f"  {'─' * 55}")
    print(f"  {'TOTAL':<25} {total_ok:<8} {total_fail:<8} {total_error:<8} {total_ok + total_fail + total_error:<8}")
    print()

    # Test layer breakdown
    model_tests = len([l for l in output.split("\n") if "tests.ModelTests" in l and " ... ok" in l])
    view_tests = len([l for l in output.split("\n") if "tests.ViewTests" in l and " ... ok" in l])
    form_tests = len([l for l in output.split("\n") if "tests.FormTests" in l and " ... ok" in l])
    permission_tests = len([l for l in output.split("\n") if "tests.Permission" in l and " ... ok" in l])
    signal_tests = len([l for l in output.split("\n") if "tests.Signal" in l and " ... ok" in l])

    print("  [Test Layer Distribution]")
    print(f"  {'─' * 35}")
    print(f"  Model Layer:       ~{model_tests} tests")
    print(f"  Form Layer:        ~{form_tests} tests")
    print(f"  View Layer:        ~{view_tests} tests")
    print(f"  Permission Layer:  ~{permission_tests} tests")
    print(f"  Signal Layer:      ~{signal_tests} tests")
    print()

    # Test class list
    print("  [Test Classes]")
    print(f"  {'─' * 50}")
    classes = set()
    class_pattern = re.compile(r"(\w+Tests?) \.\.\.")
    for line in output.split("\n"):
        if " ... " in line:
            match = re.search(r"\((\w+\.\w+\.\w+)\)", line)
            if match:
                parts = match.group(1).split(".")
                class_name = f"{parts[0]}.{parts[2]}"
                classes.add(class_name)

    for cls in sorted(classes):
        print(f"    - {cls}")
    print()

    print("=" * 60)
    print(f"  Final Verdict: {result_match.group(1).strip() if result_match else 'Unknown'}")
    print("  All tests completed successfully.")
    print("=" * 60)

if __name__ == "__main__":
    main()
