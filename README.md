# CAS-26

**Стандарт паспорта и проверки индексов.**
**A standard for index passports and verification.**

Индекс — таблица, собранная под один вопрос, в которой у каждой строки есть происхождение: откуда взята, когда проверена, с какой уверенностью. CAS-26 не оценивает, хороши ли данные. Он даёт способ проверить, что данные собраны так, как заявлено, и что проверку может повторить любой — покупатель, площадка, агент.

An index is a provenance-bearing dataset: a table built around one question, where every row carries its source, its check date and its confidence. CAS-26 does not judge whether the data is good. It gives anyone — a buyer, a marketplace, an agent — a way to verify that the data was collected as declared, and to repeat that verification.

## Что здесь · What is here

- `SPEC.md` — the standard, v0.1 (English, reference text) · `SPEC.ru.md` — текст стандарта по-русски (перевод)
- `passport.template.json` — шаблон паспорта индекса · index passport template
- `cas26_check.py` — эталонный проверяльщик · reference checker (Python 3, no dependencies)
- `examples/` — первые проверенные индексы · first verified indexes (coming)

## Как проверить индекс · How to check an index

```
python3 cas26_check.py <folder with index and passport.json>
```

Проверяльщик сверяет хеши, число строк и колонок, уникальность идентификаторов, берёт случайную выборку строк и ходит по адресам источников, ищет цитаты и сверяет даты. Результат — `cas26-report.json` рядом с паспортом.

The checker verifies hashes, row and column counts, id uniqueness, takes a random sample of rows, opens each source URL, looks for the quoted text and checks the dates. It writes `cas26-report.json` next to the passport.

## Статус · Status

Версия 0.1, черновик. Открыт, без платы и регистрации.
Version 0.1, draft. Open, free, no registration.
