"""Measure RAG quality against a running backend.

Usage:  python evals/run_eval.py <public_key> [base_url]
1. Upload your demo documents through the dashboard.
2. Edit evals/questions.json to match them (include questions that are NOT answerable).
3. Run this after every change to chunking, thresholds or prompts and compare pass rates.
"""
import json
import sys
import uuid
from pathlib import Path

import httpx

public_key = sys.argv[1]
base = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:8000"
questions = json.loads((Path(__file__).parent / "questions.json").read_text())

passed = 0
with httpx.Client(base_url=base, timeout=60) as client:
    for q in questions:
        r = client.post("/public/chat", json={"public_key": public_key, "session_id": uuid.uuid4().hex, "message": q["question"]})
        r.raise_for_status()
        data = r.json()
        answered = bool(data["sources"])
        keywords_ok = not q["expect_any"] or any(k.lower() in data["reply"].lower() for k in q["expect_any"])
        ok = answered == q["should_answer"] and (keywords_ok if q["should_answer"] else True)
        passed += ok
        print(f"{'PASS' if ok else 'FAIL'}  {q['question']}\n      -> {data['reply'][:110]!r} (sources: {len(data['sources'])})")
print(f"\n{passed}/{len(questions)} passed")
