import logging
import re
from typing import List, Dict, Any, Optional


class QueryRewriter:
    """
    Deterministic standalone query rewriter following industry-standard design:
    - Use conversation summary + history to rewrite into a short, factual, context-independent query
    - Resolve pronouns (e.g., "this case", "same one") into explicit terms (case number/title)
    - Return a clean string suitable for vector + keyword search
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def _extract_case_number_like(self, text: str) -> Optional[str]:
        try:
            # Common Pakistan case number pattern (flexible)
            pattern = r'([A-Z][a-z]?\.?\s*\d+/\d+\s+[A-Za-z]+(?:\s*\([A-Z]+\))?)'
            matches = re.findall(pattern, text or "")
            if matches:
                return matches[0].strip()
            return None
        except Exception:
            return None

    def rewrite(self,
                current_query: str,
                recent_turns: List[Dict[str, Any]],
                short_summary: str,
                active_case: Optional[Dict[str, Any]] = None) -> str:
        """
        Return a standalone retrieval query. Priority:
        1) If active_case has case_number/title, expand pronouns to that explicit reference.
        2) Else, extract the latest case-number-like string from history and expand.
        3) Keep it short and factual; remove filler. Avoid answering the question; just rewrite it.
        4) If nothing explicit, append a minimal parenthetical with short_summary for disambiguation.
        """
        try:
            cq = (current_query or "").strip()
            case_number = None
            if active_case:
                case_number = active_case.get('case_number') or active_case.get('case_title')

            # Try to extract from recent turns if not present
            if not case_number and recent_turns:
                for t in reversed(recent_turns):
                    cn = self._extract_case_number_like(t.get('query', '')) or self._extract_case_number_like(t.get('response', ''))
                    if cn:
                        case_number = cn
                        break

            # Resolve pronouns if we have a case number or title
            rewritten = cq
            if case_number:
                rewritten = (rewritten
                             .replace('this case', case_number)
                             .replace('that case', case_number)
                             .replace('this matter', case_number)
                             .replace('that matter', case_number)
                             .replace('same one', case_number))
                # Be conservative with 'it'
                if len(cq.split()) <= 8 and 'it' in cq.lower():
                    rewritten = f"{rewritten} {case_number}"

            # If no explicit case and we have a useful short summary, include it minimally
            if not case_number and short_summary:
                rewritten = f"{rewritten} (context: {short_summary})"

            # As a final fallback include last query THEN current
            if recent_turns:
                last_q = (recent_turns[-1].get('query') or '').strip()
                if last_q and last_q.lower() != cq.lower():
                    rewritten = f"{last_q} THEN: {rewritten}"

            # Trim overly long rewrites; target short factual phrasing
            rewritten = re.sub(r'\s+', ' ', rewritten).strip()
            if len(rewritten) > 350:
                rewritten = rewritten[:350].rstrip()
            return rewritten
        except Exception:
            return current_query or ""


