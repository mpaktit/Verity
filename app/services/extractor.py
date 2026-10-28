"""Extract public-offer signals from official HTML pages.

This is conservative by design: it records what a public page says about trials,
credits, student programs, and eligibility. It does not infer loopholes or
account-bypass paths.
"""

from __future__ import annotations

import re
from html import unescape

SIGNAL_PATTERNS: list[tuple[str, str, int]] = [
    (r"\bfree trial\b", "free-trial", 22),
    (r"\bstart(?:ing)? (?:a )?free trial\b", "free-trial", 20),
    (r"\btrial period\b", "trial-window", 16),
    (r"\bfree tier\b", "free-tier", 20),
    (r"\bno[- ]cost\b", "no-cost", 10),
    (r"\bstarter credits?\b", "starter-credits", 18),
    (r"\bapi credits?\b", "api-credits", 16),
    (r"\bfree credits?\b", "free-credits", 18),
    (r"\bstudent(?:s)?\b", "student-program", 16),
    (r"\beducation(?:al)? (?:pack|program|plan|discount)\b", "education-program", 20),
    (r"\bgithub education\b", "education-program", 18),
    (r"\bstartup (?:credits?|program)\b", "startup-credits", 18),
    (r"\bpartner program\b", "partner-program", 12),
    (r"\beligib(?:le|ility)\b", "eligibility", 10),
    (r"\bnew (?:users?|accounts?|customers?)\b", "new-account", 12),
    (r"\bonboarding\b", "onboarding", 8),
    (r"\bpromo(?:tion)?\b", "promotion", 8),
    (r"\bpricing\b", "pricing", 4),
]


def strip_html(html: str) -> str:
    text = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", html)
    text = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", text)
    text = re.sub(r"(?is)<noscript[^>]*>.*?</noscript>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _snippet(text: str, match: re.Match[str], radius: int = 90) -> str:
    start = max(0, match.start() - radius)
    end = min(len(text), match.end() + radius)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = "…" + snippet
    if end < len(text):
        snippet = snippet + "…"
    return snippet


def extract_signals(html: str, max_signals: int = 12) -> list[dict]:
    text = strip_html(html)
    if not text:
        return []

    found: list[dict] = []
    seen_labels: set[str] = set()
    lowered = text.lower()

    for pattern, label, weight in SIGNAL_PATTERNS:
        if label in seen_labels:
            continue
        match = re.search(pattern, lowered, flags=re.IGNORECASE)
        if not match:
            continue
        seen_labels.add(label)
        found.append(
            {
                "label": label,
                "weight": weight,
                "snippet": _snippet(text, match),
            }
        )
        if len(found) >= max_signals:
            break

    found.sort(key=lambda item: item["weight"], reverse=True)
    return found


def score_page(signals: list[dict], http_status: int | None) -> int:
    if http_status is None or http_status >= 400:
        return 0
    base = 28 if http_status < 300 else 12
    weighted = sum(item["weight"] for item in signals)
    return max(0, min(100, base + weighted))
