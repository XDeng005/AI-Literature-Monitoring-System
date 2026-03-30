# -*- coding: utf-8 -*-
"""
classify_relevance_ai.py
Step 3: Classify filtered papers using AI
"""

import os
import sys
import json
import pandas as pd
from openai import OpenAI

# =========================
# 项目根目录
# =========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# =========================
# 读取配置
# =========================
from config.config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

# =========================
# 文件路径
# =========================
INPUT_FILE = os.path.join(BASE_DIR, "outputs", "papers_filtered.csv")
OUTPUT_FILE = os.path.join(BASE_DIR, "outputs", "papers_classified.csv")


def classify_paper(title, abstract):
    prompt = f"""
You are an academic research assistant.

Determine whether this paper is relevant to the user's research topic.

Return JSON only:
{{
  "category": "Relevant" or "Other"
}}

Title: {title}
Abstract: {abstract}
"""

    response = client.responses.create(
        model="gpt-4o-mini",
        input=prompt
    )

    text = response.output_text.strip()

    try:
        return json.loads(text)
    except Exception:
        return {"category": "Other"}


def main():
    print("[INFO] Starting AI classification step")

    if not os.path.exists(INPUT_FILE):
        print(f"[INFO] Input file does not exist: {INPUT_FILE}")
        return

    if os.path.getsize(INPUT_FILE) == 0:
        print(f"[INFO] Input file is empty: {INPUT_FILE}")
        return

    try:
        df = pd.read_csv(INPUT_FILE)
    except pd.errors.EmptyDataError:
        print(f"[INFO] Input CSV has no columns or rows: {INPUT_FILE}")
        return
    except Exception as e:
        print(f"[ERROR] Cannot read CSV: {e}")
        return

    if df.empty:
        print("[INFO] No papers to classify.")
        return

    results = []

    for i, row in df.iterrows():
        title = str(row.get("title", "")).strip()
        abstract = str(row.get("abstract", "")).strip()

        try:
            result = classify_paper(title, abstract)
            category = result.get("category", "Other")
            print(f"[INFO] Classified {i+1}/{len(df)} | {category}")
        except Exception as e:
            print(f"[ERROR] AI classification failed on row {i+1}: {e}")
            category = "Other"

        new_row = row.to_dict()
        new_row["category"] = category
        results.append(new_row)

    df_out = pd.DataFrame(results)
    df_out.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print(f"[INFO] Classification complete. Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()