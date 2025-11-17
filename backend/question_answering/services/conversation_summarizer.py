import logging
from typing import List, Dict, Any, Optional


class ConversationSummarizer:
    """
    Lightweight, safe summarizer for short conversation state (<150 words).
    Deterministic summary capturing entities/case names/topics/requests for future disambiguation.
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def summarize(self, recent_turns: List[Dict[str, Any]], active_case: Optional[Dict[str, Any]] = None) -> str:
        try:
            if not recent_turns:
                if active_case and active_case.get('case_number'):
                    return f"User is discussing case {active_case.get('case_number')}."
                return "No prior conversation."

            # Use last up to 5 turns
            last_turns = recent_turns[-5:]
            queries = [t.get('query', '').strip() for t in last_turns if t.get('query')]
            intents = []
            for q in queries:
                ql = q.lower()
                if 'summary' in ql:
                    intents.append('summary')
                elif 'advocat' in ql or 'lawyer' in ql or 'counsel' in ql:
                    intents.append('advocates')
                elif 'order' in ql:
                    intents.append('court order')
                elif 'fir' in ql:
                    intents.append('fir info')

            case_number = None
            if active_case:
                case_number = active_case.get('case_number') or active_case.get('case_title')

            parts: List[str] = []
            if case_number:
                parts.append(f"Active case: {case_number}")

            if queries:
                parts.append("Recent questions: " + " | ".join(q[:120] for q in queries))
            if intents:
                parts.append("Topics: " + ", ".join(intents))

            result = ". ".join(p for p in parts if p).strip()
            if not result:
                result = "Short conversation without specific details."
            # Enforce <150 words
            words = result.split()
            if len(words) > 150:
                result = " ".join(words[:150])
            return result
        except Exception:
            return "Short conversation without specific details."


