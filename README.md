# Text-to-SQL Analytics Agent

Business question → SQL → validation → read-only SQLite → actual result rows.
The bundled data is synthetic. The offline translator recognizes six question patterns;
optional OpenAI translation accepts free-form questions. Both use the same execution boundary.

## Run the demo

Python 3.11+ from the repository root:

```bash
python -m pip install -r requirements.txt
python demo.py
python -m pytest -q
```

`demo.py` creates a temporary database, shows two answers, rejects a hidden table,
and caps an oversized query. It never uses an API key and leaves no database behind.
See the [offline demonstration walkthrough](docs/demo.md).

To explore the five sample questions:

```bash
python data/build_sample_db.py
python cli.py --offline
```

The builder **replaces the four demo tables' contents** in `data/analytics.db`.
Use it only for demo data. To enable optional paid translation, configure
`OPENAI_API_KEY` locally and run `python cli.py`. No model call is needed for tests.
The live LLM path has not been evaluated for semantic accuracy in this release.

## Query boundary

- SQLGlot parses one SQLite SELECT/set query, checks physical tables in CTEs,
  joins and subqueries, and rejects unsupported statements/functions.
- The **outermost** LIMIT is capped, including when subqueries have their own LIMIT.
- The database file opens with `mode=ro` and `PRAGMA query_only=ON`.
- A SQLite authorizer separately checks every table read and function call.
- A progress handler interrupts expensive computation after the configured budget
  (default two seconds). This is not a hard operating-system memory/time sandbox.
- The default allowlist includes all ordinary tables discovered in the file.
  Pass `allowed_tables={'leads', 'revenue'}` to restrict a mixed database; only this
  subset is included in the model prompt. Views are excluded.

Only existing, local, file-backed SQLite databases are supported. PostgreSQL would
need a separate least-privilege execution implementation. Recursive CTEs, schema-qualified
tables, table functions and unlisted functions are intentionally outside this demo.

Read-only access does not establish user authorization or make an answer semantically
correct. Production work also needs per-user permissions, column/privacy policies,
resource isolation and an evaluation dataset. A status distribution cannot measure
conversion rates between funnel stages without event history.

## Evidence

Tests cover quoted hidden tables, comma joins, nested queries, CTEs, excessive/negative
limits, actual write rejection, authorizer enforcement when the parser is bypassed,
query interruption and deterministic results. GitHub Actions runs the same offline suite.

With seed 42 and the fixed sample dates, total revenue is **187,172.39**;
referrals account for **115 of 500** leads. These are sample values, not client outcomes.
