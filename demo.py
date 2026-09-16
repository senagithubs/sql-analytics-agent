"""A repeatable, no-API-cost presentation. Run from the repository root."""
from tempfile import TemporaryDirectory
from pathlib import Path
from agent import AnalyticsAgent
from agent.guard import validate_sql, UnsafeSQLError
from data.build_sample_db import build


def main():
    with TemporaryDirectory() as folder:
        url = 'sqlite:///' + str(Path(folder) / 'demo.db')
        build(url)
        agent = AnalyticsAgent(url, offline=True)
        for question in ['What is the total revenue?', 'Which source brought the most leads?']:
            result = agent.ask(question)
            print('\nQUESTION:', question)
            print('VALIDATED SQL:', result['sql'])
            print('DATABASE RESULT:', result['rows'])
        print('\nREJECTED QUERY: SELECT * FROM "secrets"')
        try:
            validate_sql('SELECT * FROM "secrets"', set(agent.schema))
        except UnsafeSQLError as exc:
            print('REASON:', exc)
        print('\nCAPPED QUERY:', validate_sql('SELECT * FROM leads LIMIT 99999', set(agent.schema)))
        print('\nMode: deterministic rules. No LLM/API call was made.')


if __name__ == '__main__':
    main()
