#!/usr/bin/env python3
"""
RAG evaluation test script — with incremental save, timeout, and resume.
Usage: python eval_script.py
Requires: set QUESTIONS, OUTPUT_PATH, PROJECT_DIR, and import your RAG agent.
"""
import sys
import os
import time
import json
import concurrent.futures

# === CONFIGURE THESE ===
from datetime import datetime
PROJECT_DIR = "/path/to/your/project"
TIMESTAMPED = True  # True = eval_results_20260619_1750.json (preserves history)
                     # False = eval_results.json (overwrites each run)
OUTPUT_PATH = f"eval_results_{datetime.now().strftime('%Y%m%d_%H%M')}.json" if TIMESTAMPED else "eval_results.json"
QUESTION_TIMEOUT = 120  # seconds per question
DELAY_BETWEEN = 3       # seconds between questions

sys.path.insert(0, PROJECT_DIR)
os.chdir(PROJECT_DIR)

# Import your RAG agent here:
# from your_agent import agent_executor  # for LangChain AgentExecutor
# from your_rag import ask              # for simple ask() function

# === DEFINE QUESTIONS ===
QUESTIONS = [
    # ("单点查询", "精确事实问题?"),
    # ("对比型", "两个方案对比问题?"),
    # ("多跳推理", "需要多步计算的问题?"),
    # ("流程型", "操作步骤问题?"),
    # ("场景型", "用户场景推荐问题?"),
    # ("边界/异常", "超出范围的问题?"),
    # ("边界/异常", "需要拒答的问题?"),
]

def run_with_timeout(func, timeout):
    """Run func in a thread with timeout. Returns None on timeout."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            return None

def main():
    # RESUME: load partial results from previous run
    if os.path.exists(OUTPUT_PATH):
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            results = json.load(f)
        completed_ids = {r["id"] for r in results}
        print(f"Resuming: {len(results)} questions already done")
    else:
        results = []
        completed_ids = set()

    total = len(QUESTIONS)
    print(f"Starting evaluation: {total} questions")

    for i, (qtype, question) in enumerate(QUESTIONS, 1):
        if i in completed_ids:
            print(f"[{i}/{total}] already done, skipping")
            continue

        print(f"\n{'='*60}")
        print(f"[{i}/{total}] {qtype}: {question}")
        print(f"{'='*60}")

        t0 = time.time()

        # --- CALL YOUR RAG AGENT HERE ---
        # Option A: AgentExecutor
        # result = run_with_timeout(
        #     lambda q=question: agent_executor.invoke({"input": q}),
        #     QUESTION_TIMEOUT
        # )
        # answer = result["output"] if result else None
        # tools = [s[0].tool for s in result.get("intermediate_steps", [])] if result else []

        # Option B: Simple ask()
        # result = run_with_timeout(
        #     lambda q=question: ask(q),
        #     QUESTION_TIMEOUT
        # )
        # answer = result

        # Placeholder — replace with your agent call:
        result = run_with_timeout(
            lambda q=question: f"MOCK ANSWER for: {q}",
            QUESTION_TIMEOUT
        )
        answer = result
        tools = []
        # --- END AGENT CALL ---

        elapsed = time.time() - t0

        if answer is None:
            print(f"  TIMEOUT (>{QUESTION_TIMEOUT}s)")
            results.append({
                "id": i, "type": qtype, "question": question,
                "answer": None, "tools": [],
                "time_seconds": round(elapsed, 1), "status": "timeout"
            })
        else:
            print(f"  Answer: {str(answer)[:100]}...")
            print(f"  Time: {elapsed:.1f}s | Tools: {len(tools)}")
            results.append({
                "id": i, "type": qtype, "question": question,
                "answer": answer, "tools": tools,
                "time_seconds": round(elapsed, 1), "status": "ok"
            })

        # INCREMENTAL SAVE — critical for long runs
        results.sort(key=lambda x: x["id"])
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        if i < total:
            time.sleep(DELAY_BETWEEN)

    # Summary
    ok = sum(1 for r in results if r["status"] == "ok")
    err = sum(1 for r in results if r["status"] != "ok")
    avg = sum(r["time_seconds"] for r in results) / len(results)
    print(f"\n{'='*60}")
    print(f"DONE: {ok}/{total} ok, {err}/{total} errors, {avg:.1f}s avg")
    print(f"Results: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
