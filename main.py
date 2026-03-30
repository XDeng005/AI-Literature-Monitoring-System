# -*- coding: utf-8 -*-
"""
main.py

Stable main pipeline:
1. Fetch papers
2. AI filtering
3. AI classification
4. Push to Zotero
5. Send email report

Features:
- Displays runtime for each step
- Stops when a critical step fails
- Provides a clear pipeline summary
- Keeps the structure simple and stable
"""

import os
import sys
import time
import subprocess

# main.py is located in the project root directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def run_step(name, script_relative_path):
    """
    Run one pipeline step and return (success, elapsed_seconds).
    """
    print("\n" + "=" * 60)
    print(name)
    print("=" * 60)

    start_time = time.time()
    script_full_path = os.path.join(BASE_DIR, script_relative_path)

    if not os.path.exists(script_full_path):
        elapsed = time.time() - start_time
        print(f"[FAILED] {name}")
        print(f"Runtime before failure: {elapsed:.2f}s")
        print(f"Script not found: {script_full_path}")
        return False, elapsed

    try:
        subprocess.run(
            [sys.executable, script_full_path],
            cwd=BASE_DIR,
            check=True
        )
        elapsed = time.time() - start_time
        print(f"[SUCCESS] {name} finished in {elapsed:.2f}s")
        return True, elapsed

    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start_time
        print(f"[FAILED] {name}")
        print(f"Runtime before failure: {elapsed:.2f}s")
        print(f"Subprocess error: {e}")
        return False, elapsed

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"[FAILED] {name}")
        print(f"Runtime before failure: {elapsed:.2f}s")
        print(f"Unexpected error: {e}")
        return False, elapsed


def main():
    pipeline_start = time.time()

    steps = [
        ("Step 1 - Fetch papers", "scripts/fetch_papers.py"),
        ("Step 2 - AI filtering", "scripts/filter_papers_ai.py"),
        ("Step 3 - AI classification", "scripts/classify_relevance_ai.py"),
        ("Step 4 - Push to Zotero", "scripts/push_to_zotero.py"),
        ("Step 5 - Send email report", "scripts/send_email_report.py"),
    ]

    results = []

    print("\n" + "#" * 60)
    print("AI Literature Monitoring Pipeline Started")
    print("#" * 60)

    for step_name, script_path in steps:
        success, elapsed = run_step(step_name, script_path)
        results.append({
            "step": step_name,
            "script": script_path,
            "success": success,
            "runtime_seconds": elapsed
        })

        if not success:
            print("\n[PIPELINE STOPPED]")
            break

    total_elapsed = time.time() - pipeline_start

    print("\n" + "#" * 60)
    print("Pipeline Summary")
    print("#" * 60)

    for result in results:
        status = "SUCCESS" if result["success"] else "FAILED"
        print(f"[{status}] {result['step']} ({result['runtime_seconds']:.2f}s)")

    print("-" * 60)
    print(f"Total runtime: {total_elapsed:.2f}s")

    if results and all(r["success"] for r in results):
        print("[PIPELINE COMPLETED SUCCESSFULLY]")
    else:
        print("[PIPELINE FINISHED WITH ERRORS]")

    print("#" * 60)


if __name__ == "__main__":
    main()