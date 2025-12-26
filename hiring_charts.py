#!/usr/bin/env python3
"""
Visualization charts for company hiring patterns.
Generates static (PNG) and interactive (HTML) charts.

Note: Quality rankings removed due to small sample sizes.
"""
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from pathlib import Path


def create_hiring_trends(candidates_df: pd.DataFrame, output_dir: str = 'charts'):
    """Line chart showing hiring trends over time by top companies."""
    if 'graduation_year' not in candidates_df.columns:
        print("  Skipping hiring trends: no graduation_year column")
        return

    # Get top 10 companies by hire count
    top_companies = candidates_df['initial_placement'].value_counts().head(10).index.tolist()

    # Filter to top companies and valid years
    df = candidates_df[candidates_df['initial_placement'].isin(top_companies)].copy()
    df['graduation_year'] = pd.to_numeric(df['graduation_year'], errors='coerce')
    df = df[df['graduation_year'].between(2014, 2024)]

    # Count hires per year per company
    trend_data = df.groupby(['graduation_year', 'initial_placement']).size().unstack(fill_value=0)

    fig, ax = plt.subplots(figsize=(14, 8))
    trend_data.plot(ax=ax, marker='o', linewidth=2)

    ax.set_xlabel('Graduation Year', fontsize=12)
    ax.set_ylabel('Number of PhD Hires', fontsize=12)
    ax.set_title('PhD Hiring Trends by Company (2014-2024)', fontsize=14, fontweight='bold')
    ax.legend(title='Company', bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.set_xticks(range(2014, 2025))
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(f'{output_dir}/hiring_trends.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Created: {output_dir}/hiring_trends.png")


def create_school_company_sankey(candidates_df: pd.DataFrame, output_dir: str = 'charts'):
    """Sankey diagram showing flow from schools to companies."""
    # Get top 10 schools and companies
    top_schools = candidates_df['school'].value_counts().head(10).index.tolist()
    top_companies = candidates_df['initial_placement'].value_counts().head(15).index.tolist()

    df = candidates_df[
        (candidates_df['school'].isin(top_schools)) &
        (candidates_df['initial_placement'].isin(top_companies))
    ]

    # Create flow counts
    flows = df.groupby(['school', 'initial_placement']).size().reset_index(name='count')
    flows = flows[flows['count'] >= 1]

    if len(flows) < 3:
        print("  Skipping Sankey: insufficient data")
        return

    # Create node lists
    schools = flows['school'].unique().tolist()
    companies = flows['initial_placement'].unique().tolist()
    all_nodes = schools + companies

    # Create link indices
    source_idx = [schools.index(s) for s in flows['school']]
    target_idx = [len(schools) + companies.index(c) for c in flows['initial_placement']]

    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color='black', width=0.5),
            label=all_nodes,
            color=['#1f77b4'] * len(schools) + ['#2ca02c'] * len(companies)
        ),
        link=dict(
            source=source_idx,
            target=target_idx,
            value=flows['count'].tolist(),
            color='rgba(100,100,100,0.3)'
        )
    )])

    fig.update_layout(
        title='Economics PhD Flow: Schools to Tech Companies',
        font_size=12
    )

    fig.write_html(f'{output_dir}/school_company_flow.html')
    print(f"  Created: {output_dir}/school_company_flow.html")


def create_field_distribution(candidates_df: pd.DataFrame, output_dir: str = 'charts'):
    """Stacked bar chart showing research field mix by company."""
    if 'research_fields' not in candidates_df.columns:
        print("  Skipping field distribution: no research_fields column")
        return

    # Get top companies
    top_companies = candidates_df['initial_placement'].value_counts().head(10).index.tolist()
    df = candidates_df[candidates_df['initial_placement'].isin(top_companies)].copy()

    # Parse research fields
    field_data = []
    for _, row in df.iterrows():
        if pd.notna(row['research_fields']):
            fields = [f.strip() for f in str(row['research_fields']).split(',')]
            for field in fields:
                if field:
                    field_data.append({
                        'company': row['initial_placement'],
                        'field': field[:20]
                    })

    if not field_data:
        print("  Skipping field distribution: no field data")
        return

    field_df = pd.DataFrame(field_data)

    # Get top fields
    top_fields = field_df['field'].value_counts().head(8).index.tolist()
    field_df = field_df[field_df['field'].isin(top_fields)]

    # Pivot for stacked bar
    pivot = field_df.groupby(['company', 'field']).size().unstack(fill_value=0)

    fig, ax = plt.subplots(figsize=(14, 8))
    pivot.plot(kind='bar', stacked=True, ax=ax, colormap='tab10')

    ax.set_xlabel('Company', fontsize=12)
    ax.set_ylabel('Number of PhDs', fontsize=12)
    ax.set_title('Research Field Distribution by Company', fontsize=14, fontweight='bold')
    ax.legend(title='Research Field', bbox_to_anchor=(1.05, 1), loc='upper left')

    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(f'{output_dir}/field_distribution.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Created: {output_dir}/field_distribution.png")


def create_all_charts(candidates_df: pd.DataFrame, output_dir: str = 'charts'):
    """Generate all hiring pattern charts (no quality rankings)."""
    Path(output_dir).mkdir(exist_ok=True)
    print(f"\nGenerating charts in {output_dir}/...")

    create_hiring_trends(candidates_df, output_dir)
    create_school_company_sankey(candidates_df, output_dir)
    create_field_distribution(candidates_df, output_dir)

    print(f"\nDone! Charts saved to {output_dir}/")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Generate hiring pattern charts')
    parser.add_argument('--candidates', default='data/candidates_enriched.csv', help='Candidates CSV')
    parser.add_argument('--output', default='charts', help='Output directory')
    args = parser.parse_args()

    candidates_path = Path(args.candidates)
    if not candidates_path.exists():
        candidates_path = Path('data/candidates.csv')

    if not candidates_path.exists():
        print(f"Error: No candidates file found")
        return

    print(f"Loading {candidates_path}...")
    candidates_df = pd.read_csv(candidates_path)
    print(f"Found {len(candidates_df)} candidates")

    create_all_charts(candidates_df, args.output)


if __name__ == "__main__":
    main()
