

import logging

from agent import AnalyticsAgent

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

DEMO_QUESTIONS = [
    "What is the total revenue?",
    "Show me the revenue trend by month",
    "Which source brought the most leads?",
    "Where are we losing people in the funnel?",
    "What's our marketing spend by channel?",
]


def main():
    agent = AnalyticsAgent()
    print(f"Analytics agent hazir ({agent.mode} modunda). Ornek sorular calisiyor:\n")
    for q in DEMO_QUESTIONS:
        try:
            out = agent.ask(q)
            print(f"Soru : {q}")
            print(f"SQL  : {out['sql']}")
            print(f"Sonuc: {out['columns']}")
            for row in out["rows"][:5]:
                print(f"       {row}")
            print()
        except Exception as exc:
            print(f"Soru : {q}\nHata : {exc}\n")


if __name__ == "__main__":
    main()
