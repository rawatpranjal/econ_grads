#!/usr/bin/env python3
"""
Work tagging module for Economics PhD candidate analysis.
Provides curated tags, ngram extraction, and fractional allocation.
"""

import re
from collections import Counter
from typing import List, Dict

# DOMAINS - What area/industry they work in
DOMAIN_TAGS = {
    'Pricing/Revenue': [
        'pricing', 'revenue', 'monetization', 'dynamic pricing', 'price optimization',
        'price', 'tariff', 'surge', 'fee'
    ],
    'Marketing/Ads': [
        'marketing', 'ads', 'advertising', 'content', 'attribution', 'growth',
        'acquisition', 'campaign', 'creative'
    ],
    'Platform/Marketplace': [
        'platform', 'marketplace', 'multi-sided', 'matching', 'network effects',
        'two-sided', 'market design', 'mechanism', 'ride-hailing', 'uber eats'
    ],
    'Prime/Subscription': [
        'prime', 'subscription', 'membership'
    ],
    'Crypto/Fintech': [
        'crypto', 'cryptocurrency', 'bitcoin', 'stablecoin', 'blockchain',
        'fintech', 'payment', 'defi', 'token', 'tokenized'
    ],
    'Macro': [
        'macro', 'macroeconomic', 'economic outlook', 'gdp', 'inflation', 'central bank'
    ],
    'People/HR Analytics': [
        'people analytics', 'workforce', 'employee', 'hr analytics',
        'organizational', 'talent', 'hiring', 'labor economics', 'personnel'
    ],
    'Supply Chain/Logistics': [
        'supply chain', 'logistics', 'inventory', 'operations', 'fulfillment',
        'delivery', 'fleet', 'dispatch', 'routing', 'sourcing'
    ],
    'Risk/Credit': [
        'risk', 'credit', 'fraud', 'underwriting', 'default', 'lending',
        'insurance', 'claims'
    ],
    'Search/Ranking': [
        'search ranking', 'feed ranking', 'relevance', 'discovery', 'retrieval',
        'personalization', 'recommendations', 'reels', 'news feed'
    ],
    'Policy/Regulation': [
        'policy', 'regulation', 'antitrust', 'compliance', 'government',
        'regulatory', 'public policy', 'public finance'
    ],
    'Product': [
        'product optimization', 'user research', 'engagement', 'conversion', 'funnel',
        'product', 'brands'
    ],
    'Sales/Revenue': [
        'sales', 'revenue', 'business strategies', 'business strategy'
    ],
}

# METHODS - What techniques/approaches they use
METHOD_TAGS = {
    'Causal Inference': [
        'causal', 'experimentation', 'a/b test', 'ab test', 'rct',
        'treatment effect', 'experiment', 'randomized', 'counterfactual'
    ],
    'Forecasting': [
        'forecast', 'prediction', 'time series', 'projections', 'predictive', 'nowcast'
    ],
    'Machine Learning': [
        'machine learning', 'ml', 'gradient boosted', 'random forest',
        'reinforcement learning', 'bandit'
    ],
    'Deep Learning': [
        'deep learning', 'neural', 'dnn', 'cnn', 'rnn'
    ],
    'LLMs/GenAI': [
        'llm', 'llms', 'transformer', 'generative ai', 'gpt', 'large language model'
    ],
    'Econometrics': [
        'econometric', 'econometrics', 'regression', 'empirical',
        'statistical', 'panel data'
    ],
    'Optimization': [
        'optimization', 'algorithms', 'modeling', 'simulation'
    ],
    'Data Science': [
        'data science', 'analytics', 'metrics', 'kpi', 'quantitative', 'quant'
    ],
    'Game Theory': [
        'game theory', 'mechanism design', 'auction', 'contract design',
        'incentive', 'strategic'
    ],
    'Structural Modeling': [
        'structural', 'structural model', 'structural estimation'
    ],
    'Measurement': [
        'measurement', 'incrementality', 'attribution'
    ],
}

# Combined for backwards compatibility
WORK_TAGS = {**DOMAIN_TAGS, **METHOD_TAGS}

# Common stopwords to filter out from ngrams
STOPWORDS = {
    'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
    'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
    'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
    'that', 'this', 'these', 'those', 'i', 'you', 'he', 'she', 'it',
    'we', 'they', 'what', 'which', 'who', 'whom', 'their', 'its', 'his',
    'her', 'our', 'your', 'my', 'about', 'into', 'through', 'during',
    'before', 'after', 'above', 'below', 'between', 'under', 'over',
    'such', 'no', 'not', 'only', 'same', 'so', 'than', 'too', 'very',
    'just', 'also', 'now', 'here', 'there', 'when', 'where', 'why', 'how',
    'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other',
    'some', 'any', 'many', 'much', 'own', 'out', 'up', 'down', 'off',
    'then', 'once', 'again', 'further', 'while', 'although', 'because',
    'if', 'unless', 'until', 'since', 'even', 'though', 'whether',
    'unknown', 'nan', 'none', '0', '0.0', ''
}


def tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase words."""
    if not text or not isinstance(text, str):
        return []
    # Remove punctuation and split
    text = re.sub(r'[^\w\s-]', ' ', text.lower())
    words = text.split()
    # Filter stopwords and short words
    return [w for w in words if w not in STOPWORDS and len(w) > 2]


def extract_ngrams(texts: List[str], n: int = 2, top_k: int = 20) -> List[tuple]:
    """
    Extract top ngrams from a list of texts.

    Args:
        texts: List of text strings
        n: n-gram size (2 for bigrams, 3 for trigrams)
        top_k: Number of top ngrams to return

    Returns:
        List of (ngram, count) tuples
    """
    ngram_counter = Counter()

    for text in texts:
        tokens = tokenize(text)
        for i in range(len(tokens) - n + 1):
            ngram = ' '.join(tokens[i:i + n])
            ngram_counter[ngram] += 1

    return ngram_counter.most_common(top_k)


def categorize_with_fractional_allocation(text: str, tags: Dict[str, List[str]] = None) -> Dict[str, float]:
    """
    Match text against tags and return fractional allocations.

    Args:
        text: Text to categorize (e.g., work_focus or team description)
        tags: Dictionary of category -> keywords. Defaults to WORK_TAGS.

    Returns:
        Dictionary of category -> fractional weight.
        If text matches 3 categories, each gets 0.333...

    Example:
        text = "pricing and experimentation platform"
        returns: {'Pricing/Revenue': 0.33, 'Causal Inference': 0.33, 'Platform/Marketplace': 0.33}
    """
    if tags is None:
        tags = WORK_TAGS

    if not text or not isinstance(text, str):
        return {'Other': 1.0}

    text_lower = text.lower()
    matched_categories = []

    for category, keywords in tags.items():
        if any(kw in text_lower for kw in keywords):
            matched_categories.append(category)

    if not matched_categories:
        return {'Other': 1.0}

    weight = 1.0 / len(matched_categories)
    return {cat: weight for cat in matched_categories}


def aggregate_fractional_counts(allocations: List[Dict[str, float]]) -> Dict[str, float]:
    """
    Aggregate fractional allocations across all candidates.

    Args:
        allocations: List of allocation dicts from categorize_with_fractional_allocation

    Returns:
        Dictionary of category -> total fractional count
    """
    totals = Counter()
    for alloc in allocations:
        for cat, weight in alloc.items():
            totals[cat] += weight
    return dict(totals)


def get_all_matched_tags(text: str, tags: Dict[str, List[str]] = None) -> List[str]:
    """
    Get all matching categories for a text (without fractional allocation).

    Args:
        text: Text to categorize
        tags: Dictionary of category -> keywords. Defaults to WORK_TAGS.

    Returns:
        List of matched category names
    """
    if tags is None:
        tags = WORK_TAGS

    if not text or not isinstance(text, str):
        return []

    text_lower = text.lower()
    matched = []

    for category, keywords in tags.items():
        if any(kw in text_lower for kw in keywords):
            matched.append(category)

    return matched


if __name__ == "__main__":
    # Test the module
    test_texts = [
        "pricing and experimentation platform",
        "causal inference for marketplace matching",
        "demand forecasting using machine learning",
        "ads optimization and marketing analytics",
        "unknown",
        "",
    ]

    print("Testing fractional allocation:\n")
    for text in test_texts:
        result = categorize_with_fractional_allocation(text)
        print(f"'{text}' -> {result}")

    print("\n\nTesting ngram extraction:\n")
    sample_texts = [
        "pricing optimization and revenue management",
        "pricing algorithms for dynamic pricing",
        "causal inference experiments",
        "marketplace pricing and demand forecasting",
    ]
    ngrams = extract_ngrams(sample_texts, n=2, top_k=10)
    print(f"Top bigrams: {ngrams}")
