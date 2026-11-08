import io
import sys
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from recipebot.config import DATASET_URL, RAW_DIR, SOURCES


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if all((RAW_DIR / f).exists() for f in SOURCES.values()):
        print(f"Dataset already present in {RAW_DIR}")
        return

    print(f"Downloading {DATASET_URL} (~53 MB)...")
    req = urllib.request.Request(DATASET_URL, headers={"User-Agent": "Mozilla/5.0 (compatible; recipebot-downloader)"})
    with urllib.request.urlopen(req) as resp:
        payload = resp.read()

    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        for name in zf.namelist():
            if name.endswith(".json") or name == "LICENSE":
                zf.extract(name, RAW_DIR)
                print("  extracted", name)
    print("Done.")


if __name__ == "__main__":
    main()
