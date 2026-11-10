import re
from markdown_it import MarkdownIt
import nh3

PATTERNS = [
    (re.compile(r'-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----', re.S), '[REDACTED PRIVATE KEY]'),
    (re.compile(r'\b(?:sk-[A-Za-z0-9_-]{10,}|gh[pousr]_[A-Za-z0-9]{12,}|AKIA[A-Z0-9]{16})\b'), '[REDACTED TOKEN]'),
    (re.compile(r'(?i)\b(authorization\s*[:=]\s*(?:bearer|basic)\s+)[^\s,;]+'), r'\1[REDACTED]'),
    (re.compile(r'(?i)\b(password|passwd|secret|api[_-]?key|access[_-]?token)\s*[:=]\s*["\']?[^\s,"\';]+'), r'\1=[REDACTED]'),
    (re.compile(r'\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+'), '[REDACTED JWT]'),
    (re.compile(r'(https?://)[^\s/@:]+:[^\s/@]+@'), r'\1[REDACTED]@'),
]
def redact(text: str) -> str:
    for pattern, replacement in PATTERNS:
        text = pattern.sub(replacement, text)
    return text

def safe_html(markdown: str) -> str:
    return nh3.clean(MarkdownIt('commonmark', {'html': False}).enable('table').render(markdown),
                     tags={'p','br','h1','h2','h3','strong','em','code','pre','ul','ol','li','blockquote','table','thead','tbody','tr','th','td','hr'}, attributes={})
