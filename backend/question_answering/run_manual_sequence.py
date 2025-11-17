import os
import sys
import django
import json

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from question_answering.services.enhanced_qa_engine import EnhancedQAEngine


def ask_seq(engine: EnhancedQAEngine, queries, user_id="cli_sequence_tester"):
    session_id = None
    outputs = []
    for q in queries:
        res = engine.ask_question(q, user_id=user_id, session_id=session_id)
        session_id = res.get("session_id", session_id)
        outputs.append({
            "question": q,
            "answer_preview": (res.get("answer") or "")[:450],
            "sources": [s.get("title", "") for s in (res.get("sources") or [])],
        })
    return outputs


def main():
    eng = EnhancedQAEngine()
    queries = [
        "give me details for this case: Crl. Misc. 2/2025 Bail After Arrest (SB)",
        "what is the court order",
        "any advocates",
        "give me the summary of the details",
        "now give me details for this case Rimsa tahir VS pakistan institute of medical sciences",
    ]
    results = ask_seq(eng, queries)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

