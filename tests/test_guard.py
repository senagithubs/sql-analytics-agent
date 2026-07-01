"""Guvenlik katmani testleri — projenin en kritik guvencesi."""

import pytest

from agent.guard import validate_sql, UnsafeSQLError

TABLES = {"leads", "revenue", "appointments", "marketing_spend"}


def test_select_passes_and_gets_limit():
    out = validate_sql("SELECT * FROM leads", TABLES)
    assert out.lower().startswith("select")
    assert "limit" in out.lower()


def test_existing_limit_is_preserved():
    out = validate_sql("SELECT * FROM leads LIMIT 5", TABLES)
    assert out.count("LIMIT") + out.count("limit") == 1


def test_delete_is_rejected():
    with pytest.raises(UnsafeSQLError):
        validate_sql("DELETE FROM leads", TABLES)


def test_drop_inside_select_is_rejected():
    with pytest.raises(UnsafeSQLError):
        validate_sql("SELECT 1; DROP TABLE leads", TABLES)


def test_update_is_rejected():
    with pytest.raises(UnsafeSQLError):
        validate_sql("UPDATE leads SET status='x'", TABLES)


def test_unknown_table_is_rejected():
    # LLM tablo uydurursa (halusinasyon) calistirmadan yakalariz
    with pytest.raises(UnsafeSQLError):
        validate_sql("SELECT * FROM salaries", TABLES)


def test_join_with_allowed_tables_passes():
    sql = ("SELECT l.source, SUM(r.amount) FROM revenue r "
           "JOIN leads l ON l.id = r.lead_id GROUP BY l.source")
    assert validate_sql(sql, TABLES)
