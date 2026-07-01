# Text-to-SQL Analytics Agent

A natural-language analytics agent: ask business questions in plain English
("Which source brought the most leads?", "Show me the revenue trend") and get
answers grounded in real data — the LLM writes the **query**, the **database**
provides the numbers, so answers cannot be fabricated.

## Why accuracy is the core design goal

Text-to-SQL systems fail in two ways: the LLM writes destructive SQL, or it
hallucinates tables/columns. This project treats both as first-class problems
solved by a **validation layer** (`agent/guard.py`) that every generated query
must pass **before execution**:

- single statement, `SELECT`-only (rejects INSERT/UPDATE/DELETE/DROP/…)
- table **allowlist** derived from live schema introspection — a hallucinated
  table name is caught before it ever reaches the database
- enforced `LIMIT` to cap result size

The LLM's output is never trusted; it is checked, then executed read-only.

## Architecture

```
question ──► translator (OpenAI · temp=0)  ──► guard.validate_sql ──► DB ──► answer
                 │ schema injected via                │
                 │ live introspection                 └─ rejects unsafe /
                 │ (agent/schema.py)                     hallucinated SQL
                 └─ falls back to a rule-based demo translator
                    when no OPENAI_API_KEY is set (graceful degradation)
```

- **SQLAlchemy** keeps the layer engine-agnostic: SQLite for the demo,
  PostgreSQL in production by changing one URL.
- **Schema introspection** means the prompt always reflects the real database —
  essential when the schema is large (30+ tables) or evolving.
- **temperature=0** for SQL generation: determinism over creativity.

## Quick start

```bash
pip install -r requirements.txt
python data/build_sample_db.py      # builds a sample leads/revenue/marketing DB
python cli.py                       # runs demo questions end-to-end
export OPENAI_API_KEY=...           # optional: enables free-form questions
```

## Tests

```bash
pytest
```

10 tests cover the guard layer (destructive SQL, chained statements,
hallucinated tables) and end-to-end correctness (funnel counts reconcile with
totals, orderings verified against the data).

## Project structure

```
├── cli.py                  # interactive demo
├── agent/
│   ├── guard.py            # SQL validation layer (the heart of the project)
│   ├── schema.py           # live schema introspection → prompt
│   └── pipeline.py         # question → SQL → validate → execute → answer
├── data/build_sample_db.py # sample analytics DB (leads, revenue, spend)
└── tests/                  # guard + end-to-end tests
```
