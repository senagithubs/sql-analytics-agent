# Offline demonstration

## Run

From the repository root with Python 3.11 or newer:

```bash
python -m pip install -r requirements.txt
python demo.py
python -m pytest -q
```

The demo creates a temporary SQLite database from deterministic synthetic data.
It requires no API key and removes the temporary database when finished.

## Demonstrated behavior

| Check | Expected result |
|---|---|
| Total revenue | 187,172.39 |
| Lead-source ranking | Referrals: 115 of 500 leads |
| Access to a hidden table | Rejected |
| Requested LIMIT of 99,999 | Capped at 1,000 |

The offline translator supports predefined question patterns. Each generated query
passes parsed SQL validation before execution through a read-only SQLite connection.
Database authorization rules provide a second boundary for table and function access.

## Validation

The 34-test suite covers query validation, disallowed writes, result limits,
timeout recovery, and deterministic sample data. GitHub Actions runs the tests
and the same offline demonstration.

## Scope

This demonstration supports existing file-backed SQLite databases. Synthetic
results are not client outcomes. The optional live LLM translator is separate
from the offline demonstration and has not been evaluated for semantic accuracy.
Read-only controls do not replace application-level user authorization.
