"""Small synthetic development check against a real local Ollama model."""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from agent import Ollama, analyze

CASES = [
    ("invoice", "Missing invoice", "I purchased the application yesterday. Where is my invoice?", "billing", False),
    ("password", "Forgot my password", "How do I reset my forgotten password?", "account", False),
    ("app_error", "Application error", "The application crashes on launch. What information do you need?", "technical", False),
    ("refund", "Refund request", "I want a refund for my purchase.", "billing", True),
    ("security", "Stolen account", "My account was stolen and the password changed.", "account", True),
    ("unsupported", "International shipping", "Can you ship a physical package to Antarctica?", "other", True),
]


def main():
    results = []
    model = Ollama()
    for name, subject, body, category, escalate in CASES:
        start = time.monotonic()
        try:
            result = analyze({"subject": subject, "body": body}, model)
            passed = result["category"] == category and result["escalate"] == escalate
            row = {"case": name, "passed": passed, "expected_category": category,
                   "expected_escalate": escalate, "result": result}
        except Exception as exc:
            row = {"case": name, "passed": False, "error": type(exc).__name__ + ": " + str(exc)}
        row["seconds"] = round(time.monotonic() - start, 2)
        results.append(row)
        print(name, row["passed"], row["seconds"], flush=True)
    report = {"timestamp": datetime.now(timezone.utc).isoformat(), "model": model.model,
              "scope": "Six synthetic development cases; category and escalation checks only. Not a draft-quality or real-world accuracy benchmark.",
              "passed": sum(r["passed"] for r in results), "total": len(results), "results": results}
    folder = Path(__file__).parent / "reports"
    folder.mkdir(exist_ok=True)
    (folder / "evaluation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
