#!/usr/bin/env python3
"""Load test for concurrent script execution to catch race conditions.

This script runs the concurrent test many times to stress test the PTY handling
and catch any flaky failures related to race conditions.
"""

import concurrent.futures
import subprocess
import sys


def run_concurrent_test():
    """Run the concurrent execution test once."""
    # Import here to avoid import issues
    sys.path.insert(0, "src")
    from bake.ui.run import run_script

    scripts = [
        ("Script 1", "echo one"),
        ("Script 2", "echo two"),
        ("Script 3", "echo three"),
    ]

    def run_script_pair(title: str, script: str):
        return run_script(title, script)

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(run_script_pair, title, script) for title, script in scripts]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # All scripts should succeed
    if len(results) != 3:
        return False, f"Expected 3 results, got {len(results)}"

    for result in results:
        if result.returncode != 0:
            return False, f"Script failed with returncode {result.returncode}"

    # All outputs should be present
    all_stdout = "".join(r.stdout for r in results if r.stdout)
    missing = []
    for expected in ["one", "two", "three"]:
        if expected not in all_stdout:
            missing.append(expected)

    if missing:
        return False, f"Missing outputs: {missing}, got: {repr(all_stdout)}"

    return True, all_stdout


def main():
    """Run load test."""
    iterations = 100
    failures = []

    print(f"Running concurrent execution test {iterations} times...")
    print("=" * 60)

    for i in range(iterations):
        try:
            success, result = run_concurrent_test()
            if not success:
                failures.append((i + 1, result))
                print(f"  [{i + 1}] FAILED: {result}")
            else:
                print(f"  [{i + 1}] PASSED")
        except Exception as e:
            failures.append((i + 1, str(e)))
            print(f"  [{i + 1}] ERROR: {e}")

    print("=" * 60)
    print(f"\nResults: {iterations - len(failures)}/{iterations} passed")

    if failures:
        print(f"\n{len(failures)} failures:")
        for iteration, error in failures[:10]:  # Show first 10 failures
            print(f"  Iteration {iteration}: {error}")
        if len(failures) > 10:
            print(f"  ... and {len(failures) - 10} more failures")
        sys.exit(1)
    else:
        print("\nAll tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
