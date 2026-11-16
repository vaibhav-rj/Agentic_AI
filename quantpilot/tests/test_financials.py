from src.tools.financials import get_financial_metrics


def main():
    result = get_financial_metrics(
        ticker="AAPL",
        metrics=["marketCap", "trailingPE", "profitMargins"],
    )

    print(type(result))
    print(result.ticker)
    print(result.metrics)


if __name__ == "__main__":
    main()