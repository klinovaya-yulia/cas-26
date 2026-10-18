# CAS-26 pre-check — catalogs without a passport (2026-10-18)

A pre-check is not the CAS-26 check. Without quotes and dates nothing can be confirmed; the pre-check only asks what a buyer can learn in five minutes: do the links open, is the named thing on the page, and how far is the catalog from a passport. Tool: `cas26_precheck.py 0.1`, sample 30, seed 26, run from cas26-1 (Frankfurt).

| catalog | rows with URL | reachable | name on page | unreachable, by reason |
|---|---|---|---|---|
| public-apis (GitHub) | 2185 | 28/30 | 24/30 | 2 dead domains |
| university-domains-list (Hipo, GitHub) | 10268 | 17/30 | 16/30 | 6 domains gone from DNS, 2 no answer, 2 TLS after redirect, 1 HTTP 403, 2 tool errors |
| awesome-public-datasets (GitHub) | 1074 | 29/30 | 23/30 | 1 HTTP 403 |

Passport distance, all three: publisher known; file hash computable but not declared; no question, schema, coverage, method; provenance = URL only (no quote, no source date, no confidence, no checker); no negative knowledge, no conflicts, no dead list, no checked_at. awesome-public-datasets is the closest: it marks dead links itself (|OK_ICON| / |FIXME_ICON|) and keeps a meta file per entry — in our sample its own marks agreed with the pre-check on 28 of 30.

Reports and logs are in the folders. Errors named "tool errors" (UnicodeError, RemoteDisconnected) are limits of the 0.1 tool, not findings about the catalog.

---

Предпроверка — не проверка CAS-26: без цитат и дат подтвердить нечего. Она отвечает только на то, что покупатель хочет знать за пять минут: открываются ли адреса, есть ли на странице названное и сколько шагов до паспорта. Три известных каталога с GitHub, по 30 случайных строк (сид 26), с cas26-1. Самый тревожный — список университетов мира, на котором построена половина форм «выбери свой вуз»: из тридцати адресов открылись семнадцать, у шести доменов больше нет записи в DNS. Самый близкий к паспорту — awesome-public-datasets: он сам помечает мёртвые ссылки и держит мета-файл на каждую запись.
