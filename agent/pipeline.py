"""
pipeline.py
-----------
Ana akis: soru -> SQL uret -> DOGRULA (guard) -> calistir -> cevapla.

Iki SQL uretici var:
1. LLMTranslator  : OpenAI ile gercek text-to-SQL (uretim modu).
2. RuleTranslator : API anahtari yokken calisan desen tabanli demo modu
                    (graceful degradation — sistem her kosulda calisir).

Onemli tasarim karari: LLM'in ciktisi ASLA dogrudan calistirilmaz;
once guard.validate_sql'den gecer. Dogruluk vurgusu ilanin kalbiydi:
cevap her zaman gercek veriden gelir, sayi uydurulamaz — cunku cevabi
LLM degil, veritabani verir; LLM yalnizca SORGUYU yazar.
"""

import logging
import os
import re

from sqlalchemy import create_engine, text

from .guard import validate_sql, UnsafeSQLError
from .schema import get_schema, schema_as_prompt

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
    def __init__(self, db_url: str = "sqlite:///data/analytics.db"):
        self.db_url = db_url
        self.engine = create_engine(db_url)
        self.schema = get_schema(db_url)
        self.schema_prompt = schema_as_prompt(self.schema)

        api_key = os.environ.get("OPENAI_API_KEY")
        self.translator = LLMTranslator(api_key) if api_key else RuleTranslator()
        self.mode = "llm" if api_key else "rule-based demo"

    def ask(self, question: str) -> dict:
        """Soru sorar; {sql, rows, columns} dondurur. Hata halinde aciklayici mesaj."""
        raw_sql = self.translator.to_sql(question, self.schema_prompt)
        safe_sql = validate_sql(raw_sql, allowed_tables=set(self.schema))
        with self.engine.connect() as conn:
            result = conn.execute(text(safe_sql))
            columns = list(result.keys())
            rows = [tuple(r) for r in result.fetchall()]
        logger.info("Q: %s | SQL: %s | %d satir", question, safe_sql, len(rows))
        return {"sql": safe_sql, "columns": columns, "rows": rows}
