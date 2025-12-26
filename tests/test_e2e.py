"""End-to-end tests for econ-grads analysis scripts."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
CHARTS_DIR = ROOT / "charts"


def test_analyze_runs():
    """Verify analyze.py runs and produces output."""
    result = subprocess.run(
        [sys.executable, ROOT / "analyze.py"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"analyze.py failed: {result.stderr}"
    assert "ECON PHD TECH PLACEMENTS" in result.stdout
    assert "Total candidates:" in result.stdout
    assert "PLACEMENTS BY SCHOOL" in result.stdout


def test_charts_generates_files():
    """Verify charts.py creates all expected chart files."""
    result = subprocess.run(
        [sys.executable, ROOT / "charts.py"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"charts.py failed: {result.stderr}"

    expected_files = [
        "school_placements.png",
        "top_companies.png",
        "heatmap.png",
        "timeline.png",
        "roles.png",
    ]

    for filename in expected_files:
        filepath = CHARTS_DIR / filename
        assert filepath.exists(), f"Missing chart: {filename}"
        assert filepath.stat().st_size > 0, f"Empty chart: {filename}"
