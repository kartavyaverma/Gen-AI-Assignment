"""Paths and settings in one place so nothing is hard-coded elsewhere."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

# The three files shipped in recipes_raw.zip (Allrecipes, Epicurious, Food Network)
SOURCES = {
    "ar": "recipes_raw_nosource_ar.json",
    "epi": "recipes_raw_nosource_epi.json",
    "fn": "recipes_raw_nosource_fn.json",
}
DATASET_URL = "https://eightportions.com/recipes_raw.zip"

RECIPES_PKL = PROCESSED_DIR / "recipes.pkl"
INDEX_PKL = PROCESSED_DIR / "search_index.pkl"

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()
