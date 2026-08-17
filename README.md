# Text-to-SQL Analytics Agent

A natural-language analytics agent that turns business questions into SQL, runs them read-only, and answers using real query results instead of numbers the model made up.

## What it does

- Translates plain-English questions (e.g. "Which source brought the most leads?") into SQL using an LLM, with a rule-based fallback when no API key is configured.
- Runs every generated query through a validation layer before execution: single-statement, SELECT-only, a table allowlist derived from live schema introspection, and an enforced LIMIT.
- Executes only the validated query against a real database (SQLite for the demo, swappable to PostgreSQL) and returns the actual rows, so the agent answers from data rather than stating a number on its own.
- Falls back to a deterministic rule-based translator when no OPENAI_API_KEY is set, so the demo always runs end to end.
- Ships with a sample leads / revenue / marketing-spend database and a pytest suite covering both the guard layer and end-to-end correctness.

## Why the safety layer matters

Every SQL string returned by the LLM passes through agent/guard.py before it ever touches the database. It must be a single statement (no chained statements), it must start with SELECT or WITH ... SELECT, it is scanned for destructive keywords such as INSERT, UPDATE, DELETE, DROP and ALTER, and every table it references must appear in a table allowlist built by introspecting the live database schema - so a hallucinated table name is rejected before execution instead of surfacing as a confusing database error. If the generated query has no LIMIT, one is added automatically to cap result size. The LLM's SQL is never trusted or executed as-is: it is checked, then executed read-only. That is also why every answer is grounded in the real query results rather than a number the model guessed.

## Tech stack

- Python
- OpenAI API (gpt-4o-mini) for question-to-SQL translation, with a rule-based fallback
- SQLAlchemy for engine-agnostic database access and schema introspection
- SQLite for the bundled demo database
- pytest for the guard and end-to-end test suite

## Quickstart

```bash
pip install -r requirements.txt
python data/build_sample_db.py  # builds a sample leads/revenue/marketing DB
python cli.py                   # runs demo questions end-to-end
export OPENAI_API_KEY=...       # optional: enables free-form questions
```

Run the test suite (10 tests covering the guard layer and end-to-end correctness):

```bash
pytest
```

## Example output

```
Soru : Which source brought the most leads?
SQL  : SELECT source, COUNT(*) AS lead_count FROM leads GROUP BY source ORDER BY lead_count DESC LIMIT 1000
Sonuc: ['source', 'lead_count']
  ('google_ads', 108)
  ('facebook', 102)
  ...
```
