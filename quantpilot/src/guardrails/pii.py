import re
from typing import Any

import logging
logger = logging.getLogger(__name__)

# Labelled Aadhaar: avoids redacting arbitrary 12-digit numbers.
_AADHAAR_PATTERN = re.compile(
    r"(?i)\b(aadhaar(?:\s*(?:number|no\.?))?\s*[:#=-]\s*)"
    r"\d{4}(?:[\s-]?\d{4}){2}\b"
)

# Labelled tax, company-registration, licence and permit identifiers.
_REGISTRATION_PATTERN = re.compile(
    r"(?i)\b("
    r"GSTIN|GST(?:\s*(?:registration|reg))?(?:\s*(?:ID|number|no\.?))?"
    r"|VAT(?:\s*(?:ID|number|no\.?|registration number))?"
    r"|EIN|UEN|CIN|TIN|NTN|STRN|BIN|NPWP"
    r"|SST(?:\s*(?:number|ID|no\.?))?"
    r"|company registration(?:\s*(?:number|no\.?|ID))?"
    r"|business registration(?:\s*(?:number|no\.?|ID))?"
    r"|tax identification number|tax ID|tax number"
    r"|business licen[cs]e(?:\s*(?:number|no\.?|ID))?"
    r"|licen[cs]e number|permit number"
    r")\s*[:#=-]\s*"
    r"([A-Z0-9][A-Z0-9./_-]{3,29})\b"
)

_CERTIFICATE_PATTERN = re.compile(
    r"(?i)\b("
    r"ISO(?:\s*\d{4,5})?\s+certification(?:\s+reference)?"
    r"|ISO(?:\s*\d{4,5})?\s+certificate"
    r"(?:\s+(?:number|no\.?|ID|reference))?"
    r"|certificate number|certificate no\.?|certificate ID"
    r"|certification reference"
    r")\s*[:#=-]\s*"
    r"([A-Z0-9][A-Z0-9./_-]{3,29})\b"
)

_IP_REFERENCE_PATTERN = re.compile(
    r"(?i)\b("
    r"patent(?:\s+(?:application|registration))?"
    r"(?:\s*(?:number|no\.?|ID|reference))?"
    r"|trademark(?:\s+(?:registration|application))?"
    r"(?:\s*(?:number|no\.?|ID|reference))?"
    r"|copyright(?:\s+(?:registration))?"
    r"(?:\s*(?:number|no\.?|ID|reference))?"
    r"|industrial design(?:\s+(?:registration|application))?"
    r"(?:\s*(?:number|no\.?|ID|reference))?"
    r"|design registration(?:\s*(?:number|no\.?|ID|reference))?"
    r"|semiconductor layout(?:\s+(?:registration|design))?"
    r"(?:\s*(?:number|no\.?|ID|reference))?"
    r")\s*[:#=-]\s*"
    r"([A-Z0-9][A-Z0-9./_-]{3,39})\b"
)

# Only redact explicitly labelled confidential content.
# Scope: same line, stopping at a comma or semicolon.
_CONFIDENTIAL_CONTENT_PATTERN = re.compile(
    r"(?i)\b("
    r"confidential(?:\s+business)?\s+(?:information|details|data)"
    r"|proprietary\s+(?:information|data|source code|design|technology)"
    r"|trade secrets?"
    r"|confidential\s+(?:blueprint|schematic|design|layout|formula)"
    r"|proprietary\s+(?:blueprint|schematic|design|layout)"
    r")\s*[:=-]\s*"
    r"([^\r\n;,]+)"
)

# Recognizable identifier formats, including when unlabelled.
_FORMAT_PATTERNS = [
    (
        "GSTIN",
        re.compile(
            r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z0-9]Z[A-Z0-9]\b",
            re.IGNORECASE,
        ),
    ),
    (
        "CIN",
        re.compile(r"\b[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}\b", re.I),
    ),
    ("EIN", re.compile(r"\b\d{2}-\d{7}\b")),
    (
        "EMAIL",
        re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    ),
    ("PHONE", re.compile(r"(?<!\w)(?:\+91[\s-]?)?[6-9]\d{9}(?!\w)")),
    ("PAN", re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b", re.I)),
]


def redact_pii(text: str) -> str:
    """Deterministically redact supported PII and labelled confidential data."""
    for pattern in (
        _AADHAAR_PATTERN,
        _REGISTRATION_PATTERN,
        _CERTIFICATE_PATTERN,
        _IP_REFERENCE_PATTERN,
    ):
        original_text = text
        
        text = pattern.sub(
            lambda match: f"{match.group(1)}[IDENTIFIER REDACTED]",
            text,
        )

    text = _CONFIDENTIAL_CONTENT_PATTERN.sub(
        lambda match: f"{match.group(1)}: [CONFIDENTIAL CONTENT REDACTED]",
        text,
    )

    for label, pattern in _FORMAT_PATTERNS:
        text = pattern.sub(f"[{label} REDACTED]", text)

    if text != original_text:
        logger.info("PII/confidential content detected and redacted")

    return text


# Custom LangChain detectors reuse the same patterns as the deterministic
# sanitizer. PIIMiddleware redacts the entire regex match.
_LANGCHAIN_CUSTOM_RULES = [
    ("aadhaar", _AADHAAR_PATTERN),
    ("business_registration", _REGISTRATION_PATTERN),
    ("certificate_reference", _CERTIFICATE_PATTERN),
    ("ip_registration_reference", _IP_REFERENCE_PATTERN),
    ("confidential_content", _CONFIDENTIAL_CONTENT_PATTERN),
    *_FORMAT_PATTERNS,
]


def build_langchain_pii_middleware(
    *,
    apply_to_output: bool = True,
    apply_to_tool_results: bool = True,
) -> list[Any]:
    """Create reusable PII middleware for compatible LangChain agents.

    Requires a LangChain version supporting PIIMiddleware and the requested
    options. This factory does not automatically protect custom graph nodes
    or direct LLM calls outside a LangChain agent.
    """
    try:
        from langchain.agents.middleware import PIIMiddleware
    except ImportError as exc:
        
        logger.exception("LangChain PII middleware unavailable")
        raise RuntimeError(
            "PIIMiddleware is unavailable. Check your installed LangChain "
            "version and upgrade to a compatible release."
        ) from exc

    middleware = [
        PIIMiddleware(
            pii_type,
            strategy="redact",
            apply_to_input=True,
            apply_to_output=apply_to_output,
            apply_to_tool_results=apply_to_tool_results,
        )
        for pii_type in ("email", "credit_card", "ip", "mac_address")
    ]

    middleware.extend(
        PIIMiddleware(
            pii_type,
            detector=pattern.pattern,
            strategy="redact",
            apply_to_input=True,
            apply_to_output=apply_to_output,
            apply_to_tool_results=apply_to_tool_results,
        )
        for pii_type, pattern in _LANGCHAIN_CUSTOM_RULES
    )

    return middleware