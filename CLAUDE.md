# econ-grads

Track where Economics PhD graduates land in tech to infer quality of tech firms.

## Goals

- goal is to get a sense of where econ phd are going in tech to try to infer the quality of the tech firm itself. 
- we will: scrape, parse via LLMs, structure and create a dataset first. 
- focus only on tech jobs nothing else
- try to gather as much info as possible
- data analysis and visualization at the end
- info like: name, school, year, initial placement, current placement, initial role, current role. 
- optional info: teams, role, location, role description, field
- range: last 10 years, all top 20 schools, economics, tech jobs only (at least those initially placed in tech)

## Project Structure

```
econ-grads/
├── CLAUDE.md              # This file
├── scraper.py             # Web scraper with Selenium fallback + incremental scraping
├── enricher.py            # Perplexity Sonar + Google Scholar enrichment
├── compensation.py        # H1B salary + Levels.fyi data
├── scoring.py             # Company quality scoring
├── analyze.py             # Data analysis functions
├── charts.py              # Visualization generator
├── normalize.py           # Company name normalization
├── cleanup.py             # Data cleanup utilities
├── expand_search.py       # Search expansion utilities
├── network.py             # Network analysis
├── pdf_parser.py          # PDF parsing for placement data
├── ranking_charts.py      # Additional ranking visualizations
├── work_tags.py           # Work focus tagging
├── requirements.txt       # Python dependencies
├── parsers/               # School-specific parsers (24 schools)
│   ├── __init__.py
│   ├── base.py            # Base parser class
│   └── {school}.py        # berkeley, brown, cmu, columbia, cornell, duke,
│                          # harvard, illinois, maryland, michigan, minnesota,
│                          # mit, northwestern, nyu, penn, princeton, stanford,
│                          # uchicago, ucla, utaustin, virginia, washington,
│                          # wisconsin, yale
├── data/
│   ├── candidates.csv          # Main dataset
│   ├── candidates_enriched.csv # With Sonar + Scholar data
│   ├── company_scores.csv      # Quality rankings (generated)
│   ├── scrape_state.json       # Incremental scrape state
│   ├── raw/                    # Cached HTML for debugging
│   └── h1b_lca.csv             # H1B salary data (manual download)
├── tests/
│   └── test_e2e.py             # E2E tests (pytest)
└── charts/                     # Generated visualizations
    └── *.png                   # Static charts
```

## Data Schema

`data/candidates.csv` columns:

| Column | Description |
|--------|-------------|
| `name` | Candidate full name |
| `school` | PhD-granting institution |
| `graduation_year` | Year of PhD completion |
| `research_fields` | Research specializations |
| `initial_placement` | First job after PhD |
| `initial_role` | Title at initial placement |
| `current_placement` | Current employer |
| `current_role` | Current job title |
| `linkedin_url` | LinkedIn profile URL |

## Schools Tracked (24)

Berkeley, Brown, CMU, Columbia, Cornell, Duke, Harvard, Illinois, Maryland, Michigan, Minnesota, MIT, Northwestern, NYU, Penn, Princeton, Stanford, UChicago, UCLA, UT Austin, Virginia, Washington, Wisconsin, Yale

## Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                        PIPELINE STAGES                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. SCRAPE        python scraper.py                             │
│     └─> Pulls placement data from 24 university websites        │
│         Output: data/candidates.csv                             │
│                                                                 │
│  2. ENRICH        python enricher.py        [OPTIONAL]          │
│     └─> Adds LinkedIn, publications, research interests         │
│         Requires: PERPLEXITY_API_KEY env var                    │
│         Output: data/candidates_enriched.csv                    │
│                                                                 │
│  3. COMPENSATION  python compensation.py    [OPTIONAL]          │
│     └─> Adds salary data from H1B filings                       │
│         Requires: data/h1b_lca.csv (manual download from DOL)   │
│                                                                 │
│  4. SCORE         python scoring.py                             │
│     └─> Ranks companies by PhD talent quality                   │
│         Output: data/company_scores.csv                         │
│                                                                 │
│  5. ANALYZE       python analyze.py                             │
│     └─> Prints summary stats to console                         │
│                                                                 │
│  6. VISUALIZE     python charts.py                              │
│     └─> Generates PNG charts                                    │
│         Output: charts/*.png                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
pip install -r requirements.txt
python scraper.py    # Get base data from university websites
python scoring.py    # Score companies by PhD talent
python analyze.py    # See summary results
python charts.py     # Generate visualizations
```

## Command Reference

```bash
# Scraping
python scraper.py              # Incremental scrape (only changed pages)
python scraper.py --force      # Full re-scrape (ignore cache)

# Enrichment (requires PERPLEXITY_API_KEY)
python enricher.py             # Full enrichment with Google Scholar
python enricher.py --no-scholar  # Skip Scholar (faster)

# Compensation (requires data/h1b_lca.csv)
# Download from: https://www.dol.gov/agencies/eta/foreign-labor/performance
python compensation.py

# Analysis & Visualization
python scoring.py              # Generate company quality scores
python analyze.py              # Print analysis to console
python charts.py               # Generate charts to charts/

# Testing
pytest tests/ -v
```

## Charts Generated

| Chart | File | Description |
|-------|------|-------------|
| Placements by School | `school_placements.png` | Bar chart by university |
| Top Companies | `top_companies.png` | Bar chart of hiring companies |
| School×Company | `heatmap.png` | Placement matrix |
| Timeline | `timeline.png` | Placements by year |
| Role Types | `roles.png` | Job title distribution |

## Tech Companies Tracked

100+ companies including:
- **FAANG+:** Google, Meta, Amazon, Apple, Microsoft, Netflix
- **Unicorns:** Uber, Airbnb, Stripe, DoorDash, Instacart
- **AI/ML:** OpenAI, Anthropic, DeepMind, Scale AI
- **Fintech:** Two Sigma, Jane Street, Citadel, Capital One
- **Enterprise:** Salesforce, Snowflake, Palantir, Databricks
