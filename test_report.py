"""
Generate a clean test report for screenshots.
Usage: python test_report.py
"""
import subprocess
import sys
import re

def main():
    print("=" * 64)
    print("  Unit Test Report: TravelWebsite")
    print("  Framework: PyUnit (unittest) + Django TestCase")
    print("  Database: SQLite (in-memory)")
    print("=" * 64)
    print()

    # Run tests
    print("  Running tests, please wait...")
    print()

    proc = subprocess.run(
        [sys.executable, "manage.py", "test",
         "tours", "applications", "users", "finance",
         "--verbosity=2", "--no-input"],
        capture_output=True,
    )

    # Decode stdout (bytes -> str, handle both utf-8 and gbk)
    raw = proc.stdout
    for encoding in ["utf-8", "gbk", "latin-1"]:
        try:
            output = raw.decode(encoding)
            break
        except (UnicodeDecodeError, LookupError):
            continue
    else:
        output = raw.decode("utf-8", errors="replace")

    # Parse summary
    found_match = re.search(r"Found (\d+) test", output)
    ran_match = re.search(r"Ran (\d+) tests", output)
    time_match = re.search(r"in ([\d.]+)s", output)

    # Determine result
    tail = output.split("---")[-1] if "---" in output else output[-800:]
    is_ok = "OK" in tail and "FAILED" not in tail

    print(f"  Tests Discovered: {found_match.group(1) if found_match else '?'}")
    print(f"  Tests Executed:   {ran_match.group(1) if ran_match else '?'}")
    if time_match:
        print(f"  Duration:         {time_match.group(1)}s")
    print(f"  Result:           {'ALL PASSED' if is_ok else 'FAILURES DETECTED'}")
    print()

    # Count per app from output
    app_ok = {}
    app_total = {}
    for line in output.split("\n"):
        if " ... ok" in line:
            m = re.search(r"(\w+)\.tests\.", line)
            if m:
                app = m.group(1)
                app_ok[app] = app_ok.get(app, 0) + 1

    print(f"  {'-' * 40}")
    print(f"  {'Module':<20} {'Tests Passed':>15}")
    print(f"  {'-' * 40}")
    total = 0
    for app in ["tours", "applications", "users", "finance"]:
        count = app_ok.get(app, 0)
        total += count
        print(f"  {app:<20} {count:>15}")
    print(f"  {'-' * 40}")
    print(f"  {'TOTAL':<20} {total:>15}")
    print()

    # List test classes
    print(f"  {'-' * 40}")
    print(f"  Test Classes:")
    print(f"  {'-' * 40}")
    classes_seen = set()
    for line in output.split("\n"):
        m = re.search(r"(\w+Tests?) \.\.\.", line)
        if m and m.group(1) not in classes_seen:
            classes_seen.add(m.group(1))
            # Find the module
            mod_m = re.search(r"\((\w+)\.tests\.", line)
            module = mod_m.group(1) if mod_m else "?"
            count_in_class = len([l for l in output.split("\n")
                                  if m.group(1) in l and " ... ok" in l])
            print(f"    {module}.{m.group(1)} ({count_in_class} tests)")

    print()
    print("=" * 64)
    if is_ok:
        print(f"  >>> ALL {total} TESTS PASSED <<<")
    else:
        print(f"  >>> TESTS FAILED - SEE ABOVE <<<")
    print("=" * 64)

if __name__ == "__main__":
    main()
