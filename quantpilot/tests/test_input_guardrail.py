from src.guardrails.input import validate_user_query


def main():
    # Valid
    result = validate_user_query("Analyze Apple's historical volatility.")
    print(result)

    # Normalization
    result = validate_user_query("   Analyze Apple's valuation.   ")
    print(result.query)

    # Empty
    try:
        validate_user_query("   ")
    except ValueError as e:
        print("Empty query rejected:", e)

    # Too short
    try:
        validate_user_query("Hi")
    except ValueError as e:
        print("Short query rejected:", e)

    # Too long
    try:
        validate_user_query("A" * 2001)
    except ValueError as e:
        print("Long query rejected:", e)


if __name__ == "__main__":
    main()