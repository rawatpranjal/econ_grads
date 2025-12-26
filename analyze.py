#!/usr/bin/env python3
"""Data analysis for Economics PhD tech placements."""

import pandas as pd
import numpy as np
from pathlib import Path
from collections import Counter
from scipy import stats
from normalize import normalize_company, standardize_current_placement

DATA_PATH = Path(__file__).parent / "data" / "candidates.csv"
ENRICHED_PATH = Path(__file__).parent / "data" / "candidates_enriched.csv"

# Seniority levels for career progression analysis (ordered from highest to lowest)
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


def get_seniority(role: str, name: str = None) -> str:
    """Extract seniority level from a role title.

    Args:
        role: Job title string
        name: Person's name (optional, for manual overrides)

    Returns one of the seniority levels or None if role is empty.
    """
    # Check manual overrides first
    if name and name in SENIORITY_OVERRIDES:
        return SENIORITY_OVERRIDES[name]

    if pd.isna(role) or str(role) in ['', '0', 'nan']:
        return None
    role_lower = str(role).lower()
    for level, keywords in SENIORITY_LEVELS.items():
        if any(kw in role_lower for kw in keywords):
            return level
    return 'Entry/IC'


def load_data() -> pd.DataFrame:
    """Load the candidates dataset with normalized company names."""
    df = pd.read_csv(DATA_PATH)

    # Filter to 2014 and later only
    if 'graduation_year' in df.columns:
        df = df[df['graduation_year'] >= 2014]

    # Normalize company names (Facebook→Meta, Twitter→X, etc.)
    if 'initial_placement' in df.columns:
        df['initial_placement'] = df['initial_placement'].apply(normalize_company)
    if 'current_company' in df.columns:
        df['current_company'] = df['current_company'].apply(standardize_current_placement)
    if 'current_placement' in df.columns:
        df['current_placement'] = df['current_placement'].apply(standardize_current_placement)

    return df


def placements_by_school(df: pd.DataFrame) -> pd.Series:
    """Count placements by PhD-granting institution."""
    return df["school"].value_counts()


def placements_by_company(df: pd.DataFrame) -> pd.Series:
    """Count placements by initial company."""
    return df["initial_placement"].value_counts()


def placements_by_year(df: pd.DataFrame) -> pd.Series:
    """Count placements by graduation year."""
    return df["graduation_year"].value_counts().sort_index()


def career_transitions(df: pd.DataFrame) -> pd.DataFrame:
    """Get initial -> current company transitions."""
    transitions = df[
        (df["current_placement"].notna()) &
        (df["current_placement"] != "") &
        (df["initial_placement"] != df["current_placement"])
    ][["name", "school", "initial_placement", "current_placement"]].copy()
    return transitions


def school_company_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Create cross-tabulation of school vs company."""
    return pd.crosstab(df["school"], df["initial_placement"])


def role_distribution(df: pd.DataFrame) -> pd.Series:
    """Categorize roles into types."""
    roles = df["current_role"].dropna()
    roles = roles[roles != ""]

    categories = {
        "Economist": ["economist", "principal economist", "senior economist"],
        "Data Scientist": ["data scientist", "senior data scientist"],
        "Applied Scientist": ["applied scientist", "senior applied scientist"],
        "Quantitative Researcher": ["quant", "quantitative"],
        "Professor/Academic": ["professor", "prof", "assistant prof", "postdoc"],
        "Manager/Director": ["manager", "director", "lead"],
        "ML Engineer": ["ml engineer", "machine learning"],
        "Other": []
    }

    def categorize(role: str) -> str:
        role_lower = role.lower()
        for cat, keywords in categories.items():
            if cat == "Other":
                continue
            for kw in keywords:
                if kw in role_lower:
                    return cat
        return "Other"

    return roles.apply(categorize).value_counts()


def top_feeders_per_company(df: pd.DataFrame, top_n: int = 3) -> dict:
    """For each company, find top feeder schools."""
    result = {}
    for company in df["initial_placement"].unique():
        schools = df[df["initial_placement"] == company]["school"].value_counts()
        result[company] = schools.head(top_n).to_dict()
    return result


def school_placements_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Analyze school placements (counts only, no quality ranking).

    Returns DataFrame with:
    - school: School name
    - total_placements: Total number of placements
    - top_companies: Most common destinations
    """
    results = []
    for school in df['school'].unique():
        school_df = df[df['school'] == school]

        # Top companies for this school
        top_companies = school_df['initial_placement'].value_counts().head(3).index.tolist()

        results.append({
            'school': school,
            'total_placements': len(school_df),
            'top_companies': ', '.join(top_companies),
        })

    result_df = pd.DataFrame(results)
    result_df = result_df.sort_values('total_placements', ascending=False)
    return result_df


def career_progression_analysis(df: pd.DataFrame) -> dict:
    """Analyze career progression: retention and job changes.

    Returns dict with:
    - retention_by_company: {company: retention_rate}
    - popular_transitions: [(from, to, count), ...]
    """
    # Identify job changers
    df_copy = df.copy()
    if 'current_company' not in df_copy.columns:
        df_copy['current_company'] = df_copy['initial_placement']

    df_copy['current_co'] = df_copy['current_company'].fillna(df_copy['initial_placement'])
    df_copy['moved'] = df_copy.apply(
        lambda r: str(r['initial_placement']).lower().strip() != str(r['current_co']).lower().strip()
        if pd.notna(r['current_co']) and str(r['current_co']) not in ['', '0', '0.0', 'nan']
        else False,
        axis=1
    )

    # Retention by company (top 10 companies by hire count)
    top_companies = df_copy['initial_placement'].value_counts().head(10).index
    retention = {}
    for company in top_companies:
        company_df = df_copy[df_copy['initial_placement'] == company]
        retained = (~company_df['moved']).sum()
        retention[company] = round(retained / len(company_df) * 100, 1) if len(company_df) > 0 else 0

    # Job changers
    movers = df_copy[df_copy['moved']]

    # Popular transitions
    transitions = movers.apply(lambda r: (r['initial_placement'], r['current_co']), axis=1)
    trans_counts = transitions.value_counts().head(15)
    popular = [(t[0], t[1], c) for t, c in trans_counts.items()]

    return {
        'retention_by_company': retention,
        'total_movers': len(movers),
        'total_stayers': len(df_copy) - len(movers),
        'popular_transitions': popular
    }


def seniority_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Analyze distribution of economists across seniority levels.

    Returns DataFrame with:
    - level: Seniority level name
    - count: Number of economists at that level
    - percentage: Percentage of total
    """
    df_copy = df.copy()
    df_copy['seniority'] = df_copy.apply(
        lambda r: get_seniority(r['current_role'], r.get('name')), axis=1)

    # Filter to those with known roles
    df_with_role = df_copy[df_copy['seniority'].notna()]

    if len(df_with_role) == 0:
        return pd.DataFrame()

    # Count by level
    level_order = ['Entry/IC', 'Senior', 'Lead', 'Staff', 'Principal', 'Manager', 'Director', 'Head', 'VP', 'Chief', 'Founder']
    counts = df_with_role['seniority'].value_counts()

    results = []
    total = len(df_with_role)
    for level in level_order:
        count = counts.get(level, 0)
        pct = count / total * 100 if total > 0 else 0
        results.append({
            'level': level,
            'count': count,
            'percentage': round(pct, 1)
        })

    return pd.DataFrame(results)


def promotion_timeline_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Analyze years since PhD for each seniority level.

    Returns DataFrame with:
    - level: Seniority level
    - mean: Average years since PhD
    - median: Median years since PhD
    - min: Minimum years
    - max: Maximum years
    - n: Count at that level
    """
    df_copy = df.copy()
    df_copy['seniority'] = df_copy.apply(
        lambda r: get_seniority(r['current_role'], r.get('name')), axis=1)
    df_copy['years_since_phd'] = 2025 - df_copy['graduation_year']

    # Filter to those with seniority above Entry/IC
    df_senior = df_copy[
        (df_copy['seniority'].notna()) &
        (df_copy['seniority'] != 'Entry/IC')
    ]

    if len(df_senior) == 0:
        return pd.DataFrame()

    level_order = ['Senior', 'Lead', 'Staff', 'Principal', 'Manager', 'Director', 'Head', 'VP', 'Chief', 'Founder']
    results = []

    for level in level_order:
        level_data = df_senior[df_senior['seniority'] == level]['years_since_phd']
        if len(level_data) > 0:
            results.append({
                'level': level,
                'mean': round(level_data.mean(), 1),
                'median': round(level_data.median(), 1),
                'min': int(level_data.min()),
                'max': int(level_data.max()),
                'n': len(level_data)
            })

    return pd.DataFrame(results)


def high_achievers_analysis(df: pd.DataFrame) -> dict:
    """Analyze economists who reached Director level or higher.

    Returns dict with:
    - achievers: DataFrame of high achievers with details
    - starting_firms: Counter of initial placements
    - schools: Counter of PhD schools
    - research_fields: Counter of research fields
    - avg_years_to_director: Average years since PhD for Director+ roles
    """
    df_copy = df.copy()
    df_copy['seniority'] = df_copy.apply(
        lambda r: get_seniority(r['current_role'], r.get('name')), axis=1)
    df_copy['years_since_phd'] = 2025 - df_copy['graduation_year']

    # Filter to Director and above
    high_levels = {'Director', 'Head', 'VP', 'Chief', 'Founder'}
    achievers = df_copy[df_copy['seniority'].isin(high_levels)].copy()

    if len(achievers) == 0:
        return {
            'achievers': pd.DataFrame(),
            'starting_firms': Counter(),
            'schools': Counter(),
            'research_fields': Counter(),
            'avg_years_to_director': 0
        }

    # Select relevant columns
    cols = ['name', 'current_role', 'seniority', 'initial_placement', 'school',
            'research_fields', 'graduation_year', 'years_since_phd']
    if 'current_company' in df_copy.columns:
        cols.insert(2, 'current_company')
    achievers_df = achievers[cols].sort_values('years_since_phd')

    # Count starting firms
    starting_firms = Counter(achievers['initial_placement'])

    # Count schools
    schools = Counter(achievers['school'])

    # Count research fields (split comma-separated)
    fields = []
    for f in achievers['research_fields'].dropna():
        fields.extend([x.strip() for x in str(f).split(',') if x.strip() and x.strip() != 'nan'])
    research_fields = Counter(fields)

    # Average years to reach Director+
    avg_years = achievers['years_since_phd'].mean()

    return {
        'achievers': achievers_df,
        'starting_firms': starting_firms,
        'schools': schools,
        'research_fields': research_fields,
        'avg_years_to_director': round(avg_years, 1)
    }


def statistical_analysis(df: pd.DataFrame) -> dict:
    """Run statistical tests on the data.

    Returns dict with chi-square results (no quality rankings).
    """
    results = {}

    # Chi-square: School independence from Company
    contingency = pd.crosstab(df['school'], df['initial_placement'])
    # Filter to cells with enough data
    contingency = contingency.loc[:, contingency.sum() >= 3]
    if contingency.shape[1] >= 2:
        chi2, pval, dof, expected = stats.chi2_contingency(contingency)
        results['school_company_independence'] = {
            'chi2': round(chi2, 2),
            'p_value': round(pval, 4),
            'degrees_of_freedom': dof,
            'independent': pval > 0.05,
            'interpretation': 'School and company are related' if pval < 0.05 else 'No significant relationship'
        }

    return results


def print_quirky_facts(df: pd.DataFrame) -> None:
    """Print quirky and interesting facts from the data."""
    print("\n" + "=" * 60)
    print("QUIRKY FACTS")
    print("=" * 60)

    total = len(df)

    # 1. The Uber PhD phenomenon
    uber_count = len(df[df['initial_placement'] == 'Uber'])
    uber_pct = uber_count / total * 100
    print(f"\n📊 THE UBER PHENOMENON: {uber_count} PhDs ({uber_pct:.1f}% of all placements) went to Uber")

    # 2. The Amazon army
    amazon_count = len(df[df['initial_placement'] == 'Amazon'])
    amazon_pct = amazon_count / total * 100
    print(f"📊 THE AMAZON ARMY: {amazon_count} PhDs ({amazon_pct:.1f}%) - nearly 1 in 2!")

    # 3. Harvard exclusives - companies that only hire from Harvard
    school_company = pd.crosstab(df['school'], df['initial_placement'])
    harvard_only = []
    for company in school_company.columns:
        if school_company[company].sum() >= 1:
            if 'Harvard' in school_company.index and school_company.loc['Harvard', company] == school_company[company].sum():
                harvard_only.append(company)
    if harvard_only:
        print(f"🎓 HARVARD EXCLUSIVES: {', '.join(harvard_only[:5])} only hire Harvard PhDs")

    # 4. Loneliest companies (hired exactly 1 person)
    company_counts = df['initial_placement'].value_counts()
    loners = company_counts[company_counts == 1].index.tolist()
    if loners:
        print(f"🏝️  LONELY COMPANIES: {len(loners)} companies hired exactly 1 PhD each")
        print(f"    Examples: {', '.join(loners[:5])}")

    # 5. Most common research field per top company
    if 'research_fields' in df.columns:
        top_companies = company_counts.head(5).index
        print("\n📚 FAVORITE RESEARCH FIELDS BY COMPANY:")
        for company in top_companies:
            company_df = df[df['initial_placement'] == company]
            fields = []
            for f in company_df['research_fields'].dropna():
                fields.extend([x.strip() for x in str(f).split(',') if x.strip() and x.strip() != 'nan'])
            if fields:
                top_field = Counter(fields).most_common(1)[0][0]
                print(f"    {company}: {top_field}")

    # 6. The FAANG+ ratio
    faang = {'Google', 'Meta', 'Amazon', 'Apple', 'Microsoft', 'Netflix'}
    faang_count = len(df[df['initial_placement'].isin(faang)])
    faang_pct = faang_count / total * 100
    print(f"\n💼 FAANG+ DOMINANCE: {faang_count} PhDs ({faang_pct:.1f}%) went to Big Tech")

    print("\n" + "=" * 60)


def print_summary(df: pd.DataFrame) -> None:
    """Print a summary of the dataset."""
    print("=" * 60)
    print("ECON PHD TECH PLACEMENTS - SUMMARY")
    print("=" * 60)

    print(f"\nTotal candidates: {len(df)}")
    print(f"Schools represented: {df['school'].nunique()}")
    print(f"Companies represented: {df['initial_placement'].nunique()}")
    print(f"Year range: {df['graduation_year'].min()} - {df['graduation_year'].max()}")

    print("\n" + "-" * 40)
    print("PLACEMENTS BY SCHOOL")
    print("-" * 40)
    for school, count in placements_by_school(df).items():
        print(f"  {school}: {count}")

    print("\n" + "-" * 40)
    print("TOP HIRING COMPANIES")
    print("-" * 40)
    for company, count in placements_by_company(df).head(10).items():
        print(f"  {company}: {count}")

    print("\n" + "-" * 40)
    print("PLACEMENTS BY YEAR")
    print("-" * 40)
    for year, count in placements_by_year(df).items():
        print(f"  {year}: {count}")

    print("\n" + "-" * 40)
    print("ROLE DISTRIBUTION (Current)")
    print("-" * 40)
    for role, count in role_distribution(df).items():
        print(f"  {role}: {count}")

    transitions = career_transitions(df)
    if len(transitions) > 0:
        print("\n" + "-" * 40)
        print(f"CAREER TRANSITIONS ({len(transitions)} candidates)")
        print("-" * 40)
        for _, row in transitions.iterrows():
            print(f"  {row['name']}: {row['initial_placement']} -> {row['current_placement']}")

    print("\n" + "=" * 60)


def print_extended_analysis(df: pd.DataFrame) -> None:
    """Print extended analysis including new metrics."""

    # Seniority distribution
    print("\n" + "-" * 40)
    print("SENIORITY DISTRIBUTION")
    print("-" * 40)
    seniority = seniority_distribution(df)
    if not seniority.empty:
        for _, row in seniority.iterrows():
            print(f"  {row['level']}: {row['count']} ({row['percentage']:.1f}%)")

    # Promotion timeline
    print("\n" + "-" * 40)
    print("PROMOTION TIMELINE (years since PhD)")
    print("-" * 40)
    timeline = promotion_timeline_analysis(df)
    if not timeline.empty:
        print(f"  {'Level':<25} {'Mean':>6} {'Median':>7} {'Min':>5} {'Max':>5} {'n':>5}")
        print("  " + "-" * 54)
        for _, row in timeline.iterrows():
            print(f"  {row['level']:<25} {row['mean']:>6.1f} {row['median']:>7.1f} "
                  f"{row['min']:>5} {row['max']:>5} {row['n']:>5}")

    # High achievers
    print("\n" + "-" * 40)
    print("HIGH ACHIEVERS (Director+)")
    print("-" * 40)
    achievers = high_achievers_analysis(df)
    if achievers['achievers'] is not None and len(achievers['achievers']) > 0:
        print(f"\n  Total Director+ roles: {len(achievers['achievers'])}")
        print(f"  Avg years since PhD: {achievers['avg_years_to_director']}")

        print("\n  Top starting firms:")
        for firm, count in achievers['starting_firms'].most_common(5):
            print(f"    {firm}: {count}")

        print("\n  Top schools:")
        for school, count in achievers['schools'].most_common(5):
            print(f"    {school}: {count}")

        print("\n  Common research fields:")
        for field, count in achievers['research_fields'].most_common(5):
            print(f"    {field}: {count}")

        print("\n  Individual achievers:")
        for _, row in achievers['achievers'].iterrows():
            current_co = row.get('current_company', row['initial_placement'])
            print(f"    {row['name']} - {row['current_role']}")
            print(f"      Started: {row['initial_placement']} | School: {row['school']} | "
                  f"Years: {row['years_since_phd']}")
    else:
        print("  No Director+ roles found in data")

    # School placements (counts only, no quality ranking)
    print("\n" + "-" * 40)
    print("SCHOOL PLACEMENTS")
    print("-" * 40)
    placements = school_placements_analysis(df)
    if not placements.empty:
        for _, row in placements.iterrows():
            print(f"  {row['school']}: {row['total_placements']} placements -> {row['top_companies']}")

    # Career progression
    print("\n" + "-" * 40)
    print("CAREER PROGRESSION")
    print("-" * 40)
    progression = career_progression_analysis(df)
    print(f"  Job changers: {progression['total_movers']} | Stayed: {progression['total_stayers']}")
    print("\n  Retention by company (top 10):")
    for company, rate in progression['retention_by_company'].items():
        print(f"    {company}: {rate:.0f}%")

    # Statistical analysis
    print("\n" + "-" * 40)
    print("STATISTICAL ANALYSIS")
    print("-" * 40)
    stats_results = statistical_analysis(df)
    for test_name, result in stats_results.items():
        print(f"\n  {test_name}:")
        for k, v in result.items():
            print(f"    {k}: {v}")


if __name__ == "__main__":
    # Try enriched data first, fall back to basic
    if ENRICHED_PATH.exists():
        df = pd.read_csv(ENRICHED_PATH)
        # Filter to 2014 and later only
        if 'graduation_year' in df.columns:
            df = df[df['graduation_year'] >= 2014]
        print(f"Loaded enriched data: {len(df)} candidates (2014+)")
    else:
        df = load_data()
        print(f"Loaded basic data: {len(df)} candidates (2014+)")

    print_summary(df)
    print_extended_analysis(df)
    print_quirky_facts(df)
