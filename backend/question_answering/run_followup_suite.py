import os
import sys
import django

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from question_answering.services.enhanced_qa_engine import EnhancedQAEngine


def ask(engine, q, sid=None):
    res = engine.ask_question(q, user_id="cli_tester", session_id=sid)
    sid = res.get("session_id") or sid
    print("\nQ:", q)
    print("A:", (res.get("answer") or "")[:260])
    srcs = res.get("sources", [])
    print("Sources:", [f"{s.get('title')}|{s.get('case_number')}" for s in srcs if isinstance(s, dict)])
    return sid


def main():
    eng = EnhancedQAEngine()
    session_id = None

    # 1) Detailed
    session_id = ask(eng, "give me details for this case: Crl. Misc. 2/2025 Bail After Arrest (SB)", session_id)
    # 2) Advocates
    session_id = ask(eng, "who are the Petitioner's and Respondent's advocates of this case?", session_id)
    # 3) Court order
    session_id = ask(eng, "what is the court order in this case?", session_id)
    # 4) FIR + sections list
    session_id = ask(eng, "list the FIR number and sections for this case", session_id)
    # 5) Concise summary
    session_id = ask(eng, "give me a concise summary of this case in 3 bullet points", session_id)


if __name__ == "__main__":
    main()

