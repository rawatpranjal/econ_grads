#!/usr/bin/env python3
"""
Career network graph analysis for economics PhD placements.

Builds a directed graph of career transitions and calculates:
- PageRank: "Ultimate destination" popularity
- In-degree: Destination hub (people move TO)
- Out-degree: Talent source (people leave FROM)
- Betweenness: Stepping stone / career accelerator
"""

import pandas as pd
import networkx as nx
from collections import defaultdict
from datetime import datetime
from normalize import normalize_company

# Seniority levels for career growth tracking
SENIORITY_LEVELS = {
    'intern': 0,
    'analyst': 1,
    'associate': 2,
    'economist': 3,
    'data scientist': 3,
    'applied scientist': 3,
    'research scientist': 3,
    'senior': 4,
    'lead': 5,
    'principal': 6,
    'staff': 6,
    'director': 7,
    'head': 8,
    'vp': 9,
    'chief': 10,
}


def get_seniority(role: str) -> int:
    """Get seniority level from role title."""
    if not role or pd.isna(role):
        return 3  # Default to mid-level

    role_lower = str(role).lower()

    for keyword, level in sorted(SENIORITY_LEVELS.items(), key=lambda x: -x[1]):
        if keyword in role_lower:
            return level

    return 3  # Default


def build_career_graph(df: pd.DataFrame) -> nx.DiGraph:
    """
    Build a directed graph of career transitions.

    Nodes = Companies
    Edges = Career transitions (weight = number of people)
    """
    G = nx.DiGraph()

    # Add all companies as nodes
    for company in df['initial_placement'].dropna().unique():
        G.add_node(company, type='initial')

    # Track transitions
    transitions = defaultdict(int)

    for _, row in df.iterrows():
        initial = row.get('initial_placement', '')
        current = row.get('current_company', '')

        if pd.isna(initial) or pd.isna(current):
            continue
        if not initial or not current:
            continue

        # Normalize
        initial_norm = normalize_company(str(initial))
        current_norm = normalize_company(str(current))

        # Skip if same company (compare full normalized names)
        if initial_norm.lower() == current_norm.lower():
            continue

        # Skip academia
        if 'academia' in current_norm.lower():
            current_norm = 'Academia'

        # Add current as node if not exists
        if current_norm not in G:
            G.add_node(current_norm, type='current')

        # Count transition
        transitions[(initial_norm, current_norm)] += 1

    # Add edges with weights
    for (source, target), weight in transitions.items():
        G.add_edge(source, target, weight=weight)

    return G


def calculate_centrality(G: nx.DiGraph) -> dict:
    """
    Calculate various centrality measures for the career graph.

    Returns dict of company -> centrality scores
    """
    if len(G.nodes()) == 0:
        return {}

    # Calculate centralities
    try:
        pagerank = nx.pagerank(G, weight='weight')
    except Exception as e:
        print(f"Warning: PageRank calculation failed: {e}")
        pagerank = {n: 0 for n in G.nodes()}

    in_degree = dict(G.in_degree(weight='weight'))
    out_degree = dict(G.out_degree(weight='weight'))

    try:
        betweenness = nx.betweenness_centrality(G, weight='weight')
    except Exception as e:
        print(f"Warning: Betweenness calculation failed: {e}")
        betweenness = {n: 0 for n in G.nodes()}

    # Combine into single dict
    results = {}
    for node in G.nodes():
        results[node] = {
            'pagerank': pagerank.get(node, 0),
            'in_degree': in_degree.get(node, 0),
            'out_degree': out_degree.get(node, 0),
            'net_flow': in_degree.get(node, 0) - out_degree.get(node, 0),
            'betweenness': betweenness.get(node, 0),
        }

    return results


def find_career_paths(G: nx.DiGraph, min_weight: int = 1) -> list:
    """
    Find common career paths (sequences of transitions).

    Returns list of (path, count) tuples.
    """
    paths = []

    # Get all edges with their weights
    edges = [(u, v, d.get('weight', 1)) for u, v, d in G.edges(data=True)]
    edges.sort(key=lambda x: -x[2])  # Sort by weight

    # Return top transitions as simple paths
    for source, target, weight in edges[:20]:
        if weight >= min_weight:
            paths.append({
                'from': source,
                'to': target,
                'count': weight,
            })

    return paths


def analyze_career_growth(df: pd.DataFrame) -> pd.DataFrame:
    """
    Analyze career growth trajectories.

    Returns DataFrame with:
    - initial_role -> current_role
    - seniority change
    - years since graduation
    """
    growth_data = []

    for _, row in df.iterrows():
        initial_role = row.get('initial_role', '')
        current_role = row.get('current_role', '')
        grad_year = row.get('graduation_year', 2024)

        if pd.isna(current_role) or not current_role:
            continue

        initial_seniority = get_seniority(initial_role)
        current_seniority = get_seniority(current_role)
        seniority_change = current_seniority - initial_seniority

        years = datetime.now().year - int(grad_year) if pd.notna(grad_year) else 0

        growth_data.append({
            'name': row.get('name', ''),
            'initial_company': row.get('initial_placement', ''),
            'current_company': row.get('current_company', ''),
            'initial_role': initial_role,
            'current_role': current_role,
            'initial_seniority': initial_seniority,
            'current_seniority': current_seniority,
            'seniority_change': seniority_change,
            'years': years,
            'velocity': seniority_change / max(years, 1),
        })

    return pd.DataFrame(growth_data)


def print_network_analysis(centrality: dict, paths: list, growth_df: pd.DataFrame):
    """Print formatted network analysis results."""
    print("\n" + "=" * 80)
    print("CAREER NETWORK ANALYSIS")
    print("=" * 80)

    # Sort by PageRank
    sorted_companies = sorted(
        centrality.items(),
        key=lambda x: x[1]['pagerank'],
        reverse=True
    )

    print(f"\n{'Company':<20} {'PageRank':<10} {'In':<6} {'Out':<6} {'Net':<6} {'Between':<8}")
    print("-" * 80)

    for company, scores in sorted_companies[:15]:
        if company == 'Academia':
            continue
        print(f"{company[:19]:<20} {scores['pagerank']:<10.3f} "
              f"{scores['in_degree']:<6} {scores['out_degree']:<6} "
              f"{scores['net_flow']:+5} {scores['betweenness']:<8.3f}")

    # Career paths
    print("\n" + "-" * 80)
    print("TOP CAREER TRANSITIONS")
    print("-" * 80)
    for path in paths[:10]:
        if path['from'] != 'Academia' and path['to'] != 'Academia':
            print(f"  {path['from']} -> {path['to']} ({path['count']} people)")

    # Career growth by company
    if len(growth_df) > 0:
        print("\n" + "-" * 80)
        print("CAREER GROWTH BY COMPANY (avg seniority change)")
        print("-" * 80)

        growth_by_company = growth_df.groupby('initial_company').agg({
            'seniority_change': 'mean',
            'velocity': 'mean',
            'name': 'count'
        }).rename(columns={'name': 'count'})

        growth_by_company = growth_by_company.sort_values('seniority_change', ascending=False)

        for company, row in growth_by_company.head(10).iterrows():
            if row['count'] >= 1:
                print(f"  {company[:20]:<22} +{row['seniority_change']:.1f} levels "
                      f"(velocity: {row['velocity']:.2f}/yr, n={int(row['count'])})")

    print("\n" + "=" * 80)
    print("Key:")
    print("  PageRank = 'Ultimate destination' popularity (higher = where careers end up)")
    print("  In/Out = Talent inflows/outflows")
    print("  Net = In - Out (positive = destination, negative = source)")
    print("  Between = Stepping stone centrality (higher = career accelerator)")
    print("=" * 80)


def visualize_network(G: nx.DiGraph, centrality: dict, output_path: str = 'charts/career_network.png'):
    """Create a visualization of the career network graph."""
    import matplotlib.pyplot as plt
    from pathlib import Path

    Path('charts').mkdir(exist_ok=True)

    # Filter to only companies with connections (not isolated nodes)
    connected = [n for n in G.nodes() if G.degree(n) > 0]
    G_sub = G.subgraph(connected).copy()

    if len(G_sub.nodes()) == 0:
        print("No connected nodes to visualize")
        return

    # Set up figure
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_facecolor('#1a1a2e')
    fig.patch.set_facecolor('#1a1a2e')

    # Node sizes based on PageRank
    node_sizes = []
    for node in G_sub.nodes():
        pr = centrality.get(node, {}).get('pagerank', 0.05)
        node_sizes.append(max(pr * 5000, 500))

    # Node colors based on net flow
    node_colors = []
    for node in G_sub.nodes():
        net = centrality.get(node, {}).get('net_flow', 0)
        if net > 0:
            node_colors.append('#00ff88')  # Green = destination
        elif net < 0:
            node_colors.append('#ff6b6b')  # Red = source
        else:
            node_colors.append('#4ecdc4')  # Teal = balanced

    # Edge widths based on weight
    edge_widths = [G_sub[u][v].get('weight', 1) * 2 for u, v in G_sub.edges()]

    # Layout
    pos = nx.spring_layout(G_sub, k=2, iterations=50, seed=42)

    # Draw edges
    nx.draw_networkx_edges(
        G_sub, pos,
        edge_color='#ffffff',
        alpha=0.4,
        width=edge_widths,
        arrows=True,
        arrowsize=20,
        arrowstyle='-|>',
        connectionstyle='arc3,rad=0.1',
        ax=ax
    )

    # Draw nodes
    nx.draw_networkx_nodes(
        G_sub, pos,
        node_size=node_sizes,
        node_color=node_colors,
        alpha=0.9,
        ax=ax
    )

    # Draw labels
    labels = {n: n[:12] for n in G_sub.nodes()}
    nx.draw_networkx_labels(
        G_sub, pos,
        labels=labels,
        font_size=9,
        font_color='white',
        font_weight='bold',
        ax=ax
    )

    # Add edge labels (transition counts)
    edge_labels = {(u, v): str(d.get('weight', 1)) for u, v, d in G_sub.edges(data=True)}
    nx.draw_networkx_edge_labels(
        G_sub, pos,
        edge_labels=edge_labels,
        font_size=8,
        font_color='yellow',
        ax=ax
    )

    ax.set_title('Career Transition Network\n(Green=Destination, Red=Source, Size=PageRank)',
                 fontsize=14, color='white', fontweight='bold')
    ax.axis('off')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, facecolor='#1a1a2e', bbox_inches='tight')
    plt.close()
    print(f"Saved network visualization to {output_path}")


def visualize_sankey(df: pd.DataFrame, output_path: str = 'charts/career_sankey.html'):
    """Create an interactive Sankey diagram of career flows."""
    try:
        import plotly.graph_objects as go
    except ImportError:
        print("Plotly not installed, skipping Sankey diagram")
        return

    from pathlib import Path
    Path('charts').mkdir(exist_ok=True)

    # Build transitions
    transitions = []
    for _, row in df.iterrows():
        initial = row.get('initial_placement', '')
        current = row.get('current_company', '')

        if pd.isna(initial) or pd.isna(current):
            continue
        if not initial or not current:
            continue

        initial_norm = normalize_company(str(initial))
        current_norm = normalize_company(str(current))

        # Skip if same company (compare full normalized names)
        if initial_norm.lower() == current_norm.lower():
            continue

        transitions.append((initial_norm[:15], current_norm[:15]))

    if not transitions:
        print("No transitions to visualize")
        return

    # Count transitions
    from collections import Counter
    trans_counts = Counter(transitions)

    # Build node list
    sources = list(set(t[0] for t in transitions))
    targets = list(set(t[1] for t in transitions))
    all_nodes = sources + [t for t in targets if t not in sources]

    # Create Sankey data
    source_idx = []
    target_idx = []
    values = []

    for (src, tgt), count in trans_counts.items():
        source_idx.append(all_nodes.index(src))
        target_idx.append(all_nodes.index(tgt) if tgt in all_nodes else len(all_nodes))
        values.append(count)

    # Create figure
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color='black', width=0.5),
            label=all_nodes,
            color=['#ff6b6b' if n in sources else '#00ff88' for n in all_nodes]
        ),
        link=dict(
            source=source_idx,
            target=target_idx,
            value=values,
            color='rgba(100,100,100,0.4)'
        )
    )])

    fig.update_layout(
        title='Career Transition Flow (Red=Source → Green=Destination)',
        font_size=12,
        paper_bgcolor='#1a1a2e',
        font_color='white'
    )

    fig.write_html(output_path)
    print(f"Saved Sankey diagram to {output_path}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Career network analysis')
    parser.add_argument('--input', default='data/candidates_enriched.csv', help='Input CSV')
    parser.add_argument('--viz', action='store_true', help='Generate visualizations')
    args = parser.parse_args()

    print(f"Loading {args.input}...")
    df = pd.read_csv(args.input)
    print(f"Found {len(df)} candidates")

    # Build graph
    print("\nBuilding career graph...")
    G = build_career_graph(df)
    print(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    # Calculate centrality
    print("Calculating centrality measures...")
    centrality = calculate_centrality(G)

    # Find paths
    paths = find_career_paths(G)

    # Analyze growth
    print("Analyzing career growth...")
    growth_df = analyze_career_growth(df)

    # Print results
    print_network_analysis(centrality, paths, growth_df)

    # Save results
    centrality_df = pd.DataFrame.from_dict(centrality, orient='index')
    centrality_df.to_csv('data/network_centrality.csv')
    print(f"\nSaved centrality scores to data/network_centrality.csv")

    # Generate visualizations
    if args.viz:
        print("\nGenerating visualizations...")
        visualize_network(G, centrality)
        visualize_sankey(df)


if __name__ == "__main__":
    main()
