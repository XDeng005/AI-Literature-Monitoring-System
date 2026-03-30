import os
import sys
import math
import json
import hashlib
import requests
import pandas as pd

# =========================
# Project Root Directory
# =========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from scripts.logger_setup import setup_logger

logger = setup_logger()

# =========================
# OpenAlex API Endpoint
# =========================
URL = "https://api.openalex.org/works"

# =========================
# Load Research Configuration
# =========================
CONFIG_FILE = os.path.join(BASE_DIR, "config", "research_config.json")

if not os.path.exists(CONFIG_FILE):
    raise FileNotFoundError(f"Config file not found: {CONFIG_FILE}")

with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config = json.load(f)

SEARCH_QUERY = config.get("search_query", "")
START_YEAR = config.get("start_year", 2018)
END_YEAR = config.get("end_year", 2026)
MAX_RECORDS = config.get("max_records", 500)
PER_PAGE = config.get("per_page", 200)

TIMEOUT = 30

# =========================
# File Paths
# =========================
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
DATABASE_DIR = os.path.join(BASE_DIR, "database")

RAW_OUTPUT_FILE = os.path.join(OUTPUT_DIR, "papers_raw.csv")
SEEN_FILE = os.path.join(DATABASE_DIR, "seen_papers.csv")


# =========================
# Ensure Directories Exist
# =========================
def ensure_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(DATABASE_DIR, exist_ok=True)


# =========================
# Safe Text Handling
# =========================
def safe_text(x):
    if pd.isna(x):
        return ""
    return str(x).strip()


# =========================
# Reconstruct Abstract
# =========================
def invert_abstract(inv_idx):

    if not inv_idx:
        return ""

    word_positions = []

    for word, positions in inv_idx.items():
        for pos in positions:
            word_positions.append((pos, word))

    word_positions.sort(key=lambda x: x[0])

    return " ".join(word for _, word in word_positions)


# =========================
# Create Unique Paper ID
# =========================
def make_unique_id(row):

    doi = safe_text(row.get("doi")).lower()
    title = safe_text(row.get("title")).lower()
    year = safe_text(row.get("year"))
    journal = safe_text(row.get("journal")).lower()

    if doi:
        return f"doi::{doi}"

    base = f"{title}::{year}::{journal}"

    return "hash::" + hashlib.md5(base.encode("utf-8")).hexdigest()


# =========================
# Fetch One Page from OpenAlex
# =========================
def fetch_one_page(page):

    params = {
        "search": SEARCH_QUERY,
        "per_page": PER_PAGE,
        "page": page,
        "sort": "publication_date:desc"
    }

    r = requests.get(URL, params=params, timeout=TIMEOUT)
    r.raise_for_status()

    return r.json()


# =========================
# Parse Paper Metadata
# =========================
def parse_paper(paper):

    title = paper.get("title", "")
    year = paper.get("publication_year", "")
    doi = paper.get("doi", "")
    openalex_id = paper.get("id", "")

    abstract_inv = paper.get("abstract_inverted_index", {})
    abstract = invert_abstract(abstract_inv)

    primary_location = paper.get("primary_location") or {}
    source = primary_location.get("source") or {}
    journal = source.get("display_name", "")

    landing_page = primary_location.get("landing_page_url", "")
    pdf_url = primary_location.get("pdf_url", "")

    url = landing_page or pdf_url

    authorships = paper.get("authorships", [])

    authors = []
    for a in authorships[:8]:

        author_info = a.get("author") or {}
        name = author_info.get("display_name", "")

        if name:
            authors.append(name)

    authors_text = "; ".join(authors)

    cited_by = paper.get("cited_by_count", 0)

    return {

        "title": title,
        "year": year,
        "doi": doi,
        "journal": journal,
        "abstract": abstract,
        "url": url,
        "authors": authors_text,
        "openalex_id": openalex_id,
        "cited_by_count": cited_by

    }


# =========================
# Fetch Multiple Pages
# =========================
def fetch_papers():

    papers = []

    total_pages = math.ceil(MAX_RECORDS / PER_PAGE)

    logger.info(f"Planned retrieval: {MAX_RECORDS} papers (~{total_pages} pages)")

    for page in range(1, total_pages + 1):

        logger.info(f"Fetching page {page}")

        data = fetch_one_page(page)

        results = data.get("results", [])

        if not results:
            break

        for paper in results:

            papers.append(parse_paper(paper))

            if len(papers) >= MAX_RECORDS:
                break

        if len(papers) >= MAX_RECORDS:
            break

    return papers


# =========================
# Filter by Year Range
# =========================
def filter_year_range(df):

    if df.empty:
        return df

    df["year"] = pd.to_numeric(df["year"], errors="coerce")

    return df[(df["year"] >= START_YEAR) & (df["year"] <= END_YEAR)].copy()


# =========================
# Remove Duplicates within Batch
# =========================
def deduplicate_batch(df):

    if df.empty:
        return df

    df["unique_id"] = df.apply(make_unique_id, axis=1)

    return df.drop_duplicates(subset=["unique_id"]).copy()


# =========================
# Load Historical Database
# =========================
def load_seen():

    if not os.path.exists(SEEN_FILE):
        return set(), pd.DataFrame()

    try:

        seen_df = pd.read_csv(SEEN_FILE)

        if "unique_id" not in seen_df.columns:
            return set(), seen_df

        seen_ids = set(seen_df["unique_id"].astype(str))

        return seen_ids, seen_df

    except:

        return set(), pd.DataFrame()


# =========================
# Remove Previously Seen Papers
# =========================
def remove_seen(df, seen_ids):

    if df.empty or not seen_ids:
        return df

    return df[~df["unique_id"].isin(seen_ids)].copy()


# =========================
# Update Historical Database
# =========================
def update_seen(df_new, seen_df_old):

    if df_new.empty:
        return

    keep_cols = [
        "unique_id",
        "title",
        "year",
        "doi",
        "journal",
        "url",
        "authors",
        "openalex_id"
    ]

    df_new = df_new.copy()

    for col in keep_cols:
        if col not in df_new.columns:
            df_new[col] = ""

    df_new = df_new[keep_cols]

    if seen_df_old.empty:

        merged = df_new

    else:

        for col in keep_cols:
            if col not in seen_df_old.columns:
                seen_df_old[col] = ""

        seen_df_old = seen_df_old[keep_cols]

        merged = pd.concat([seen_df_old, df_new])

        merged = merged.drop_duplicates(subset=["unique_id"])

    merged.to_csv(SEEN_FILE, index=False, encoding="utf-8-sig")

    logger.info(f"Historical database updated: {len(merged)} records")


# =========================
# Main Pipeline
# =========================
def main():

    try:

        ensure_dirs()

        logger.info("Starting OpenAlex retrieval")

        papers = fetch_papers()

        if not papers:

            pd.DataFrame().to_csv(RAW_OUTPUT_FILE, index=False)

            print("Retrieval completed: 0 papers")

            return

        df = pd.DataFrame(papers)

        logger.info(f"Retrieved {len(df)} papers")

        df = filter_year_range(df)

        logger.info(f"After year filtering: {len(df)}")

        df = deduplicate_batch(df)

        logger.info(f"After batch deduplication: {len(df)}")

        seen_ids, seen_df_old = load_seen()

        before = len(df)

        df = remove_seen(df, seen_ids)

        logger.info(f"Removed historical duplicates: {before-len(df)}")

        df.to_csv(RAW_OUTPUT_FILE, index=False, encoding="utf-8-sig")

        logger.info("Raw output saved")

        update_seen(df, seen_df_old)

        print(f"Retrieval completed: {len(df)} new papers")

    except Exception as e:

        logger.error(f"Retrieval failed: {e}")

        print("Retrieval failed. Please check logs/system.log")


if __name__ == "__main__":
    main()