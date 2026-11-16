from src.tools.registry import TOOLS


def main():
    print(f"Registered tools: {len(TOOLS)}")

    for tool in TOOLS:
        print(tool.__name__)


if __name__ == "__main__":
    main()