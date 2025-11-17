import logging
from typing import Optional


class TopicClassifier:
    """
    Minimal topic shift detector.
    Returns 'same' or 'new' based on short summary and current query.
    Conservative to avoid accidental resets.
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def classify(self, short_summary: str, current_query: str, active_case_number: Optional[str] = None) -> str:
        try:
            q = (current_query or "").lower()
            if not q:
                return "same"

            # If user explicitly mentions a different case marker, treat as new
            explicit_case_tokens = [' vs ', ' v. ', '/', ' crim ', ' crl ', ' misc ', ' ta ', ' c.o. ', ' writ ']
            if any(tok in q for tok in explicit_case_tokens):
                # If active case number is mentioned, probably same
                if active_case_number and active_case_number.lower() in q:
                    return "same"
                return "new"

            # Generic "new topic" starters
            new_topic_starters = ['new query', 'another case', 'different case', 'switch case', 'move to']
            if any(s in q for s in new_topic_starters):
                return "new"

            # Otherwise default to same
            return "same"
        except Exception:
            return "same"


