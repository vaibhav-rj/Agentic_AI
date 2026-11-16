from src.schemas.evidence import Evidence, EvidenceLedger

evidence = Evidence(
    claim="AAPL had negative short-term returns.",
    source_type="market_data",
    source="historical_prices",
    task_type ="market_analysis",
    tool_category="market",
    evidence="Total return was -0.67%.",
    confidence=0.95,
    status="SUPPORTED",
)

ledger = EvidenceLedger(items=[evidence])

print(ledger)

assert len(ledger.items) == 1
assert ledger.items[0].status == "SUPPORTED"
assert ledger.items[0].confidence == 0.95