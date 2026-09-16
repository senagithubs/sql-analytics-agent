# Two-minute demo

Run `python demo.py` once before recording. Share the terminal and keep this script beside it.
This is a live demo command and recording script; no recorded video is included.

| Time | Show | Say |
|---|---|---|
| 0:00–0:20 | README flow | “This demo turns a business question into a database result. The data is synthetic; today I use deterministic rules so the demo has no API cost.” |
| 0:20–0:50 | Total revenue result | “The question becomes a SELECT. Validation adds a row cap. The database returns 187,172.39; the language model does not invent that figure.” |
| 0:50–1:10 | Lead sources | “Referrals lead with 115 records. GROUP BY aggregates each source; ORDER BY ranks the result.” |
| 1:10–1:35 | Hidden-table rejection and LIMIT cap | “Quoted identifiers still go through the table allowlist. A request for 99,999 rows is capped at 1,000.” |
| 1:35–2:00 | `python -m pytest -q` | “There are also database-level read-only controls and a query time budget. The tests include attempts to bypass the parser. This version supports SQLite; production authorization is a separate requirement.” |

## Oturum 1 — Sorgunun yolunu öğren (60–90 dakika)

1. `python demo.py` çalıştır. Soru, SQL ve sonuç arasındaki farkı kendi sözlerinle anlat.
2. `RuleTranslator.PATTERNS` içindeki lead-source sorgusunu oku. GROUP BY olmadan ne değişir?
3. `validate_sql` fonksiyonuna bak: metin eşleştirmesi yerine sözdizimi ağacı neden gerekli?
4. `test_guard_rejects_quoted_hidden_table` testini aç. İzin verilen tablo ile gizli tablo arasındaki farkı açıkla.
5. Kodu kapatıp akışı 60 saniyede anlat. Ezberden “LLM eğittim” deme: bu projede hazır modeli çağıran isteğe bağlı bir çevirici var.

## Oturum 2 — Küçük değişiklik yap ve savun (60–90 dakika)

Görev: “average deal size” sorusu için `AVG(amount)` kuralı ekle.
Önce örnek veritabanından beklenen ortalamayı bağımsız SQL ile hesapla; sonra yeni
sorunun aynı sonucu verdiğini doğrulayan test yaz. Testin önce başarısız olduğunu gör.
Ardından kuralı ekle, testleri çalıştır ve iki dakikalık ekran kaydı yap.
Bu alıştırma bilerek çözülmeden bırakıldı; senin bağımsız katkını gösterecek.

## Mülakatta cevaplayabilmen gerekenler

- **Regex neden yetmedi?** Tırnaklı tablo adları ve iç içe sorgular gözden kaçabiliyordu. AST fiziksel tabloları ayırıyor; SQLite authorizer ikinci kontrol.
- **LIMIT neden güvenlik garantisi değil?** Sonuç sayısını sınırlar. Bir aggregate veya cross join yine çok hesap yapabilir; progress handler bunu keser.
- **API anahtarı olmadan ne oluyor?** Sadece desteklenen soru kalıpları çevriliyor. Bu genel doğal dil anlayışı değil.
- **Prompt saldırısı neden doğrudan SQL çalıştıramıyor?** Üretilen SQL her durumda aynı doğrulama ve veritabanı sınırlarından geçiyor. İş mantığı doğruluğu ayrıca değerlendirilir.
- **Gelir toplamının doğru olduğunu nasıl kontrol edersin?** Örnek veri üzerinde bağımsız aggregate ve bilinen beklenen değerle test edersin.
- **Gerçek müşteriye ilk ne sorarsın?** Tablo şeması, izin verilen veriler, KPI tanımı, örnek sorular ve beklenen cevaplar.

CV cümlesini ancak projeyi açıklayıp küçük bir değişikliği kendin yaptıktan sonra rahatlıkla kullan:
“Developed a SQLite analytics demo with parsed SQL validation, database-level read-only controls and regression tests.”
