from src.agents.replan_researcher import replan_research
from src.schemas.adjudication import Adjudication
from src.schemas.query import ResearchQuery
from src.schemas.evidence import Evidence, EvidenceLedger


research_query = ResearchQuery(
    original_query="Analyze Apple's historical volatility.",
    task_types=["quantitative_analysis"],
)

evidence_elm = Evidence(
    claim="AAPL had negative short-term returns.",
    source_type="market_data",
    source="historical_prices",
    task_type ="market _analysis",
    tool_category="market",
    evidence="Total return was -0.67%.",
    confidence=0.95,
    status="SUPPORTED",
)

evidence_ledger = EvidenceLedger(items=[evidence_elm])

adjudication = Adjudication(
    decision="FAIL",
    rationale="Additional market and quantitative evidence is required.",
    evidence_debt=[
        "Missing market evidence.",
        "Missing quantitative evidence.",
    ],
    confidence=0.6,
)

plan = replan_research(
    research_query=research_query,
    evidence =evidence_ledger,
    adjudication=adjudication,
)

print("Replan:", plan)