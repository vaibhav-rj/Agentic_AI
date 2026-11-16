import pytest

from src.guardrails.pii import (
    build_langchain_pii_middleware,
    redact_pii,
)


def test_redacts_email_phone_and_pan():
    query = (
        "Contact user@example.com, call +91 9876543210, "
        "PAN: ABCDE1234F"
    )

    result = redact_pii(query)

    assert "user@example.com" not in result
    assert "9876543210" not in result
    assert "ABCDE1234F" not in result
    assert "[EMAIL REDACTED]" in result
    assert "[PHONE REDACTED]" in result
    assert "[PAN REDACTED]" in result


def test_redacts_labelled_aadhaar_and_registration_ids():
    query = (
        "Aadhaar number: 1234 5678 9012; "
        "GSTIN: 22AAAAA0000A1Z5; "
        "EIN: 12-3456789; UEN: 200312345A"
    )

    result = redact_pii(query)

    for secret in (
        "1234 5678 9012",
        "22AAAAA0000A1Z5",
        "12-3456789",
        "200312345A",
    ):
        assert secret not in result

    assert "[IDENTIFIER REDACTED]" in result


def test_redacts_certificate_and_ip_references():
    query = (
        "ISO 9001 certificate: QMS-12345; "
        "Patent application number: US2026123456; "
        "Trademark registration number: TM-12345; "
        "Design registration number: DESIGN-9876"
    )

    result = redact_pii(query)

    for secret in ("QMS-12345", "US2026123456", "TM-12345", "DESIGN-9876"):
        assert secret not in result

    assert "[IDENTIFIER REDACTED]" in result

#below "@pytest.mark.parametrize"-->runs same test multiple times
@pytest.mark.parametrize(
    "query",
    [
        "Confidential business information: Project Falcon launch plan",
        "Trade secret: proprietary chip fabrication process",
        "Confidential blueprint: unreleased vehicle chassis design",
        "Proprietary source code: internal pricing algorithm",
    ],
)
def test_redacts_labelled_confidential_content(query):
    sensitive_value = query.split(": ", maxsplit=1)[1]

    result = redact_pii(query)

    assert sensitive_value not in result
    assert "[CONFIDENTIAL CONTENT REDACTED]" in result


def test_preserves_ordinary_public_financial_research():
    query = (
        "Analyze Apple's valuation and historical volatility, "
        "and compare its public patent portfolio with competitors."
    )

    assert redact_pii(query) == query


def test_redacts_common_identifier_formats_without_labels():
    query = (
        "Email user@example.com; "
        "GSTIN 22AAAAA0000A1Z5; "
        "PAN ABCDE1234F"
    )

    result = redact_pii(query)

    assert "user@example.com" not in result
    assert "22AAAAA0000A1Z5" not in result
    assert "ABCDE1234F" not in result


def test_langchain_middleware_factory_when_available():
    pytest.importorskip("langchain.agents.middleware")#Checks whether that LangChain module is importable-->
    #if yes continues, if not then skipps(not failed)

    middleware = build_langchain_pii_middleware()

    types = {item.pii_type for item in middleware}

    assert {"email", "credit_card", "ip", "mac_address"} <= types
    assert "confidential_content" in types
    assert all(item.strategy == "redact" for item in middleware)
    assert all(item.apply_to_input for item in middleware)
    assert all(item.apply_to_output for item in middleware)
    assert all(item.apply_to_tool_results for item in middleware)