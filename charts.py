#!/usr/bin/env python3
"""Generate visualizations for Economics PhD tech placements."""

import re
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import networkx as nx
from datetime import datetime
from wordcloud import WordCloud
from pathlib import Path
from work_tags import (
    WORK_TAGS,
    DOMAIN_TAGS,
    METHOD_TAGS,
    categorize_with_fractional_allocation,
    aggregate_fractional_counts,
    extract_ngrams,
)

# Paths
DATA_PATH = Path(__file__).parent / "data" / "candidates_enriched.csv"
CHARTS_DIR = Path(__file__).parent / "charts"

# Dark theme colors
COLORS = {
    "bg": "#1a1a2e",
    "surface": "#16213e",
    "primary": "#e94560",
    "secondary": "#0f3460",
    "accent": "#00d9ff",
    "text": "#eaeaea",
    "grid": "#2a2a4a",
}

PALETTE = ["#e94560", "#00d9ff", "#ffd369", "#7b68ee", "#50fa7b", "#ff79c6", "#bd93f9", "#f1fa8c"]

# Finance firms to exclude from all charts (focus on tech only)
FINANCE_FIRMS = {
    'Jane Street', 'Two Sigma', 'Citadel', 'Susquehanna', 'DE Shaw', 'D.E. Shaw',
    'Vanguard', 'BlackRock', 'Goldman Sachs', 'Morgan Stanley', 'JP Morgan',
    'JPMorgan', 'Bridgewater', 'Renaissance', 'Point72', 'Millennium',
    'Susquehanna International Group', 'Two Sigma Investments', 'Squarepoint',
    'Capital One', 'Fidelity', 'Charles Schwab', 'Robinhood', 'Coinbase'
}

# Non-tech category keywords for career transition analysis
NON_TECH_CATEGORIES = {
    'Academia': ['professor', 'faculty', 'assistant prof', 'university', 'college', 'mit', 'stanford', 'berkeley', 'nyu', 'yale', 'harvard', 'academia'],
    'Government': ['government', 'fed ', 'federal', 'treasury', 'intelligence', 'policy', 'u.s.', 'bureau', 'bea'],
    'Consulting': ['consulting', 'nera', 'cornerstone', 'analysis group', 'mckinsey', 'bain', 'bcg'],
    'Finance (Trad)': ['bank', 'capital', 'investment', 'vanguard', 'fidelity', 'jpmorgan', 'goldman'],
}


def setup_dark_theme():
    """Configure matplotlib for dark theme."""
    plt.style.use("dark_background")
    plt.rcParams.update({
        "figure.facecolor": COLORS["bg"],
        "axes.facecolor": COLORS["surface"],
        "axes.edgecolor": COLORS["grid"],
        "axes.labelcolor": COLORS["text"],
        "text.color": COLORS["text"],
        "xtick.color": COLORS["text"],
        "ytick.color": COLORS["text"],
        "grid.color": COLORS["grid"],
        "figure.figsize": (12, 7),
        "font.size": 11,
        "axes.titlesize": 14,
        "axes.labelsize": 12,
    })


def load_data() -> pd.DataFrame:
    """Load the candidates dataset (tech only, excludes finance firms)."""
    df = pd.read_csv(DATA_PATH)
    # Filter to 2014 and later only
    if 'graduation_year' in df.columns:
        df = df[df['graduation_year'] >= 2014]
    # Filter out finance firms
    if 'initial_placement' in df.columns:
        df = df[~df['initial_placement'].isin(FINANCE_FIRMS)]
    return df


def chart_placements_by_school(df: pd.DataFrame) -> None:
    """Bar chart of placements by school."""
    data = df["school"].value_counts()

    fig, ax = plt.subplots()
    bars = ax.barh(data.index[::-1], data.values[::-1], color=PALETTE[:len(data)])
    ax.set_xlabel("Number of Candidates")
    ax.set_title("PhD Placements by School", fontweight="bold", color=COLORS["primary"])
    ax.bar_label(bars, padding=5)
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "school_placements.png", dpi=150, facecolor=COLORS["bg"])
    plt.close()
    print("  - school_placements.png")


def chart_top_companies(df: pd.DataFrame, top_n: int = 20) -> None:
    """Bar chart of top hiring companies (tech only)."""
    data = df["initial_placement"].value_counts().head(top_n)

    fig, ax = plt.subplots()
    bars = ax.barh(data.index[::-1], data.values[::-1], color=COLORS["accent"])
    ax.set_xlabel("Number of Placements")
    ax.set_title("Top Hiring Companies", fontweight="bold", color=COLORS["primary"])
    ax.bar_label(bars, padding=5)
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "top_companies.png", dpi=150, facecolor=COLORS["bg"])
    plt.close()
    print("  - top_companies.png")


def chart_heatmap(df: pd.DataFrame) -> None:
    """Heatmap of school vs company placements."""
    matrix = pd.crosstab(df["school"], df["initial_placement"])
    matrix = matrix.loc[:, matrix.sum() >= 2]

    if matrix.empty:
        print("  - heatmap.png (skipped - insufficient data)")
        return

    fig, ax = plt.subplots(figsize=(14, 8))
    sns.heatmap(
        matrix, annot=True, fmt="d", cmap="magma",
        linewidths=0.5, linecolor=COLORS["grid"],
        cbar_kws={"label": "Placements"}, ax=ax,
    )
    ax.set_title("School × Company Placement Matrix", fontweight="bold", color=COLORS["primary"])
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "heatmap.png", dpi=150, facecolor=COLORS["bg"])
    plt.close()
    print("  - heatmap.png")


def chart_timeline(df: pd.DataFrame) -> None:
    """Timeline of placements by graduation year."""
    data = df["graduation_year"].value_counts().sort_index()

    fig, ax = plt.subplots()
    ax.fill_between(data.index, data.values, alpha=0.3, color=COLORS["accent"])
    ax.plot(data.index, data.values, marker="o", color=COLORS["accent"], linewidth=2, markersize=8)
    ax.set_xlabel("Graduation Year")
    ax.set_ylabel("Number of Placements")
    ax.set_title("Tech Placements by Year", fontweight="bold", color=COLORS["primary"])
    ax.set_xticks(data.index)
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "timeline.png", dpi=150, facecolor=COLORS["bg"])
    plt.close()
    print("  - timeline.png")


def chart_roles(df: pd.DataFrame) -> None:
    """Pie chart of role distribution."""
    roles = df["current_role"].dropna()
    roles = roles[roles != ""]

    if len(roles) == 0:
        print("  - roles.png (skipped - no role data)")
        return

    categories = {
        "Economist": ["economist", "principal economist", "senior economist"],
        "Data Scientist": ["data scientist", "senior data scientist", "analyst"],
        "Applied Scientist": ["applied scientist", "senior applied scientist"],
        "Research Scientist": ["research scientist", "researcher", "scientist", "investigator"],
        "Quant Researcher": ["quant", "quantitative"],
        "Academic": ["professor", "prof", "assistant prof", "postdoc"],
        "Manager/Director": ["manager", "director", "lead"],
        "ML Engineer": ["ml engineer", "machine learning"],
    }

    def categorize(role: str) -> str:
        role_lower = role.lower()
        for cat, keywords in categories.items():
            for kw in keywords:
                if kw in role_lower:
                    return cat
        return "Other"

    role_cats = roles.apply(categorize).value_counts()

    fig, ax = plt.subplots()
    wedges, texts, autotexts = ax.pie(
        role_cats.values, labels=role_cats.index, autopct="%1.0f%%",
        colors=PALETTE[:len(role_cats)],
        wedgeprops=dict(linewidth=2, edgecolor=COLORS["bg"]),
    )
    for text in autotexts:
        text.set_color(COLORS["bg"])
        text.set_fontweight("bold")
    ax.set_title("Current Role Distribution", fontweight="bold", color=COLORS["primary"])
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "roles.png", dpi=150, facecolor=COLORS["bg"])
    plt.close()
    print("  - roles.png")


def chart_research_to_company(df: pd.DataFrame) -> None:
    """Research Field → Company as stacked bar (rank ordered)."""
    # Generic terms to exclude - these are not real research specializations
    GENERIC_TERMS = {
        'economics', 'economist', 'economic', 'phd', 'ph.d', 'applied',
        'theory', 'microeconomics', 'microeconomic'  # too broad
    }

    rows = []
    for _, r in df.iterrows():
        fields = str(r.get('research_fields', '')).split(',')
        for field in fields:
            field = field.strip()
            # Skip empty, nan, and generic terms
            if field and field != 'nan' and field.lower() not in GENERIC_TERMS:
                rows.append({'field': field[:30], 'company': r['initial_placement']})

    if not rows:
        print("  - research_to_company.png (skipped - no data)")
        return

    field_df = pd.DataFrame(rows)

    # Get field counts and sort by total (rank order)
    field_counts = field_df['field'].value_counts()
    top_fields = field_counts.head(12).index.tolist()
    top_companies = field_df['company'].value_counts().head(6).index
    field_df = field_df[field_df['field'].isin(top_fields) & field_df['company'].isin(top_companies)]

    matrix = pd.crosstab(field_df['field'], field_df['company'])

    # Sort by total count (rank order) - descending so highest is at top of horizontal bar
    matrix['_total'] = matrix.sum(axis=1)
    matrix = matrix.sort_values('_total', ascending=True)  # ascending for barh (bottom to top)
    matrix = matrix.drop('_total', axis=1)

    fig, ax = plt.subplots(figsize=(12, 8))
    matrix.plot(kind='barh', stacked=True, ax=ax, color=PALETTE[:len(matrix.columns)])
    ax.set_xlabel("Count")
    ax.set_title("Research Fields → Company Placements (Ranked)", fontweight="bold", color=COLORS["primary"])
    ax.legend(title="Company", bbox_to_anchor=(1.02, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "research_to_company.png", dpi=150, facecolor=COLORS["bg"])
    plt.close()
    print("  - research_to_company.png")


def chart_field_to_firm(df: pd.DataFrame) -> None:
    """Field → Firm mapping: which research fields go to which companies."""
    # Generic terms to exclude
    GENERIC_TERMS = {
        'economics', 'economist', 'economic', 'phd', 'ph.d', 'applied',
        'theory', 'microeconomics', 'microeconomic'
    }

    rows = []
    for _, r in df.iterrows():
        fields = str(r.get('research_fields', '')).split(',')
        for field in fields:
            field = field.strip()
            if field and field != 'nan' and field.lower() not in GENERIC_TERMS:
                rows.append({'field': field[:30], 'company': r['initial_placement']})

    if not rows:
        print("  - field_to_firm.png (skipped - no data)")
        return

    field_df = pd.DataFrame(rows)

    # Get top fields and all companies with 2+ hires
    field_counts = field_df['field'].value_counts()
    top_fields = field_counts[field_counts >= 2].head(15).index.tolist()
    company_counts = field_df['company'].value_counts()
    top_companies = company_counts[company_counts >= 2].index.tolist()

    field_df_filtered = field_df[field_df['field'].isin(top_fields) & field_df['company'].isin(top_companies)]

    if len(field_df_filtered) == 0:
        print("  - field_to_firm.png (skipped - no data after filtering)")
        return

    matrix = pd.crosstab(field_df_filtered['field'], field_df_filtered['company'])

    # Sort fields by total hires (descending)
    matrix = matrix.loc[matrix.sum(axis=1).sort_values(ascending=False).index]
    # Sort companies by total hires (descending)
    matrix = matrix[matrix.sum(axis=0).sort_values(ascending=False).index]

    fig, ax = plt.subplots(figsize=(14, 10))
    sns.heatmap(
        matrix, annot=True, fmt="d", cmap="YlOrRd",
        linewidths=0.5, linecolor=COLORS["grid"],
        cbar_kws={"label": "Hires"}, ax=ax,
    )
    ax.set_title("Research Field → Firm Mapping", fontweight="bold", color=COLORS["primary"])
    ax.set_xlabel("Company")
    ax.set_ylabel("Research Field")
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "field_to_firm.png", dpi=150, facecolor=COLORS["bg"])
    plt.close()
    print("  - field_to_firm.png")


def chart_teams(df: pd.DataFrame) -> None:
    """Bar chart of teams/orgs people join."""
    teams = df['team'].dropna()
    teams = teams[(teams != '') & (teams != 'nan') & (teams != '0') & (teams != '0.0')]

    if len(teams) == 0:
        print("  - teams.png (skipped - no team data)")
        return

    team_keywords = {
        'AI/ML': ['ai', 'machine learning', 'ml', 'artificial intelligence'],
        'Pricing': ['pricing', 'price'],
        'Economics': ['economics', 'economist', 'econometrics'],
        'Data Science': ['data science', 'data r&d'],
        'Policy/Research': ['policy', 'research'],
        'Marketing': ['marketing', 'ads'],
        'Marketplace': ['marketplace', 'platform'],
        'Forecasting': ['forecasting', 'forecast'],
    }

    def categorize_team(team: str) -> str:
        team_lower = str(team).lower()
        for cat, keywords in team_keywords.items():
            for kw in keywords:
                if kw in team_lower:
                    return cat
        return "Other"

    team_cats = teams.apply(categorize_team).value_counts()

    fig, ax = plt.subplots()
    bars = ax.barh(team_cats.index[::-1], team_cats.values[::-1], color=PALETTE[:len(team_cats)])
    ax.set_xlabel("Count")
    ax.set_title("Teams/Orgs Econ PhDs Join", fontweight="bold", color=COLORS["primary"])
    ax.bar_label(bars, padding=5)
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "teams.png", dpi=150, facecolor=COLORS["bg"])
    plt.close()
    print("  - teams.png")


def _get_work_texts(df: pd.DataFrame) -> list:
    """Extract combined work_focus + team texts from dataframe."""
    work_texts = []
    for _, row in df.iterrows():
        work_focus = str(row.get('work_focus', '')).strip()
        team = str(row.get('team', '')).strip()
        combined = f"{work_focus} {team}".strip()
        if combined and combined not in ('nan', '0', '0.0', 'nan nan'):
            work_texts.append(combined)
    return work_texts


def chart_work_domains(df: pd.DataFrame) -> None:
    """Bar chart of work DOMAINS (what area they work in)."""
    work_texts = _get_work_texts(df)

    if len(work_texts) == 0:
        print("  - work_domains.png (skipped - no data)")
        return

    # Get fractional allocations using DOMAIN_TAGS only
    allocations = [categorize_with_fractional_allocation(text, DOMAIN_TAGS) for text in work_texts]
    totals = aggregate_fractional_counts(allocations)

    # Sort by count, exclude Other
    sorted_cats = sorted([(k, v) for k, v in totals.items() if k != 'Other'], key=lambda x: x[1], reverse=True)
    categories = [c[0] for c in sorted_cats]
    counts = [c[1] for c in sorted_cats]

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(categories[::-1], counts[::-1], color=PALETTE[:len(categories)])
    ax.set_xlabel("Fractional Count")
    ax.set_title("Work Domains: What Areas Econ PhDs Work In", fontweight="bold", color=COLORS["primary"])
    ax.bar_label(bars, fmt='%.1f', padding=5)
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "work_domains.png", dpi=150, facecolor=COLORS["bg"])
    plt.close()
    print(f"  - work_domains.png ({len(work_texts)} candidates)")


def chart_work_methods(df: pd.DataFrame) -> None:
    """Bar chart of work METHODS (what techniques they use)."""
    work_texts = _get_work_texts(df)

    if len(work_texts) == 0:
        print("  - work_methods.png (skipped - no data)")
        return

    # Get fractional allocations using METHOD_TAGS only
    allocations = [categorize_with_fractional_allocation(text, METHOD_TAGS) for text in work_texts]
    totals = aggregate_fractional_counts(allocations)

    # Sort by count, exclude Other
    sorted_cats = sorted([(k, v) for k, v in totals.items() if k != 'Other'], key=lambda x: x[1], reverse=True)
    categories = [c[0] for c in sorted_cats]
    counts = [c[1] for c in sorted_cats]

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(categories[::-1], counts[::-1], color=COLORS["accent"])
    ax.set_xlabel("Fractional Count")
    ax.set_title("Work Methods: What Techniques Econ PhDs Use", fontweight="bold", color=COLORS["primary"])
    ax.bar_label(bars, fmt='%.1f', padding=5)
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "work_methods.png", dpi=150, facecolor=COLORS["bg"])
    plt.close()
    print(f"  - work_methods.png ({len(work_texts)} candidates)")


def chart_work_ngrams(df: pd.DataFrame) -> None:
    """Bar chart of top ngrams extracted from work_focus and team fields."""
    # Words to filter out (company names, generic org terms)
    FILTER_WORDS = {
        'amazon', 'uber', 'meta', 'google', 'microsoft', 'apple', 'netflix',
        'facebook', 'airbnb', 'lyft', 'stripe', 'doordash', 'instacart',
        'team', 'group', 'science', 'services', 'web', 'eats', 'prime',
        'intelligence', 'central', 'applied', 'core'
    }

    # Collect all work-related text, splitting on slashes/commas to get separate phrases
    work_phrases = set()  # Use set to deduplicate
    for _, row in df.iterrows():
        work_focus = str(row.get('work_focus', '')).strip()
        team = str(row.get('team', '')).strip()
        # Prefer work_focus over team (more descriptive)
        text = work_focus if work_focus and work_focus not in ('nan', '0', '0.0', 'Unknown') else team
        if text and text not in ('nan', '0', '0.0', 'Unknown'):
            # Split on slashes and commas to get separate phrases
            for phrase in re.split(r'[/,]', text):
                phrase = phrase.strip()
                if phrase and len(phrase) > 3:
                    work_phrases.add(phrase)

    work_texts = list(work_phrases)

    if len(work_texts) < 3:
        print("  - work_ngrams.png (skipped - insufficient data)")
        return

    # Extract bigrams from unique phrases
    all_bigrams = extract_ngrams(work_texts, n=2, top_k=50)

    # Filter out bigrams containing company/org terms
    bigrams = []
    for bg, count in all_bigrams:
        words = bg.split()
        if not any(w in FILTER_WORDS for w in words):
            bigrams.append((bg, count))
        if len(bigrams) >= 15:
            break

    if not bigrams:
        print("  - work_ngrams.png (skipped - no ngrams found)")
        return

    labels = [bg[0] for bg in bigrams]
    counts = [bg[1] for bg in bigrams]

    fig, ax = plt.subplots(figsize=(10, 7))
    bars = ax.barh(labels[::-1], counts[::-1], color=COLORS["accent"])
    ax.set_xlabel("Frequency")
    ax.set_title("Top Work Focus Phrases (Extracted Bigrams)", fontweight="bold", color=COLORS["primary"])
    ax.bar_label(bars, padding=5)
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "work_ngrams.png", dpi=150, facecolor=COLORS["bg"])
    plt.close()
    print(f"  - work_ngrams.png ({len(work_texts)} text samples)")


def chart_company_roles(df: pd.DataFrame) -> None:
    """Heatmap: Company × Role type."""
    categories = {
        "Economist": ["economist"],
        "Data Scientist": ["data scientist"],
        "Applied Scientist": ["applied scientist"],
        "ML Engineer": ["ml engineer", "machine learning engineer"],
        "Researcher": ["researcher", "research scientist"],
        "Manager": ["manager", "director", "lead"],
    }

    def categorize(role: str) -> str:
        if pd.isna(role) or role == '':
            return None
        role_lower = str(role).lower()
        for cat, keywords in categories.items():
            for kw in keywords:
                if kw in role_lower:
                    return cat
        return "Other"

    df_copy = df.copy()
    df_copy['role_cat'] = df_copy['current_role'].apply(categorize)
    df_copy = df_copy[df_copy['role_cat'].notna()]

    if len(df_copy) == 0:
        print("  - company_roles.png (skipped - no data)")
        return

    top_companies = df_copy['initial_placement'].value_counts().head(8).index
    df_filtered = df_copy[df_copy['initial_placement'].isin(top_companies)]
    matrix = pd.crosstab(df_filtered['initial_placement'], df_filtered['role_cat'])

    fig, ax = plt.subplots(figsize=(12, 8))
    sns.heatmap(matrix, annot=True, fmt="d", cmap="YlOrRd",
                linewidths=0.5, linecolor=COLORS["grid"], ax=ax)
    ax.set_title("Company × Role Distribution", fontweight="bold", color=COLORS["primary"])
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "company_roles.png", dpi=150, facecolor=COLORS["bg"])
    plt.close()
    print("  - company_roles.png")


def chart_movers(df: pd.DataFrame) -> None:
    """Who changed companies? Initial vs Current."""
    df_copy = df.copy()
    df_copy['current_company'] = df_copy['current_company'].fillna(df_copy['initial_placement'])
    df_copy['moved'] = df_copy.apply(
        lambda r: str(r['initial_placement']).lower().strip() != str(r['current_company']).lower().strip()
        if pd.notna(r['current_company']) and r['current_company'] not in ['', '0', '0.0', 'nan']
        else False,
        axis=1
    )

    movers = df_copy[df_copy['moved']]

    if len(movers) == 0:
        print("  - movers.png (skipped - no job changes)")
        return

    # Create transition labels
    transitions = movers.apply(lambda r: f"{r['initial_placement']} → {r['current_company']}", axis=1)
    trans_counts = transitions.value_counts().head(15)

    fig, ax = plt.subplots(figsize=(12, 8))
    bars = ax.barh(trans_counts.index[::-1], trans_counts.values[::-1], color=COLORS["accent"])
    ax.set_xlabel("Count")
    ax.set_title(f"Career Moves ({len(movers)} people changed companies)", fontweight="bold", color=COLORS["primary"])
    ax.bar_label(bars, padding=5)
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "movers.png", dpi=150, facecolor=COLORS["bg"])
    plt.close()
    print("  - movers.png")


def chart_school_to_role(df: pd.DataFrame) -> None:
    """Stacked bar: School → Role type."""
    categories = {
        "Economist": ["economist"],
        "Data Scientist": ["data scientist"],
        "Applied Scientist": ["applied scientist"],
        "ML/Research": ["ml", "machine learning", "researcher", "research scientist"],
        "Academic": ["professor", "postdoc"],
        "Manager": ["manager", "director"],
    }

    def categorize(role: str) -> str:
        if pd.isna(role) or role == '':
            return None
        role_lower = str(role).lower()
        for cat, keywords in categories.items():
            for kw in keywords:
                if kw in role_lower:
                    return cat
        return "Other"

    df_copy = df.copy()
    df_copy['role_cat'] = df_copy['current_role'].apply(categorize)
    df_copy = df_copy[df_copy['role_cat'].notna()]

    if len(df_copy) == 0:
        print("  - school_to_role.png (skipped - no data)")
        return

    matrix = pd.crosstab(df_copy['school'], df_copy['role_cat'])

    fig, ax = plt.subplots(figsize=(12, 8))
    matrix.plot(kind='barh', stacked=True, ax=ax, color=PALETTE[:len(matrix.columns)])
    ax.set_xlabel("Count")
    ax.set_title("School → Role Type Distribution", fontweight="bold", color=COLORS["primary"])
    ax.legend(title="Role", bbox_to_anchor=(1.02, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "school_to_role.png", dpi=150, facecolor=COLORS["bg"])
    plt.close()
    print("  - school_to_role.png")


def chart_selectivity(df: pd.DataFrame) -> None:
    """Show which schools each company hires from (target school analysis)."""
    # Get company-school counts
    cross = pd.crosstab(df['initial_placement'], df['school'])

    # Filter to companies with 3+ hires for meaningful analysis
    min_hires = 3
    company_totals = cross.sum(axis=1)
    cross = cross[company_totals >= min_hires]

    if len(cross) == 0:
        print("  - selectivity.png (skipped - not enough data)")
        return

    # Convert to percentages
    cross_pct = cross.div(cross.sum(axis=1), axis=0) * 100

    # Sort companies by total hires (descending)
    cross_pct = cross_pct.loc[company_totals[company_totals >= min_hires].sort_values(ascending=False).index]

    # Only show schools that appear in at least one company
    cross_pct = cross_pct.loc[:, (cross_pct > 0).any(axis=0)]

    # Sort schools by total representation
    school_totals = cross_pct.sum(axis=0).sort_values(ascending=False)
    cross_pct = cross_pct[school_totals.index]

    # Create stacked bar chart
    fig, ax = plt.subplots(figsize=(14, 8))

    # Use color palette for schools
    n_schools = len(cross_pct.columns)
    colors = plt.cm.tab20(np.linspace(0, 1, min(20, n_schools)))

    cross_pct.plot(kind='barh', stacked=True, ax=ax, color=colors, width=0.7)

    ax.set_xlabel("% of Hires from Each School", color=COLORS["text"])
    ax.set_ylabel("")
    ax.set_title("Target Schools by Company\n(Which schools do companies hire from?)",
                 fontweight="bold", color=COLORS["primary"], fontsize=14)

    # Add hire counts as annotations
    for i, (company, total) in enumerate(company_totals[company_totals >= min_hires].sort_values(ascending=False).items()):
        ax.text(102, i, f'n={int(total)}', va='center', fontsize=9, color=COLORS["text"])

    ax.set_xlim(0, 115)
    ax.legend(title="School", bbox_to_anchor=(1.15, 1), loc='upper left', fontsize=8)

    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "selectivity.png", dpi=150, facecolor=COLORS["bg"], bbox_inches='tight')
    plt.close()
    print("  - selectivity.png")


def chart_network_graph(df: pd.DataFrame) -> None:
    """Network graph of talent flows between companies."""
    # Build transition graph
    df_copy = df.copy()
    df_copy['current_co'] = df_copy['current_company'].fillna(df_copy['initial_placement'])

    # Create edges from initial -> current (only if different)
    edges = []
    for _, row in df_copy.iterrows():
        initial = str(row['initial_placement']).strip()
        current = str(row['current_co']).strip()
        if initial and current and initial.lower() != current.lower() and current not in ['nan', '0', '0.0', '']:
            edges.append((initial, current))

    if not edges:
        print("  - network_graph.png (skipped - no transitions)")
        return

    # Count edges
    from collections import Counter
    edge_counts = Counter(edges)

    # Build NetworkX graph
    G = nx.DiGraph()

    # Add nodes with attributes
    company_counts = df['initial_placement'].value_counts()
    for company in set(list(company_counts.index) + [e[1] for e in edges]):
        G.add_node(company, size=company_counts.get(company, 1))

    # Add weighted edges
    for (src, dst), weight in edge_counts.items():
        G.add_edge(src, dst, weight=weight)

    # Only keep nodes with at least 1 edge or >= 3 hires
    nodes_to_keep = set()
    for node in G.nodes():
        if G.in_degree(node) > 0 or G.out_degree(node) > 0 or company_counts.get(node, 0) >= 3:
            nodes_to_keep.add(node)
    G = G.subgraph(nodes_to_keep).copy()

    if len(G.nodes()) < 2:
        print("  - network_graph.png (skipped - not enough connected nodes)")
        return

    # Draw with matplotlib
    fig, ax = plt.subplots(figsize=(16, 12))

    # Layout
    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)

    # Node sizes based on hires
    node_sizes = [G.nodes[n].get('size', 1) * 100 + 200 for n in G.nodes()]

    # Edge widths based on transition count
    edge_widths = [G.edges[e].get('weight', 1) * 1.5 for e in G.edges()]

    # Draw
    nx.draw_networkx_nodes(G, pos, ax=ax, node_size=node_sizes,
                           node_color=COLORS['accent'], alpha=0.9)
    nx.draw_networkx_edges(G, pos, ax=ax, width=edge_widths,
                           edge_color=COLORS['primary'], alpha=0.6,
                           arrows=True, arrowsize=15,
                           connectionstyle="arc3,rad=0.1")
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=8, font_color=COLORS['text'])

    ax.set_title("Talent Flow Network\n(Arrows show career transitions, node size = hire count)",
                 fontweight="bold", color=COLORS["primary"], fontsize=14)
    ax.axis('off')

    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "network_graph.png", dpi=150, facecolor=COLORS["bg"], bbox_inches='tight')
    plt.close()
    print("  - network_graph.png")


def chart_career_progression(df: pd.DataFrame) -> None:
    """Multi-panel career progression analysis."""
    df_copy = df.copy()
    df_copy['current_co'] = df_copy['current_company'].fillna(df_copy['initial_placement'])
    df_copy['moved'] = df_copy.apply(
        lambda r: str(r['initial_placement']).lower().strip() != str(r['current_co']).lower().strip()
        if pd.notna(r['current_co']) and str(r['current_co']) not in ['', '0', '0.0', 'nan']
        else False,
        axis=1
    )

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 1. Retention by top companies
    ax1 = axes[0, 0]
    top_companies = df_copy['initial_placement'].value_counts().head(8).index
    retention_data = []
    for company in top_companies:
        company_df = df_copy[df_copy['initial_placement'] == company]
        retained = (~company_df['moved']).sum()
        retention_data.append({'company': company, 'retention': retained / len(company_df) * 100})
    ret_df = pd.DataFrame(retention_data).sort_values('retention', ascending=True)
    bars = ax1.barh(ret_df['company'], ret_df['retention'], color=COLORS['accent'])
    ax1.set_xlabel("Retention Rate (%)")
    ax1.set_title("Retention by Company", fontweight="bold", color=COLORS["primary"])
    ax1.bar_label(bars, fmt='%.0f%%', padding=5)
    ax1.set_xlim(0, 110)

    # 2. Where movers go (destination companies)
    ax2 = axes[0, 1]
    movers = df_copy[df_copy['moved']]
    if len(movers) > 0:
        dest_counts = movers['current_co'].value_counts().head(10)
        bars = ax2.barh(dest_counts.index[::-1], dest_counts.values[::-1], color=COLORS['accent'])
        ax2.set_xlabel("Count")
        ax2.set_title("Where Job Changers Go", fontweight="bold", color=COLORS["primary"])
        ax2.bar_label(bars, padding=5)

    # 3. Popular transitions
    ax3 = axes[1, 0]
    if len(movers) > 0:
        transitions = movers.apply(lambda r: f"{r['initial_placement']} → {r['current_co']}", axis=1)
        trans_counts = transitions.value_counts().head(10)
        bars = ax3.barh(trans_counts.index[::-1], trans_counts.values[::-1], color=COLORS['primary'])
        ax3.set_xlabel("Count")
        ax3.set_title("Top Career Transitions", fontweight="bold", color=COLORS["primary"])
        ax3.bar_label(bars, padding=5)

    # 4. Mobility by graduation year
    ax4 = axes[1, 1]
    mobility_by_year = df_copy.groupby('graduation_year')['moved'].mean() * 100
    ax4.bar(mobility_by_year.index, mobility_by_year.values, color=COLORS['accent'])
    ax4.set_xlabel("Graduation Year")
    ax4.set_ylabel("% Who Changed Jobs")
    ax4.set_title("Mobility by Cohort", fontweight="bold", color=COLORS["primary"])

    plt.suptitle("Career Progression Analysis", fontsize=16, fontweight="bold", color=COLORS["text"], y=1.02)
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "career_progression.png", dpi=150, facecolor=COLORS["bg"], bbox_inches='tight')
    plt.close()
    print("  - career_progression.png")


def chart_correlations(df: pd.DataFrame) -> None:
    """Heatmap of correlations between variables (descriptive, no quality scores)."""
    df_copy = df.copy()
    df_copy['current_co'] = df_copy['current_company'].fillna(df_copy['initial_placement'])
    df_copy['moved'] = df_copy.apply(
        lambda r: 1 if str(r['initial_placement']).lower().strip() != str(r['current_co']).lower().strip()
        and str(r['current_co']) not in ['', '0', '0.0', 'nan'] else 0,
        axis=1
    )

    # Company size (hire count as proxy)
    company_counts = df_copy['initial_placement'].value_counts().to_dict()
    df_copy['company_size'] = df_copy['initial_placement'].map(company_counts)

    # Build correlation matrix
    corr_vars = ['graduation_year', 'company_size', 'moved']
    corr_data = df_copy[corr_vars].dropna()

    if len(corr_data) < 10:
        print("  - correlations.png (skipped - insufficient data)")
        return

    corr_matrix = corr_data.corr()

    # Rename for display
    labels = ['Grad Year', 'Company\nSize', 'Changed\nJobs']

    fig, ax = plt.subplots(figsize=(7, 5))
    sns.heatmap(corr_matrix, annot=True, fmt=".2f", cmap="coolwarm", center=0,
                xticklabels=labels, yticklabels=labels,
                linewidths=0.5, linecolor=COLORS["grid"], ax=ax,
                vmin=-1, vmax=1)
    ax.set_title("Correlation Matrix", fontweight="bold", color=COLORS["primary"])

    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "correlations.png", dpi=150, facecolor=COLORS["bg"])
    plt.close()
    print("  - correlations.png")


def chart_left_tech(df: pd.DataFrame) -> None:
    """Chart showing candidates who left tech for non-tech sectors."""
    # Define tech companies
    TECH_COMPANIES = {
        # Big Tech
        'google', 'meta', 'facebook', 'amazon', 'apple', 'microsoft', 'netflix',
        # Tech Unicorns / Marketplaces
        'uber', 'lyft', 'airbnb', 'stripe', 'doordash', 'instacart', 'dropbox',
        'slack', 'zoom', 'spotify', 'pinterest', 'snap', 'snapchat', 'twitter', 'x corp',
        'tiktok', 'bytedance', 'reddit', 'discord', 'nextdoor', 'thumbtack', 'turo',
        # AI/ML
        'openai', 'anthropic', 'deepmind', 'cohere', 'stability ai', 'midjourney',
        'hugging face', 'scale ai', 'databricks', 'perplexity', 'xai', 'groq',
        'codeium', 'cursor', 'anysphere', 'writer', 'elevenlabs', 'harvey',
        'cognition', 'character ai', 'inflection',
        # Fintech
        'robinhood', 'coinbase', 'plaid', 'square', 'block', 'affirm', 'chime',
        'sofi', 'brex', 'ripple', 'kraken', 'toast', 'marqeta', 'klarna', 'revolut',
        # Quant Finance / Trading
        'two sigma', 'jane street', 'citadel', 'de shaw', 'd.e. shaw', 'renaissance',
        'aqr', 'point72', 'bridgewater', 'millennium', 'tower research', 'hrt',
        'jump trading', 'virtu', 'susquehanna', 'sig', 'squarepoint', 'rokos',
        # Enterprise/Cloud/HR
        'salesforce', 'oracle', 'sap', 'vmware', 'snowflake', 'palantir',
        'servicenow', 'workday', 'splunk', 'crowdstrike', 'datadog',
        'deel', 'remote', 'rippling', 'gusto', 'qualtrics', 'amplitude',
        # E-commerce / Logistics
        'shopify', 'ebay', 'wayfair', 'etsy', 'walmart', 'flexport', 'faire',
        # Hardware/Chips
        'nvidia', 'intel', 'amd', 'qualcomm', 'tesla', 'spacex',
        # Real Estate Tech
        'zillow', 'redfin', 'opendoor', 'compass', 'houzz', 'corelogic',
        # Travel Tech
        'booking', 'expedia', 'tripadvisor', 'navan', 'tripactions', 'hopper', 'kayak',
        # Other Tech
        'linkedin', 'indeed', 'glassdoor', 'yelp', 'doximity', 'veeva',
        'twilio', 'okta', 'cloudflare', 'mongodb', 'elastic',
        'asana', 'notion', 'figma', 'canva', 'airtable',
        'grammarly', 'duolingo', 'coursera', 'udemy', 'pandora',
        'roblox', 'epic games', 'unity', 'activision', 'electronic arts', 'adobe',
        'neural sourcing', 'circle', 'barrenjoey',
    }

    # Use module-level NON_TECH_CATEGORIES

    def is_tech(company: str) -> bool:
        if pd.isna(company) or str(company) in ['', '0', 'nan']:
            return False
        c = str(company).lower()
        return any(tech in c for tech in TECH_COMPANIES)

    def is_postdoc(role: str) -> bool:
        if pd.isna(role):
            return False
        return 'postdoc' in str(role).lower()

    def categorize_non_tech(company: str, role: str) -> str:
        if pd.isna(company) and pd.isna(role):
            return None
        combined = f"{str(company)} {str(role)}".lower()
        for cat, keywords in NON_TECH_CATEGORIES.items():
            if any(kw in combined for kw in keywords):
                return cat
        return 'Other Non-Tech'

    # Count total who started in tech (excluding postdocs)
    df_copy = df.copy()
    df_copy['current_co'] = df_copy['current_company'].fillna('')
    df_copy['current_r'] = df_copy['current_role'].fillna('')

    started_in_tech = 0
    left_tech = []
    for _, row in df_copy.iterrows():
        initial_role = str(row.get('initial_role', ''))
        if is_postdoc(initial_role):
            continue
        if is_tech(row['initial_placement']):
            started_in_tech += 1
            current = str(row['current_co']).lower()
            current_role = str(row['current_r'])
            now_not_tech = current and current not in ['', '0', 'nan', '0.0'] and not is_tech(row['current_co'])
            if now_not_tech:
                category = categorize_non_tech(row['current_co'], current_role)
                left_tech.append({
                    'name': row['name'],
                    'school': row['school'],
                    'from': row['initial_placement'],
                    'to': row['current_co'],
                    'role': current_role,
                    'category': category,
                })

    if not left_tech:
        print("  - left_tech.png (skipped - no one left tech)")
        return

    left_df = pd.DataFrame(left_tech)
    pct_left = len(left_df) / started_in_tech * 100 if started_in_tech > 0 else 0

    # Single bar chart with percentages
    fig, ax = plt.subplots(figsize=(10, 6))
    cat_counts = left_df['category'].value_counts()
    cat_pcts = cat_counts / started_in_tech * 100

    bars = ax.barh(cat_pcts.index[::-1], cat_pcts.values[::-1], color=PALETTE[:len(cat_pcts)])
    ax.set_xlabel("% of Tech Starters")
    ax.set_title(f"Where They Went After Leaving Tech\n({len(left_df)}/{started_in_tech} = {pct_left:.1f}% left tech)",
                 fontweight="bold", color=COLORS["primary"])
    ax.bar_label(bars, fmt='%.1f%%', padding=5)

    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "left_tech.png", dpi=150, facecolor=COLORS["bg"])
    plt.close()
    print(f"  - left_tech.png ({len(left_df)}/{started_in_tech} = {pct_left:.1f}% left tech)")


def chart_career_growth(df: pd.DataFrame) -> None:
    """Chart showing seniority level distribution with percentages."""
    # Use module-level get_seniority function for consistency
    df_copy = df.copy()
    df_copy['seniority'] = df_copy.apply(
        lambda r: get_seniority(r['current_role'], r.get('name'), include_entry=True), axis=1)
    # Map to broader categories for this chart
    seniority_mapping = {
        'Head': 'Head/VP/Chief', 'VP': 'Head/VP/Chief', 'Chief': 'Head/VP/Chief', 'Founder': 'Head/VP/Chief',
        'Director': 'Director',
        'Manager': 'Manager/Lead/Principal', 'Lead': 'Manager/Lead/Principal', 'Principal': 'Manager/Lead/Principal',
        'Senior': 'Senior/Staff', 'Staff': 'Senior/Staff',
        'Entry/IC': 'IC/Entry',
    }
    df_copy['seniority'] = df_copy['seniority'].map(seniority_mapping)
    df_copy = df_copy[df_copy['seniority'].notna()]

    if len(df_copy) == 0:
        print("  - career_growth.png (skipped - no role data)")
        return

    total = len(df_copy)
    seniority_order = ['Head/VP/Chief', 'Director', 'Manager/Lead/Principal', 'Senior/Staff', 'IC/Entry']
    seniority_counts = df_copy['seniority'].value_counts()
    seniority_counts = seniority_counts.reindex([s for s in seniority_order if s in seniority_counts.index])
    seniority_pcts = seniority_counts / total * 100

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(seniority_pcts.index[::-1], seniority_pcts.values[::-1], color=PALETTE[:len(seniority_pcts)])
    ax.set_xlabel("% of Candidates")
    ax.set_title(f"Current Seniority Levels\n({total} candidates with role data)",
                 fontweight="bold", color=COLORS["primary"])
    ax.bar_label(bars, fmt='%.1f%%', padding=5)

    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "career_growth.png", dpi=150, facecolor=COLORS["bg"])
    plt.close()
    print(f"  - career_growth.png ({total} candidates)")


# Seniority levels for career progression (shared with analyze.py)
# Note: Director must come before Chief to avoid 'cto' matching 'Director'
SENIORITY_LEVELS = {
    'Director': ['director'],
    'Founder': ['founder', 'co-founder'],
    'Chief': ['chief', 'ceo', ' cto', 'coo'],
    'VP': ['vp ', 'vice president'],
    'Head': ['head of', 'head '],
    'Manager': ['manager'],
    'Principal': ['principal'],
    'Staff': ['staff'],
    'Lead': ['lead'],
    'Senior': ['senior', 'sr.', 'sr '],
}

# Manual overrides for specific people whose titles don't reflect true seniority
SENIORITY_OVERRIDES = {
    'Korkut': 'Entry/IC',           # "Principal Consultant" is consulting title
    'David Mao': 'Entry/IC',        # LinkedIn shows "Applied Scientist", not Senior
    'Meghanath M Y': 'Senior',      # "Head of AI" at tiny startup != Head at big tech
    'Shreya Bhattacharya': 'Senior',  # "Research Director (Asst Prof)" is academic, not tech
}


def get_seniority(role: str, name: str = None, include_entry: bool = True) -> str:
    """Extract seniority level from a role title."""
    # Check manual overrides first
    if name and name in SENIORITY_OVERRIDES:
        return SENIORITY_OVERRIDES[name]

    if pd.isna(role) or str(role) in ['', '0', 'nan']:
        return None
    role_lower = str(role).lower()
    for level, keywords in SENIORITY_LEVELS.items():
        if any(kw in role_lower for kw in keywords):
            return level
    return 'Entry/IC' if include_entry else None


def chart_seniority_pyramid(df: pd.DataFrame) -> None:
    """Horizontal bar chart showing distribution of economists at each seniority level."""
    df_copy = df.copy()
    df_copy['seniority'] = df_copy.apply(
        lambda r: get_seniority(r['current_role'], r.get('name'), include_entry=True), axis=1)
    df_with_role = df_copy[df_copy['seniority'].notna()]

    if len(df_with_role) == 0:
        print("  - seniority_pyramid.png (skipped - no data)")
        return

    level_order = ['Entry/IC', 'Senior', 'Lead', 'Staff', 'Principal', 'Manager', 'Director', 'Head', 'VP', 'Chief', 'Founder']
    counts = df_with_role['seniority'].value_counts()
    total = len(df_with_role)

    # Build data for plotting
    levels = []
    values = []
    percentages = []
    for level in level_order:
        count = counts.get(level, 0)
        levels.append(level)
        values.append(count)
        percentages.append(count / total * 100)

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(levels, values, color=PALETTE[:len(levels)])
    ax.set_xlabel("Number of Economists")
    ax.set_title("Seniority Distribution\n(Economists at each level)",
                 fontweight="bold", color=COLORS["primary"])

    # Add labels with percentage
    for bar, pct in zip(bars, percentages):
        width = bar.get_width()
        ax.text(width + 1, bar.get_y() + bar.get_height()/2,
                f'{int(width)} ({pct:.1f}%)', va='center', fontsize=10, color=COLORS['text'])

    ax.set_xlim(0, max(values) * 1.3)
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "seniority_pyramid.png", dpi=150, facecolor=COLORS["bg"])
    plt.close()
    print(f"  - seniority_pyramid.png ({len(df_with_role)} candidates with roles)")


def chart_time_to_promotion(df: pd.DataFrame) -> None:
    """Bar chart showing average years to reach each seniority level."""
    df_copy = df.copy()
    df_copy['seniority'] = df_copy.apply(
        lambda r: get_seniority(r['current_role'], r.get('name'), include_entry=True), axis=1)
    df_copy = df_copy[df_copy['seniority'].notna()]
    df_copy['years_since_phd'] = datetime.now().year - df_copy['graduation_year']

    if len(df_copy) == 0:
        print("  - time_to_promotion.png (skipped - no data)")
        return

    # Merge categories for cleaner display
    df_copy['seniority'] = df_copy['seniority'].replace({
        'Staff': 'Staff/Principal',
        'Principal': 'Staff/Principal',
        'Lead': 'Senior',
        'Chief': 'Director+',
        'Director': 'Director+',
    })

    # Exclude Founder only (too few, not comparable)
    df_copy = df_copy[~df_copy['seniority'].isin(['Founder'])]

    # Calculate stats for each level
    stats = []
    for level in df_copy['seniority'].unique():
        level_data = df_copy[df_copy['seniority'] == level]['years_since_phd']
        if len(level_data) > 0:
            stats.append({
                'level': level,
                'avg_years': level_data.mean(),
                'count': len(level_data),
            })

    if not stats:
        print("  - time_to_promotion.png (skipped - no senior+ data)")
        return

    # Sort by average years (ascending - fastest to slowest)
    stats_df = pd.DataFrame(stats).sort_values('avg_years', ascending=True)

    fig, ax = plt.subplots(figsize=(12, 7))

    # Create bar chart
    bars = ax.barh(stats_df['level'], stats_df['avg_years'], color=PALETTE[:len(stats_df)])

    ax.set_xlabel("Average Years Since PhD")
    ax.set_title("Years Post-PhD by Seniority Level\n(When economists are typically found at each level)",
                 fontweight="bold", color=COLORS["primary"])

    # Add labels with count
    for i, (_, row) in enumerate(stats_df.iterrows()):
        label = f"{row['avg_years']:.1f} yrs (n={row['count']})"
        ax.text(row['avg_years'] + 0.2, i, label, va='center', fontsize=10, color=COLORS['text'])

    ax.set_xlim(0, stats_df['avg_years'].max() * 1.4)
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "time_to_promotion.png", dpi=150, facecolor=COLORS["bg"])
    plt.close()
    print(f"  - time_to_promotion.png ({len(df_copy)} senior+ candidates)")


def chart_high_achiever_origins(df: pd.DataFrame) -> None:
    """Bar chart showing which firms Director+ people started at."""
    df_copy = df.copy()
    df_copy['seniority'] = df_copy.apply(
        lambda r: get_seniority(r['current_role'], r.get('name'), include_entry=False), axis=1)

    # Filter to Director and above
    high_levels = {'Director', 'Head', 'VP', 'Chief', 'Founder'}
    achievers = df_copy[df_copy['seniority'].isin(high_levels)]

    if len(achievers) == 0:
        print("  - high_achiever_origins.png (skipped - no Director+ data)")
        return

    # Count initial placements
    origins = achievers['initial_placement'].value_counts().head(10)

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(origins.index[::-1], origins.values[::-1], color=PALETTE[0])
    ax.set_xlabel("Number of Director+ Economists")
    ax.set_title("Where Did Director+ Economists Start?\n(Initial placement of highest achievers)",
                 fontweight="bold", color=COLORS["primary"])

    # Add value labels
    for bar in bars:
        width = bar.get_width()
        ax.text(width + 0.1, bar.get_y() + bar.get_height()/2,
                f'{int(width)}', va='center', fontsize=10, color=COLORS['text'])

    ax.set_xlim(0, max(origins.values) * 1.2)
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "high_achiever_origins.png", dpi=150, facecolor=COLORS["bg"])
    plt.close()
    print(f"  - high_achiever_origins.png ({len(achievers)} Director+ candidates)")


def chart_high_achiever_schools(df: pd.DataFrame) -> None:
    """Bar chart showing which schools Director+ people came from."""
    df_copy = df.copy()
    df_copy['seniority'] = df_copy.apply(
        lambda r: get_seniority(r['current_role'], r.get('name'), include_entry=False), axis=1)

    # Filter to Director and above
    high_levels = {'Director', 'Head', 'VP', 'Chief', 'Founder'}
    achievers = df_copy[df_copy['seniority'].isin(high_levels)]

    if len(achievers) == 0:
        print("  - high_achiever_schools.png (skipped - no Director+ data)")
        return

    # Count schools
    schools = achievers['school'].value_counts().head(10)

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(schools.index[::-1], schools.values[::-1], color=PALETTE[1])
    ax.set_xlabel("Number of Director+ Economists")
    ax.set_title("Where Did Director+ Economists Study?\n(PhD schools of highest achievers)",
                 fontweight="bold", color=COLORS["primary"])

    # Add value labels
    for bar in bars:
        width = bar.get_width()
        ax.text(width + 0.1, bar.get_y() + bar.get_height()/2,
                f'{int(width)}', va='center', fontsize=10, color=COLORS['text'])

    ax.set_xlim(0, max(schools.values) * 1.2)
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "high_achiever_schools.png", dpi=150, facecolor=COLORS["bg"])
    plt.close()
    print(f"  - high_achiever_schools.png ({len(achievers)} Director+ candidates)")


def chart_data_coverage(df: pd.DataFrame) -> None:
    """Heatmap showing data coverage by school and year."""
    # Create pivot table
    coverage = df.groupby(['school', 'graduation_year']).size().unstack(fill_value=0)

    # Sort schools by total
    school_totals = coverage.sum(axis=1).sort_values(ascending=False)
    coverage = coverage.loc[school_totals.index]

    fig, ax = plt.subplots(figsize=(14, 10))

    # Create heatmap
    im = ax.imshow(coverage.values, cmap='YlGnBu', aspect='auto')

    # Set ticks
    ax.set_xticks(range(len(coverage.columns)))
    ax.set_xticklabels(coverage.columns.astype(int), rotation=45)
    ax.set_yticks(range(len(coverage.index)))
    ax.set_yticklabels(coverage.index)

    # Add text annotations
    for i in range(len(coverage.index)):
        for j in range(len(coverage.columns)):
            val = coverage.iloc[i, j]
            if val > 0:
                color = 'white' if val > 5 else 'black'
                ax.text(j, i, int(val), ha='center', va='center', color=color, fontsize=9)

    ax.set_xlabel("Graduation Year")
    ax.set_ylabel("School")
    ax.set_title("Data Coverage: PhD Placements by School and Year",
                 fontweight="bold", color=COLORS["primary"])

    # Add colorbar
    cbar = plt.colorbar(im, ax=ax, shrink=0.6)
    cbar.set_label('Number of Candidates')

    # Add totals on right
    for i, total in enumerate(school_totals):
        ax.text(len(coverage.columns) + 0.3, i, f'({int(total)})',
                va='center', fontsize=9, color=COLORS['text'])

    plt.tight_layout()
    plt.savefig(CHARTS_DIR / 'data_coverage.png', dpi=150, facecolor=COLORS["bg"])
    plt.close()
    print(f"  - data_coverage.png ({len(coverage.index)} schools, {len(coverage.columns)} years)")


def chart_hiring_timeseries(df: pd.DataFrame) -> None:
    """Time series of hiring patterns by top firms."""
    # Get top firms
    top_firms = df['initial_placement'].value_counts().head(6).index.tolist()

    fig, ax = plt.subplots(figsize=(14, 7))

    for i, firm in enumerate(top_firms):
        firm_df = df[df['initial_placement'] == firm]
        yearly = firm_df.groupby('graduation_year').size()
        ax.plot(yearly.index, yearly.values, marker='o', linewidth=2,
                label=f"{firm} ({len(firm_df)} total)", color=PALETTE[i % len(PALETTE)])

    ax.set_xlabel("Year")
    ax.set_ylabel("Number of PhD Hires")
    ax.set_title("Econ PhD Hiring by Top Tech Firms Over Time",
                 fontweight="bold", color=COLORS["primary"])
    ax.legend(loc='upper left')
    ax.set_xticks(range(2014, datetime.now().year + 1))
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(CHARTS_DIR / 'hiring_timeseries.png', dpi=150, facecolor=COLORS["bg"])
    plt.close()
    print(f"  - hiring_timeseries.png ({len(top_firms)} firms)")


def chart_work_wordcloud(df: pd.DataFrame) -> None:
    """Wordclouds showing how economists describe their work, by seniority level."""
    df_copy = df.copy()
    df_copy['seniority'] = df_copy.apply(
        lambda r: get_seniority(r['current_role'], r.get('name'), include_entry=True), axis=1)

    # Merge categories
    df_copy['seniority'] = df_copy['seniority'].replace({
        'Staff': 'Staff/Principal',
        'Principal': 'Staff/Principal',
        'Lead': 'Senior',
        'Chief': 'Director+',
        'Director': 'Director+',
    })

    # Levels to show (ordered)
    levels = ['Entry/IC', 'Senior', 'Staff/Principal', 'Manager', 'Director+']

    # Create subplot grid
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    axes = axes.flatten()

    count = 0
    for i, level in enumerate(levels):
        level_df = df_copy[df_copy['seniority'] == level]
        work_text = level_df['work_focus'].dropna().astype(str)

        if len(work_text) < 3:
            axes[i].axis('off')
            axes[i].set_title(f"{level}\n(insufficient data)", color=COLORS['text'])
            continue

        text = ' '.join(work_text)

        wc = WordCloud(
            width=400, height=300,
            background_color=COLORS['bg'],
            colormap='viridis',
            max_words=30,
            collocations=True,
        ).generate(text)

        axes[i].imshow(np.array(wc.to_image()), interpolation='bilinear')
        axes[i].axis('off')
        axes[i].set_title(f"{level} (n={len(work_text)})",
                          fontweight="bold", color=COLORS["primary"], fontsize=12)
        count += len(work_text)

    # Hide last subplot (we have 5 levels, 6 subplots)
    axes[5].axis('off')

    fig.suptitle("What Econ PhDs Work On by Seniority Level",
                 fontweight="bold", color=COLORS["primary"], fontsize=16)
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / 'work_wordcloud.png', dpi=150, facecolor=COLORS["bg"])
    plt.close()
    print(f"  - work_wordcloud.png ({count} descriptions across {len(levels)} levels)")


def main():
    """Generate all charts."""
    CHARTS_DIR.mkdir(exist_ok=True)
    setup_dark_theme()

    print("Loading data...")
    df = load_data()
    print(f"  {len(df)} candidates loaded\n")

    print("Generating basic charts:")
    chart_placements_by_school(df)
    chart_top_companies(df)
    chart_heatmap(df)
    chart_timeline(df)
    chart_roles(df)

    print("\nGenerating enriched data charts:")
    chart_research_to_company(df)
    chart_field_to_firm(df)
    chart_teams(df)
    chart_work_domains(df)
    chart_work_methods(df)
    chart_work_ngrams(df)
    chart_company_roles(df)
    chart_movers(df)
    chart_school_to_role(df)
    chart_selectivity(df)

    print("\nGenerating new analytics charts:")
    chart_network_graph(df)
    chart_career_progression(df)
    chart_correlations(df)

    print("\nGenerating career trajectory charts:")
    chart_left_tech(df)
    chart_career_growth(df)
    chart_time_to_promotion(df)
    chart_seniority_pyramid(df)
    chart_high_achiever_origins(df)
    chart_high_achiever_schools(df)
    chart_data_coverage(df)
    chart_hiring_timeseries(df)
    chart_work_wordcloud(df)

    print(f"\nDone! Charts saved to {CHARTS_DIR}/")


if __name__ == "__main__":
    main()
