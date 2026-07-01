"""
guard.py
--------
SQL guvenlik katmani. LLM'in urettigi SQL'i calistirmadan ONCE dogrular.

Neden var? Text-to-SQL sistemlerinde en buyuk iki risk:
1. Guvenlik: LLM (veya kotu niyetli prompt) DELETE/DROP uretebilir.
2. Dogruluk: LLM var olmayan tablo/kolon uydurabilir (halusinasyon).

Bu katman her iki riski de calistirma ANINDA keser:
- Sadece tek bir SELECT ifadesine izin verir.
- Tablo adlarini beyaz listeyle (allowlist) sinirlar.
- Yikici anahtar kelimeleri (DROP, DELETE, UPDATE...) reddeder.
- Sonuc boyutunu LIMIT ile sinirlar.

Yani LLM ne kadar yaratici olursa olsun, veritabanina yalnizca
guvenli, salt-okunur sorgular ulasir.
"""

import re

# Tek basina gorulmesi bile reddetme sebebi olan anahtar kelimeler
_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|replace|grant|revoke|attach|pragma|vacuum)\b",
    re.IGNORECASE,
)

_TABLE_PATTERN = re.compile(r"\b(?:from|join)\s+([a-zA-Z_][a-zA-Z0-9_]*)", re.IGNORECASE)


class UnsafeSQLError(ValueError):
    """Sorgu guvenlik kontrolunden gecemedi."""


def validate_sql(sql: str, allowed_tables: set[str], max_limit: int = 1000) -> str:
    """SQL'i dogrular; gecerse (gerekirse LIMIT eklenmis) halini dondurur.

    Gecemezse UnsafeSQLError firlatir — sorgu ASLA calistirilmaz.
    """
    stripped = sql.strip().rstrip(";").strip()

    # 1) Tek ifade olmali (noktali virgulle zincirleme yok)
    if ";" in stripped:
        raise UnsafeSQLError("Birden fazla SQL ifadesine izin verilmiyor.")

    # 2) Yalnizca SELECT (veya WITH ... SELECT)
    if not re.match(r"^\s*(select|with)\b", stripped, re.IGNORECASE):
        raise UnsafeSQLError("Yalnizca SELECT sorgularina izin verilir.")

    # 3) Yikici anahtar kelime taramasi
    if _FORBIDDEN.search(stripped):
        raise UnsafeSQLError("Sorgu yasakli bir anahtar kelime iceriyor.")

    # 4) Tablo beyaz listesi — LLM'in tablo uydurmasini engeller
    used_tables = {t.lower() for t in _TABLE_PATTERN.findall(stripped)}
    unknown = used_tables - {t.lower() for t in allowed_tables}
    if unknown:
        raise UnsafeSQLError(
            f"Bilinmeyen tablo(lar): {', '.join(sorted(unknown))}. "
            "Sorgu semadaki tablolarla sinirli olmali."
        )

    # 5) LIMIT zorunlulugu — devasa sonuc setlerini onler
    if not re.search(r"\blimit\s+\d+\b", stripped, re.IGNORECASE):
        stripped = f"{stripped} LIMIT {max_limit}"

    return stripped
