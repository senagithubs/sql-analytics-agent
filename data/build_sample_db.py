

import random
from datetime import date, timedelta

from sqlalchemy import create_engine, text

random.seed(42)  # tekrarlanabilir demo verisi

SOURCES = ["google_ads", "facebook", "referral", "organic", "linkedin"]
STATUSES = ["new", "contacted", "qualified", "converted", "lost"]

DDL = """
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY,
    created_at DATE NOT NULL,
    source TEXT NOT NULL,
    status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY,
    lead_id INTEGER NOT NULL REFERENCES leads(id),
    scheduled_at DATE NOT NULL,
    showed_up INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS revenue (
    id INTEGER PRIMARY KEY,
    lead_id INTEGER NOT NULL REFERENCES leads(id),
    amount REAL NOT NULL,
    paid_at DATE NOT NULL
);
CREATE TABLE IF NOT EXISTS marketing_spend (
    id INTEGER PRIMARY KEY,
    channel TEXT NOT NULL,
    amount REAL NOT NULL,
    spent_at DATE NOT NULL
);
"""


def build(db_url: str = "sqlite:///data/analytics.db") -> None:
    engine = create_engine(db_url)
    with engine.begin() as conn:
        for stmt in DDL.strip().split(";"):
            if stmt.strip():
                conn.execute(text(stmt))

        # 500 lead, son 6 aya yayilmis
        start = date.today() - timedelta(days=180)
        lead_rows, appt_rows, rev_rows = [], [], []
        for i in range(1, 501):
            created = start + timedelta(days=random.randint(0, 180))
            source = random.choice(SOURCES)
            status = random.choices(STATUSES, weights=[15, 25, 20, 25, 15])[0]
            lead_rows.append({"id": i, "c": created.isoformat(), "s": source, "st": status})

            if status in ("qualified", "converted"):
                appt_rows.append({
                    "lid": i,
                    "sched": (created + timedelta(days=random.randint(1, 14))).isoformat(),
                    "show": 1 if random.random() > 0.25 else 0,
                })
            if status == "converted":
                rev_rows.append({
                    "lid": i,
                    "amt": round(random.uniform(200, 3000), 2),
                    "paid": (created + timedelta(days=random.randint(3, 30))).isoformat(),
                })

        conn.execute(text("DELETE FROM leads")); conn.execute(text("DELETE FROM appointments"))
        conn.execute(text("DELETE FROM revenue")); conn.execute(text("DELETE FROM marketing_spend"))

        conn.execute(text("INSERT INTO leads (id, created_at, source, status) VALUES (:id, :c, :s, :st)"), lead_rows)
        conn.execute(text("INSERT INTO appointments (lead_id, scheduled_at, showed_up) VALUES (:lid, :sched, :show)"), appt_rows)
        conn.execute(text("INSERT INTO revenue (lead_id, amount, paid_at) VALUES (:lid, :amt, :paid)"), rev_rows)

        spend_rows = []
        for ch in SOURCES:
            for m in range(6):
                spend_rows.append({
                    "ch": ch,
                    "amt": round(random.uniform(500, 5000), 2),
                    "d": (start + timedelta(days=30 * m)).isoformat(),
                })
        conn.execute(text("INSERT INTO marketing_spend (channel, amount, spent_at) VALUES (:ch, :amt, :d)"), spend_rows)

    print(f"Ornek veritabani hazir: {db_url} (500 lead, {len(rev_rows)} gelir kaydi)")


if __name__ == "__main__":
    build()
