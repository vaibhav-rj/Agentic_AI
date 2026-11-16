import time

from src.cache.tool_cache import ToolResultCache


def test_cache_hit_and_argument_sensitivity(tmp_path):
    cache = ToolResultCache(
        db_path=tmp_path / "test_cache.sqlite3"
    )

    arguments = {"ticker": "AAPL", "start": "2025-01-01"}

    result = {
        "ticker": "AAPL",
        "prices": [100, 105],
    }

    assert cache.set(
        "market_server",
        "historical_prices",
        arguments,
        result,
    )

    assert cache.get(
        "market_server",
        "historical_prices",
        arguments,
    ) == result

    different_arguments = {
        "ticker": "AAPL",
        "start": "2025-02-01",
    }

    assert cache.get(
        "market_server",
        "historical_prices",
        different_arguments,
    ) is None


def test_cache_survives_new_instance(tmp_path):
    db_path = tmp_path / "test_cache.sqlite3"

    cache1 = ToolResultCache(db_path=db_path)
    arguments = {"ticker": "AAPL"}

    result = {"marketCap": 1000}

    assert cache1.set(
        "financial_server",
        "financial_metrics",
        arguments,
        result,
    )

    cache2 = ToolResultCache(db_path=db_path)

    assert cache2.get(
        "financial_server",
        "financial_metrics",
        arguments,
    ) == result


def test_expired_entry_returns_none(tmp_path):
    cache = ToolResultCache(
        db_path=tmp_path / "test_cache.sqlite3",
        ttl_seconds=1,
    )

    arguments = {"ticker": "AAPL"}

    assert cache.set(
        "market_server",
        "historical_prices",
        arguments,
        {"close": 100},
    )

    time.sleep(1.1)

    assert cache.get(
        "market_server",
        "historical_prices",
        arguments,
    ) is None


def test_none_and_unserializable_results_are_rejected(tmp_path):
    cache = ToolResultCache(
        db_path=tmp_path / "test_cache.sqlite3"
    )

    arguments = {"ticker": "AAPL"}

    assert not cache.set(
        "market_server",
        "historical_prices",
        arguments,
        None,
    )

    assert not cache.set(
        "market_server",
        "historical_prices",
        arguments,
        object(),
    )

#pytest tests/test_tool_cache.py -v==>with help of file path 'pytest' discovers functions 
# beginning with test and exceutes them without main fn. ---> alternate way to run rather than
#defining all these fns iunder main() and running themm under if ___init__==__main__: mains(),
#directly via python -m

#Using python -m pytest invokes pytest through the active Python interpreter, so you don't 
# depend on the standalone pytest command being on PATH.

#using pytest gives us liberty to use temp_path, while with normal python -m doesn't inject it 
#automatically(need to give path witjh '.' sep not '/' sep).