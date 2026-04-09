# AI Literature Monitoring System

An automated, AI-assisted pipeline for monitoring, filtering, and managing academic literature.

This system integrates paper retrieval, AI-based relevance classification, Zotero synchronization, and automated email reporting into a unified workflow.

## License

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0).

For commercial use, please contact the author.

---

## 📌 Overview

Keeping up with rapidly growing academic literature is increasingly challenging.  
This project provides a lightweight yet extensible system that:

- Continuously collects new research papers
- Filters them using AI relevance classification
- Organizes results into a reference manager (Zotero)
- Delivers summarized updates via email

The system is designed for researchers who need an automated, scalable literature monitoring solution.

---

## ⚙️ Core Features

### 📥 1. Paper Retrieval
- Fetches papers from academic sources (e.g., APIs, predefined queries)
- Supports configurable search topics

### 🤖 2. AI-based Filtering
- Uses LLM (OpenAI API) to evaluate relevance
- Filters noise and prioritizes high-value papers

### 📚 3. Zotero Integration
- Automatically uploads selected papers to a Zotero library
- Enables structured academic reference management

### 📧 4. Email Reporting
- Sends periodic summaries
- Includes selected papers and key metadata

### 🔄 5. Modular Pipeline
- Each step is independent and extendable
- Easy to customize for different research domains

---

## 🏗️ System Architecture

``` id="arch1"
Fetch → AI Filter → Storage → Zotero → Email Report

