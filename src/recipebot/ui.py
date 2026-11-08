import sys
from pathlib import Path


def main() -> None:
    from streamlit.web import cli as stcli

    app = Path(__file__).with_name("app.py")
    sys.argv = ["streamlit", "run", str(app), "--server.port", "8501",
                "--browser.gatherUsageStats", "false", *sys.argv[1:]]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
