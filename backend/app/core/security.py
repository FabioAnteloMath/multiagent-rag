import re
from typing import List

INJECTION_PATTERNS: List[re.Pattern] = [
    re.compile(r"ignore\s+all\s+previous", re.IGNORECASE),
    re.compile(r"forget\s+everything", re.IGNORECASE),
    re.compile(r"disregard\s+your\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(a|an)\s+(different|new)", re.IGNORECASE),
    re.compile(r"pretend\s+you\s+are", re.IGNORECASE),
    re.compile(r"override\s+your\s+system", re.IGNORECASE),
    re.compile(r"bypass\s+your\s+security", re.IGNORECASE),
    re.compile(r"system\s*prompt\s*:", re.IGNORECASE),
    re.compile(r"new\s+AI\s+model", re.IGNORECASE),
    re.compile(r"<\s*script\s*>", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
]


def detect_prompt_injection(text: str) -> bool:
    for pattern in INJECTION_PATTERNS:
        if pattern.search(text):
            return True
    return False


def sanitize_input(text: str) -> str:
    text = text.strip()
    text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', text)
    return text