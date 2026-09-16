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


@pytest.mark.parametrize('sql', [
    'SELECT * FROM "secrets"',
    'SELECT * FROM leads, secrets',
    'WITH x AS (SELECT * FROM secrets) SELECT * FROM x',
    'SELECT * FROM leads WHERE id IN (SELECT id FROM secrets)',
    'SELECT * FROM main.leads',
    'SELECT * FROM pragma_table_info("leads")',
    'SELECT load_extension("anything")',
    'SELECT randomblob(100000000)',
    'SELECT * FROM leads LIMIT -1',
    'SELECT * FROM leads LIMIT (SELECT 2)',
    'WITH RECURSIVE x(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM x) SELECT * FROM x',
    'SELECT * INTO backup FROM leads',
    'SELECT * FROM leads; SELECT * FROM revenue',
])
def test_unsafe_queries_rejected(sql):
    with pytest.raises(UnsafeSQLError):
        validate_sql(sql, TABLES)


@pytest.mark.parametrize('sql', [
    'SELECT * FROM leads LIMIT 100000',
    'SELECT * FROM (SELECT * FROM leads LIMIT 1) AS a CROSS JOIN leads',
    'SELECT id FROM leads UNION ALL SELECT id FROM leads',
])
def test_limit_applies_to_outer_query(sql):
    from sqlglot import parse_one
    query = parse_one(validate_sql(sql, TABLES, max_limit=10), read='sqlite')
    assert int(query.args['limit'].expression.this) == 10


def test_cte_and_quoted_allowed_table():
    assert validate_sql('WITH x AS (SELECT * FROM "leads") SELECT * FROM x', TABLES)


def test_keywords_and_semicolon_inside_string_are_data():
    assert validate_sql("SELECT 'delete; drop' AS label FROM leads", TABLES)
