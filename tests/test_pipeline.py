"""Uctan uca test: gercek (ornek) veritabaninda soru -> dogru cevap."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.build_sample_db import build
from agent import AnalyticsAgent

DB = "sqlite:///test_analytics.db"


def setup_module(module):
    build(DB)


def teardown_module(module):
    if os.path.exists("test_analytics.db"):
        os.remove("test_analytics.db")


def test_total_revenue_returns_positive_number():
    agent = AnalyticsAgent(DB)
    out = agent.ask("What is the total revenue?")
    assert out["rows"][0][0] > 0


def test_lead_source_breakdown_covers_all_sources():
    agent = AnalyticsAgent(DB)
    out = agent.ask("Which source brought the most leads?")
    assert len(out["rows"]) == 5  # 5 kaynak tanimladik
    # En cok lead getiren kaynak ilk sirada olmali (DESC)
    counts = [row[1] for row in out["rows"]]
    assert counts == sorted(counts, reverse=True)


def test_funnel_counts_sum_to_total_leads():
    agent = AnalyticsAgent(DB)
    out = agent.ask("Where are we losing people in the funnel?")
    assert sum(row[1] for row in out["rows"]) == 500  # toplam lead sayisi
