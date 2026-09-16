

import logging
import os
import re

from sqlalchemy import text

from .guard import validate_sql, UnsafeSQLError
from .schema import get_schema, schema_as_prompt
from .readonly import readonly_engine, restrict_connection

logger = logging.getLogger(__name__)


class RuleTranslator:
    """API anahtarsiz demo: bilinen soru kaliplarini SQL'e cevirir."""

    PATTERNS = [
        (re.compile(r"total revenue", re.I),
         "SELECT ROUND(SUM(amount), 2) AS total_revenue FROM revenue"),
        (re.compile(r"revenue.*(trend|by month|monthly)", re.I),
         "SELECT substr(paid_at, 1, 7) AS month, ROUND(SUM(amount), 2) AS revenue "
         "FROM revenue GROUP BY month ORDER BY month"),
        (re.compile(r"(which|what).*source.*(most|top).*lead|lead.*by source", re.I),
         "SELECT source, COUNT(*) AS lead_count FROM leads "
         "GROUP BY source ORDER BY lead_count DESC"),
        (re.compile(r"funnel|losing", re.I),
         "SELECT status, COUNT(*) AS count FROM leads GROUP BY status ORDER BY count DESC"),
        (re.compile(r"show[- ]?up|no[- ]?show", re.I),
         "SELECT showed_up, COUNT(*) AS count FROM appointments GROUP BY showed_up"),
        (re.compile(r"spend|marketing cost", re.I),
         "SELECT channel, ROUND(SUM(amount), 2) AS total_spend FROM marketing_spend "
         "GROUP BY channel ORDER BY total_spend DESC"),
    ]

    def to_sql(self, question: str, schema_prompt: str) -> str:
        for pattern, sql in self.PATTERNS:
            if pattern.search(question):
                return sql
        raise ValueError(
            "Demo modu bu soruyu taniyamadi. OPENAI_API_KEY ayarlayarak "
            "serbest formdaki sorulari acabilirsiniz."
        )


class LLMTranslator:
    """OpenAI ile text-to-SQL. Sema prompt'a gomulur, cikti guard'dan gecer."""

    SYSTEM = (
        "You translate business questions into a SINGLE read-only SQL SELECT "
        "statement for the schema below. Rules: only SELECT; only listed "
        "tables/columns; no comments; no explanations — output SQL only.\n\n{schema}"
    )

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def to_sql(self, question: str, schema_prompt: str) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=0,  # SQL uretiminde yaraticilik istemiyoruz
            max_tokens=300,
            messages=[
                {"role": "system", "content": self.SYSTEM.format(schema=schema_prompt)},
                {"role": "user", "content": question},
            ],
        )
        sql = resp.choices[0].message.content.strip()
        return sql.removeprefix("```sql").removeprefix("```").removesuffix("```").strip()


class AnalyticsAgent:
    def __init__(self, db_url: str = "sqlite:///data/analytics.db", *,
                 allowed_tables=None, max_rows=1000, timeout_seconds=2, offline=False):
        if not isinstance(max_rows, int) or isinstance(max_rows, bool) or max_rows < 1:
            raise ValueError("max_rows must be a positive integer.")
        if not 0 < timeout_seconds <= 30:
            raise ValueError("timeout_seconds must be between 0 and 30.")
        self.engine = readonly_engine(db_url)
        schema = get_schema(self.engine)
        if allowed_tables is not None:
            if not set(allowed_tables) <= set(schema):
                raise ValueError("The table allowlist contains an unknown table.")
            schema = {t: cols for t, cols in schema.items() if t in allowed_tables}
        self.schema = schema
        self.schema_prompt = schema_as_prompt(schema)
        self.max_rows = max_rows
        self.timeout_seconds = timeout_seconds
        api_key = None if offline else os.environ.get("OPENAI_API_KEY")
        self.translator = LLMTranslator(api_key) if api_key else RuleTranslator()
        self.mode = "llm" if api_key else "rule-based demo"

    def ask(self, question: str) -> dict:
        raw_sql = self.translator.to_sql(question, self.schema_prompt)
        safe_sql = validate_sql(raw_sql, allowed_tables=set(self.schema), max_limit=self.max_rows)
        with self.engine.connect() as conn:
            dbapi_conn = conn.connection.driver_connection
            restrict_connection(dbapi_conn, self.schema, self.timeout_seconds)
            try:
                result = conn.execute(text(safe_sql))
                columns = list(result.keys())
                rows = [tuple(r) for r in result.fetchmany(self.max_rows)]
            finally:
                dbapi_conn.set_authorizer(None)
                dbapi_conn.set_progress_handler(None, 0)
        logger.info("Executed validated query; %d rows", len(rows))
        return {"sql": safe_sql, "columns": columns, "rows": rows}
