# Площадки для бесплатной публикации статей по странам мира — v3.1

Первый прогон CAS-26 по индексу его же авторов. **Проверка не пройдена:** выборка 20 из 30 при пороге 9 из 10 (18.10.2026, cas26-1, seed 26). Целостность, покрытие и свежесть — в порядке.

Здесь лежат паспорт индекса и отчёт проверяльщика. Сам файл индекса (sha256 в паспорте) будет опубликован с той версией, которая проверку пройдёт.

Причины провала: у части строк вместо цитаты стоит заглушка «not verified» (наследие машинной перепроверки); часть источников не ответила серверу (403/500/таймаут); одна цитата — заголовок страницы вместо фразы о правилах. Версия 3.2 — после правки строк.

---

First CAS-26 run on the authors' own index. **Check failed:** 20 of 30 sampled rows confirmed against a 9-of-10 threshold (2026-10-18, cas26-1, seed 26). Integrity, coverage and freshness passed. Passport and checker report are here; the index file itself (sha256 in the passport) will be published with the version that passes.
