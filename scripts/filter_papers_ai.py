# -*- coding: utf-8 -*-
"""
filter_papers_ai.py

Purpose:
1. Read outputs/papers_raw.csv
2. Use OpenAI to determine whether papers are relevant to the research topic
3. Keep only relevant papers
4. Output to outputs/papers_filtered.csv

Revised features:
- Even if no papers are selected, an empty CSV with headers will still be written
- Prevent errors in push_to_zotero.py when reading empty files
- Automatically handle missing fields
"""

import os
import sys
import json
import time
import traceback
import pandas as pd
from openai import OpenAI

# =========================
# Project root directory
# =========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# =========================
# Load configuration
# =========================
from config.config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

# =========================
# File paths
# =========================
INPUT_FILE = os.path.join(BASE_DIR, "outputs", "papers_raw.csv")
OUTPUT_FILE = os.path.join(BASE_DIR, "outputs", "papers_filtered.csv")

# =========================
# Research topic prompt
# You can modify this as needed
# =========================
RESEARCH_TOPIC = """
The user is monitoring academic papers related to:
KEYWORDS = user_profile["keywords"]
"""

SYSTEM_PROMPT = f"""
You are an academic literature screening assistant.

Your task is to decide whether a paper is relevant to the following research topic:

{RESEARCH_TOPIC}

Return JSON only, in this exact format:
{{
  "relevant": true,
  "score": 0.85,
  "reason": "Brief explanation in one sentence."
}}

Rules:
- relevant must be true or false
- score must be a float between 0 and 1
- reason must be brief and clear
- Return JSON only, no markdown, no extra text
"""

EXPECTED_COLUMNS = [
    "title",
    "year",
    "journal",
    "doi",
    "abstract",
    "authors",
    "url",
    "openalex_id",
    "cited_by_count",
    "unique_id",
    "score",
    "reason"
]


def safe_text(x):
    if pd.isna(x):
        return ""
    return str(x).strip()


def ensure_input_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure the input dataframe contains required columns;
    if missing, create them with empty values
    """
    required = [
        "title", "year", "journal", "doi", "abstract",
        "authors", "url", "openalex_id", "cited_by_count", "unique_id"
    ]
    for col in required:
        if col not in df.columns:
            df[col] = ""
    return df


def classify_paper(title: str, abstract: str, journal: str = "", year: str = "") -> dict:
    """
    Use OpenAI to determine relevance of a paper
    """
    user_prompt = f"""
Title: {title}
Journal: {journal}
Year: {year}
Abstract: {abstract}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        relevant = bool(data.get("relevant", False))
        score = float(data.get("score", 0))
        reason = str(data.get("reason", "")).strip()

        if score < 0:
            score = 0.0
        if score > 1:
            score = 1.0

        return {
            "relevant": relevant,
            "score": score,
            "reason": reason
        }

    except Exception as e:
        print(f"[WARNING] OpenAI classification failed: {e}")
        return {
            "relevant": False,
            "score": 0.0,
            "reason": f"OpenAI error: {str(e)}"
        }


def main():
    print("=" * 60)
    print("AI FILTER: Start filtering papers")
    print("=" * 60)

    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    try:
        df = pd.read_csv(INPUT_FILE)
    except pd.errors.EmptyDataError:
        print("[INFO] papers_raw.csv is empty.")
        df = pd.DataFrame()
    except Exception as e:
        raise RuntimeError(f"Failed to read input CSV: {e}")

    if df.empty:
        print("[INFO] No papers found in papers_raw.csv")
        empty_df = pd.DataFrame(columns=EXPECTED_COLUMNS)
        empty_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
        print(f"[INFO] Empty filtered file saved to: {OUTPUT_FILE}")
        return

    df = ensure_input_columns(df)

    print(f"[INFO] Total candidate papers: {len(df)}")

    results = []
    total = len(df)

    for i, row in df.iterrows():
        title = safe_text(row.get("title", ""))
        abstract = safe_text(row.get("abstract", ""))
        journal = safe_text(row.get("journal", ""))
        year = safe_text(row.get("year", ""))

        print(f"[{i+1}/{total}] Screening: {title[:100]}")

        if not title and not abstract:
            print("[SKIP] Empty title and abstract")
            continue

        result = classify_paper(title, abstract, journal, year)

        if result["relevant"]:
            results.append({
                "title": title,
                "year": year,
                "journal": journal,
                "doi": safe_text(row.get("doi", "")),
                "abstract": abstract,
                "authors": safe_text(row.get("authors", "")),
                "url": safe_text(row.get("url", "")),
                "openalex_id": safe_text(row.get("openalex_id", "")),
                "cited_by_count": safe_text(row.get("cited_by_count", "")),
                "unique_id": safe_text(row.get("unique_id", "")),
                "score": result["score"],
                "reason": result["reason"]
            })

        time.sleep(0.2)

    filtered_df = pd.DataFrame(results)

    if filtered_df.empty:
        filtered_df = pd.DataFrame(columns=EXPECTED_COLUMNS)
    else:
        for col in EXPECTED_COLUMNS:
            if col not in filtered_df.columns:
                filtered_df[col] = ""
        filtered_df = filtered_df[EXPECTED_COLUMNS]
        filtered_df = filtered_df.sort_values(by="score", ascending=False)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    filtered_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print("=" * 60)
    print(f"[INFO] Relevant papers kept: {len(filtered_df)}")
    print(f"[INFO] Output saved to: {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("[ERROR] AI filtering failed:", e)
        traceback.print_exc()
        sys.exit(1)