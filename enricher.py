#!/usr/bin/env python3
"""
LLM-powered enrichment for economics PhD candidate data.
Uses Perplexity Sonar (cheapest model with built-in search).
Optionally enriches with Google Scholar publication data.
"""
import os
import json
import time
import requests
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

# Try to import scholarly for Google Scholar data
try:
    from scholarly import scholarly, ProxyGenerator
    SCHOLARLY_AVAILABLE = True
except ImportError:
    SCHOLARLY_AVAILABLE = False
    print("Note: scholarly not installed. Scholar enrichment disabled.")
    print("Install with: pip install scholarly")

load_dotenv()

# Import normalization
from normalize import normalize_company, standardize_current_placement

PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

# Lazy-initialize Perplexity client to avoid errors when API key is not set
_perplexity_client = None

def get_perplexity_client():
    """Get or create Perplexity client (lazy initialization)."""
    global _perplexity_client
    if _perplexity_client is None:
        if not PERPLEXITY_API_KEY:
            raise ValueError("PERPLEXITY_API_KEY not set")
        _perplexity_client = OpenAI(
            api_key=PERPLEXITY_API_KEY,
            base_url="https://api.perplexity.ai"
        )
    return _perplexity_client


def enrich_with_sonar(name: str, company: str, school: str, research_fields: str) -> dict:
    """Use Perplexity Sonar (cheapest model with built-in search) to get candidate info."""
    prompt = f"""Find information about this economics PhD graduate who now works in tech:

Name: {name}
Company: {company}
PhD School: {school}
Research Areas: {research_fields}

Search for their LinkedIn profile, personal website, news, or company blog posts about them.

Return a JSON object with these fields:
- current_role: Job title (e.g., "Senior Economist", "Staff Data Scientist")
- current_company: Current employer
- team: Team/org within company (e.g., "Pricing", "Marketplace", "Core Data Science", "Ads Economics")
- work_focus: What they work on - be specific. Pick from or combine these areas:
  * Pricing/revenue optimization
  * Causal inference/experimentation/A-B testing
  * Demand forecasting/prediction
  * Marketplace design/matching algorithms
  * Ads/marketing/attribution
  * Policy/antitrust analysis
  * ML/AI applications
  * Labor economics/HR analytics
  * Supply chain/logistics
  * Search/ranking/recommendations
- notes: Any interesting details
- linkedin_url: LinkedIn URL if found

Return ONLY valid JSON, no other text."""

    try:
        response = get_perplexity_client().chat.completions.create(
            model="sonar",  # Cheapest model with built-in search
            messages=[
                {"role": "system", "content": "You are a research assistant. Search the web and extract structured data about people. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=500
        )
        result_text = response.choices[0].message.content.strip()
        print(f"  Sonar response: {result_text[:100]}...")

        # Parse JSON
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        result_text = result_text.strip()

        return json.loads(result_text)

    except Exception as e:
        print(f"  Sonar error: {e}")
        return {
            "current_role": "Unknown",
            "current_company": company,
            "team": "Unknown",
            "work_focus": "Unknown",
            "notes": f"Error: {e}",
            "linkedin_url": ""
        }


def get_scholar_data(name: str, school: str) -> dict:
    """Fetch Google Scholar data for a candidate."""
    if not SCHOLARLY_AVAILABLE:
        return {'citations': 0, 'h_index': 0, 'publications': [], 'interests': []}

    try:
        print(f"  Searching Google Scholar for: {name}")
        # Search for author
        search_query = scholarly.search_author(f"{name} {school} economics")
        author = next(search_query, None)

        if not author:
            print(f"  No Scholar profile found for {name}")
            return {'citations': 0, 'h_index': 0, 'publications': [], 'interests': []}

        # Fill in details (this fetches additional data)
        author = scholarly.fill(author)

        # Extract top publications
        pubs = author.get('publications', [])[:5]
        top_pubs = []
        for p in pubs:
            bib = p.get('bib', {})
            top_pubs.append({
                'title': bib.get('title', ''),
                'citations': p.get('num_citations', 0)
            })

        result = {
            'citations': author.get('citedby', 0) or 0,
            'h_index': author.get('hindex', 0) or 0,
            'i10_index': author.get('i10index', 0) or 0,
            'interests': author.get('interests', []),
            'publications': top_pubs
        }
        print(f"  Found Scholar profile: {result['citations']} citations, h-index {result['h_index']}")
        return result

    except StopIteration:
        print(f"  No Scholar profile found for {name}")
        return {'citations': 0, 'h_index': 0, 'publications': [], 'interests': []}
    except Exception as e:
        print(f"  Scholar error for {name}: {e}")
        return {'citations': 0, 'h_index': 0, 'publications': [], 'interests': []}




def is_already_enriched(row: pd.Series, check_work_focus: bool = False) -> bool:
    """Check if a row has already been enriched.

    Args:
        row: DataFrame row
        check_work_focus: If True, also require meaningful work_focus value
    """
    notes = str(row.get('notes', '')).strip()
    current_role = str(row.get('current_role', '')).strip()

    # Consider enriched if notes exist (and aren't just error placeholders)
    # or if current_role has a real value
    has_notes = notes and not notes.startswith('Error:')
    has_role = current_role and current_role not in ('', 'Unknown', '0', 'nan')

    basic_enriched = has_notes or has_role

    if check_work_focus:
        work_focus = str(row.get('work_focus', '')).strip()
        has_work_focus = work_focus and work_focus not in ('', 'Unknown', '0', '0.0', 'nan')
        return basic_enriched and has_work_focus

    return basic_enriched


def enrich_candidate(row: pd.Series, include_scholar: bool = True) -> dict:
    """Enrich a single candidate with Sonar (cheapest) and Scholar data."""
    name = row['name']
    company = row['initial_placement']
    school = row.get('school', 'Unknown')
    research_fields = row.get('research_fields', '')

    print(f"\nEnriching: {name} ({company})")

    # Use Perplexity Sonar (cheapest model with built-in search)
    info = enrich_with_sonar(name, company, school, research_fields)

    # Get Google Scholar data if available
    if include_scholar and SCHOLARLY_AVAILABLE:
        scholar_data = get_scholar_data(name, school)
        info['citations'] = scholar_data.get('citations', 0)
        info['h_index'] = scholar_data.get('h_index', 0)
        info['research_interests'] = ', '.join(scholar_data.get('interests', []))
        info['top_publications'] = json.dumps(scholar_data.get('publications', []))
        time.sleep(1)  # Extra rate limiting for Scholar

    time.sleep(0.5)
    return info


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Enrich candidate data with LLM and Scholar')
    parser.add_argument('--no-scholar', action='store_true', help='Skip Google Scholar enrichment')
    parser.add_argument('--force', action='store_true', help='Force re-enrichment of all rows')
    parser.add_argument('--enrich-work-focus', action='store_true',
                        help='Re-enrich rows that have empty/unknown work_focus')
    args = parser.parse_args()

    if not PERPLEXITY_API_KEY:
        print("ERROR: PERPLEXITY_API_KEY not set!")
        return

    include_scholar = not args.no_scholar and SCHOLARLY_AVAILABLE
    print(f"Scholar enrichment: {'enabled' if include_scholar else 'disabled'}")

    input_path = "data/candidates.csv"
    output_path = "data/candidates_enriched.csv"

    # Load existing enriched data if it exists (for incremental enrichment)
    if os.path.exists(output_path) and not args.force:
        print(f"Loading existing enriched data from {output_path}...")
        df = pd.read_csv(output_path)
    else:
        print(f"Loading {input_path}...")
        df = pd.read_csv(input_path)
    print(f"Found {len(df)} candidates")

    # Normalize initial_placement company names (Facebook→Meta, etc.)
    if 'initial_placement' in df.columns:
        df['initial_placement'] = df['initial_placement'].apply(normalize_company)

    # Add new columns (including scholar fields)
    new_cols = [
        'current_role', 'current_company', 'team', 'work_focus', 'notes', 'linkedin_url',
        'citations', 'h_index', 'research_interests', 'top_publications'
    ]
    for col in new_cols:
        if col not in df.columns:
            df[col] = "" if col in ['research_interests', 'top_publications', 'notes', 'linkedin_url'] else 0

    # Enrich each candidate
    skipped = 0
    enriched = 0
    check_work_focus = args.enrich_work_focus
    for idx, row in df.iterrows():
        if not args.force and is_already_enriched(row, check_work_focus=check_work_focus):
            print(f"Skipping already enriched: {row['name']}")
            skipped += 1
            continue

        info = enrich_candidate(row, include_scholar=include_scholar)
        enriched += 1

        # Helper to convert lists/None to strings
        def to_str(val):
            if val is None:
                return ''
            if isinstance(val, list):
                return ', '.join(str(v) for v in val) if val else ''
            return str(val)

        df.at[idx, 'current_role'] = to_str(info.get('current_role', ''))
        # Standardize current_company: academia → "Academia", rebrandings normalized
        raw_company = info.get('current_company', row['initial_placement'])
        df.at[idx, 'current_company'] = standardize_current_placement(raw_company) if raw_company else ''
        df.at[idx, 'team'] = to_str(info.get('team', ''))
        df.at[idx, 'work_focus'] = to_str(info.get('work_focus', ''))
        df.at[idx, 'notes'] = to_str(info.get('notes', ''))
        df.at[idx, 'linkedin_url'] = info.get('linkedin_url', '')

        # Scholar fields
        df.at[idx, 'citations'] = info.get('citations', 0)
        df.at[idx, 'h_index'] = info.get('h_index', 0)
        df.at[idx, 'research_interests'] = info.get('research_interests', '')
        df.at[idx, 'top_publications'] = info.get('top_publications', '[]')

        # Save progress
        df.to_csv(output_path, index=False)

    print(f"\n{'='*50}")
    print(f"Done! Enriched {enriched}, skipped {skipped} already-enriched candidates")
    print(f"Saved to {output_path}")
    print(df[['name', 'initial_placement', 'current_role', 'citations', 'h_index']].head(10))


if __name__ == "__main__":
    main()
