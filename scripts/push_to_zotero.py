# -*- coding: utf-8 -*-
"""
push_to_zotero.py

Purpose:
1. Read outputs/papers_filtered.csv
2. Push the filtered papers to Zotero

Revised features:
- If the filtered CSV is empty, skip without raising an error
- If the file does not exist, show a clear message
- Compatible with missing fields
- If ZOTERO_LIBRARY_TYPE is missing in config.py, default to "user"
- Upload items to Zotero in batches (max 50 items per request)
"""

import os
import sys
import json
import time
import traceback
import requests
import pandas as pd

# =========================
# Project root directory
# =========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# =========================
# Load configuration
# =========================
from config.config import ZOTERO_LIBRARY_ID, ZOTERO_API_KEY

try:
    from config.config import ZOTERO_LIBRARY_TYPE
except ImportError:
    ZOTERO_LIBRARY_TYPE = "user"

# =========================
# File path
# =========================
INPUT_FILE = os.path.join(BASE_DIR, "outputs", "papers_filtered.csv")

# =========================
# Zotero API
# =========================
ZOTERO_API_URL = f"https://api.zotero.org/{ZOTERO_LIBRARY_TYPE}s/{ZOTERO_LIBRARY_ID}/items"
HEADERS = {
    "Zotero-API-Key": ZOTERO_API_KEY,
    "Content-Type": "application/json"
}

# =========================
# Upload settings
# =========================
BATCH_SIZE = 50
BATCH_SLEEP_SECONDS = 1


def safe_text(x):
    if pd.isna(x):
        return ""
    return str(x).strip()


def split_authors(authors_str):
    """
    Convert the author string into Zotero creator format.

    Supported formats:
    - "A; B; C"
    - "A, B, C"
    """
    text = safe_text(authors_str)
    if not text:
        return []

    if ";" in text:
        raw_authors = [a.strip() for a in text.split(";") if a.strip()]
    else:
        raw_authors = [a.strip() for a in text.split(",") if a.strip()]

    creators = []
    for author in raw_authors:
        parts = author.split()
        if len(parts) >= 2:
            first_name = " ".join(parts[:-1])
            last_name = parts[-1]
            creators.append({
                "creatorType": "author",
                "firstName": first_name,
                "lastName": last_name
            })
        else:
            creators.append({
                "creatorType": "author",
                "name": author
            })

    return creators


def load_filtered_papers():
    """
    Load the filtered CSV file.
    """
    if not os.path.exists(INPUT_FILE):
        print(f"[INFO] Input file not found: {INPUT_FILE}")
        return pd.DataFrame()

    try:
        df = pd.read_csv(INPUT_FILE)
    except pd.errors.EmptyDataError:
        print("[INFO] Filtered CSV is empty. Skip Zotero upload.")
        return pd.DataFrame()
    except Exception as e:
        print(f"[ERROR] Failed to read filtered CSV: {e}")
        return pd.DataFrame()

    if df.empty:
        print("[INFO] No rows in filtered CSV. Skip Zotero upload.")
        return df

    if "title" not in df.columns:
        print("[INFO] CSV has no title column. Skip Zotero upload.")
        return pd.DataFrame()

    df["title"] = df["title"].fillna("").astype(str).str.strip()
    df = df[df["title"] != ""]

    if df.empty:
        print("[INFO] No valid papers after title cleaning.")
        return df

    return df


def build_zotero_item(row):
    """
    Build a single Zotero item.
    """
    title = safe_text(row.get("title", ""))
    abstract = safe_text(row.get("abstract", ""))
    journal = safe_text(row.get("journal", ""))
    year = safe_text(row.get("year", ""))
    doi = safe_text(row.get("doi", ""))
    url = safe_text(row.get("url", ""))
    authors = safe_text(row.get("authors", ""))
    reason = safe_text(row.get("reason", ""))
    score = safe_text(row.get("score", ""))

    note_parts = []
    if reason:
        note_parts.append(f"AI relevance reason: {reason}")
    if score:
        note_parts.append(f"AI relevance score: {score}")

    extra_note = "\n".join(note_parts)

    item = {
        "itemType": "journalArticle",
        "title": title,
        "abstractNote": abstract,
        "publicationTitle": journal,
        "date": year,
        "DOI": doi,
        "url": url,
        "creators": split_authors(authors),
        "extra": extra_note
    }

    return item


def push_items_to_zotero(items):
    """
    Upload one batch of items to Zotero.
    """
    if not items:
        print("[INFO] No items to upload.")
        return True

    try:
        response = requests.post(
            ZOTERO_API_URL,
            headers=HEADERS,
            data=json.dumps(items),
            timeout=60
        )

        if response.status_code in [200, 201]:
            print(f"[SUCCESS] Uploaded {len(items)} items to Zotero")
            return True
        else:
            print(f"[ERROR] Zotero API failed: {response.status_code}")
            print(response.text)
            return False

    except Exception as e:
        print(f"[ERROR] Zotero request failed: {e}")
        return False


def push_in_batches(items, batch_size=BATCH_SIZE, sleep_seconds=BATCH_SLEEP_SECONDS):
    """
    Upload all items to Zotero in batches.
    Zotero allows at most 50 items per request.
    """
    total = len(items)

    if total == 0:
        print("[INFO] No items to upload.")
        return True

    total_batches = (total + batch_size - 1) // batch_size

    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        batch = items[start:end]
        batch_number = start // batch_size + 1

        print(f"[INFO] Uploading batch {batch_number}/{total_batches} ({len(batch)} items)")

        success = push_items_to_zotero(batch)
        if not success:
            return False

        if end < total:
            time.sleep(sleep_seconds)

    return True


def main():
    print("=" * 60)
    print("Push Papers to Zotero")
    print("=" * 60)

    df = load_filtered_papers()

    if df.empty:
        print("[INFO] No relevant papers found. Skipping Zotero push.")
        return

    print(f"[INFO] Papers to upload: {len(df)}")

    items = []
    for _, row in df.iterrows():
        item = build_zotero_item(row)
        items.append(item)

    success = push_in_batches(items)

    if not success:
        raise RuntimeError("Zotero push failed")

    print("=" * 60)
    print("[SUCCESS] Zotero push completed")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("[ERROR] Zotero push failed:", e)
        traceback.print_exc()
        sys.exit(1)