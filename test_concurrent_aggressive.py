#!/usr/bin/env python3
"""More aggressive load test for concurrent script execution.

This mimics the exact pytest test but runs it many times to catch flaky failures.
"""

import concurrent.futures
import sys


def test_concurrent_execution_once(num_scripts: int = 3):
    """Run concurrent test with specified number of scripts."""
    sys.path.insert(0, "src")
    from bake.ui.run import run_script

    # Use the exact scripts from the pytest test
    if num_scripts == 3:
        scripts = [
            ("Script 1", "echo one"),
            ("Script 2", "echo two"),
            ("Script 3", "echo three"),
        ]
    else:
        scripts = [(f"Script {i}", f"echo output{i}") for i in range(num_scripts)]

    def run_script_pair(title: str, script: str):
        return run_script(title, script)

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_scripts) as executor:
        futures = [executor.submit(run_script_pair, title, script) for title, script in scripts]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # All scripts should succeed
    assert len(results) == num_scripts, f"Expected {num_scripts} results, got {len(results)}"
    for result in results:
        assert result.returncode == 0, f"Script failed with returncode {result.returncode}"

    # All outputs should be present (order may vary)
    all_stdout = "".join(r.stdout for r in results if r.stdout)
    if num_scripts == 3:
        assert "one" in all_stdout, f"Missing 'one' in output: {all_stdout!r}"
        assert "two" in all_stdout, f"Missing 'two' in output: {all_stdout!r}"
        assert "three" in all_stdout, f"Missing 'three' in output: {all_stdout!r}"
    else:
        for i in range(num_scripts):
            expected = f"output{i}"
            assert expected in all_stdout, f"Missing '{expected}' in output: {all_stdout!r}"


def main():
    """Run aggressive load test."""
    iterations = 1000
    num_scripts = 10  # Stress test with more concurrent scripts
    failures = []

    print(
        f"Running concurrent execution test {iterations} times "
        f"with {num_scripts} concurrent scripts..."
    )
    print("=" * 60)

    for i in range(iterations):
        try:
            test_concurrent_execution_once(num_scripts)
            if (i + 1) % 100 == 0:
                print(f"  [{i + 1}] PASSED")
        except AssertionError as e:
            failures.append((i + 1, str(e)))
            print(f"  [{i + 1}] FAILED: {e}")
        except Exception as e:
            failures.append((i + 1, str(e)))
            print(f"  [{i + 1}] ERROR: {e}")

    print("=" * 60)
    print(f"\nResults: {iterations - len(failures)}/{iterations} passed")

    if failures:
        print(f"\n{len(failures)} failures:")
        for iteration, error in failures[:10]:
            print(f"  Iteration {iteration}: {error}")
        if len(failures) > 10:
            print(f"  ... and {len(failures) - 10} more failures")

        # Print detailed analysis
        print("\n" + "=" * 60)
        print("FAILURE ANALYSIS:")
        print("=" * 60)
        missing_counts = {}
        for _, error in failures:
            # Extract which output is missing from error message
            import re

            match = re.search(r"Missing '(\w+)'", error)
            if match:
                missing = match.group(1)
                missing_counts[missing] = missing_counts.get(missing, 0) + 1

        for missing, count in sorted(missing_counts.items()):
            print(f"  Missing '{missing}': {count}/{len(failures)}")

        sys.exit(1)
    else:
        print("\nAll tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
