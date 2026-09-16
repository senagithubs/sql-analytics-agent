import sqlite3
from unittest.mock import patch

import pytest
from sqlalchemy.exc import DatabaseError

from agent import AnalyticsAgent
from agent.guard import UnsafeSQLError
from data.build_sample_db import build


@pytest.fixture
def agent(tmp_path):
    db = tmp_path / 'demo.db'
    url = 'sqlite:///' + str(db)
    build(url)
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE secrets (value TEXT)')
        conn.execute("INSERT INTO secrets VALUES ('private demo value')")
    return AnalyticsAgent(url, allowed_tables={'leads', 'revenue'}, max_rows=7, offline=True)


def test_guard_rejects_quoted_hidden_table(agent):
    with patch.object(agent.translator, 'to_sql', return_value='SELECT * FROM "secrets"'):
        with pytest.raises(UnsafeSQLError):
            agent.ask('untrusted question')


def test_authorizer_blocks_hidden_table_even_if_parser_is_bypassed(agent):
    with patch.object(agent.translator, 'to_sql', return_value='ignored'), \
         patch('agent.pipeline.validate_sql', return_value='SELECT * FROM "secrets"'):
        with pytest.raises(DatabaseError):
            agent.ask('untrusted question')


def test_readonly_database_blocks_write_independent_of_parser(agent):
    with agent.engine.connect() as conn:
        with pytest.raises(DatabaseError):
            conn.exec_driver_sql("DELETE FROM leads")
    with patch.object(agent.translator, 'to_sql', return_value='SELECT COUNT(*) FROM leads'):
        assert agent.ask('count')['rows'] == [(500,)]


def test_oversized_result_capped(agent):
    with patch.object(agent.translator, 'to_sql', return_value='SELECT * FROM leads LIMIT 99999'):
        assert len(agent.ask('all')['rows']) == 7


def test_costly_query_interrupted_and_next_query_works(agent):
    agent.timeout_seconds = 0.001
    query = 'SELECT SUM(a.id*b.id*c.id) FROM leads a CROSS JOIN leads b CROSS JOIN leads c'
    with patch.object(agent.translator, 'to_sql', return_value=query):
        with pytest.raises(DatabaseError, match='interrupted'):
            agent.ask('costly')
    agent.timeout_seconds = 2
    with patch.object(agent.translator, 'to_sql', return_value='SELECT COUNT(*) FROM leads'):
        assert agent.ask('count')['rows'] == [(500,)]


def test_build_is_repeatable(tmp_path):
    url = 'sqlite:///' + str(tmp_path / 'demo.db')
    build(url)
    one = AnalyticsAgent(url, offline=True).ask('total revenue')
    build(url)
    two = AnalyticsAgent(url, offline=True).ask('total revenue')
    assert one == two
