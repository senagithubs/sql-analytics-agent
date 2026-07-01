"""
schema.py
---------
Veritabani semasini otomatik cikarir (introspection).

Neden? LLM'e "su tablolar ve kolonlar var" bilgisini prompt icinde
veririz; boylece sorgulari GERCEK semaya dayanir, uydurmaya degil.
Sema koda gomulmez — veritabani degisirse prompt otomatik guncellenir.
30+ tablolu gercek sistemlerde bu vazgecilmezdir.
"""

from sqlalchemy import create_engine, inspect


def get_schema(db_url: str) -> dict[str, list[str]]:
    """{tablo_adi: [kolonlar]} sozlugu dondurur."""
    engine = create_engine(db_url)
    insp = inspect(engine)
    return {
        table: [col["name"] for col in insp.get_columns(table)]
        for table in insp.get_table_names()
    }


def schema_as_prompt(schema: dict[str, list[str]]) -> str:
    """Semayi LLM promptuna eklenecek okunur metne cevirir."""
    lines = ["Database schema (SQLite dialect, dates stored as ISO strings):"]
    for table, cols in schema.items():
        lines.append(f"- {table}({', '.join(cols)})")
    return "\n".join(lines)
