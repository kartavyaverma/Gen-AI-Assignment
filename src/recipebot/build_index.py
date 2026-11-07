"""`uv run recipebot-build` - process the raw JSON and build the search indexes."""

from .store import build_and_save


def main() -> None:
    build_and_save(verbose=True)


if __name__ == "__main__":
    main()
