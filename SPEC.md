# CAS-26 — a standard for index passports and index verification

Version 0.1 · 18 October 2026 · draft, open to change through new versions.
Russian text: `SPEC.ru.md`. From this version on, the English text is the reference; the Russian one is a translation.

## Why

Data for agents is sold on marketplaces where the buyer cannot tell collected from invented until they have paid. A domain certificate solved the same problem for websites: not "trust us" but "check for yourself". CAS-26 does the same for indexes. It does not judge whether the data is good. It gives a way to check that the data was collected the way it claims, and that the check can be repeated.

## What an index is

An index is a table built around one question, in which every row has provenance: where it was taken from, when it was checked, with what confidence. An index differs from a dataset in three things: it knows what it does not contain (negative knowledge), it remembers where sources disagree (conflicts), and it has a date after which it must not be trusted without re-checking (freshness). Any dataset can become an index by getting a passport.

In one phrase: an index is a provenance-bearing dataset. The word "dataset" is acceptable as a synonym for search purposes.

## The index passport

The passport is a machine-readable file next to the index. File name: `passport.json`, in the same folder as the index. Template: `passport.template.json`. Fields:

**Who and when.** `publisher` — who published it; `title` — the name; `version` — version number; `built_at` — build date; `files` — the list of index files, each with name, size in bytes and `sha256`; `external_timestamp` — the address of an external timestamp (a commit, a post, a registry entry) that the publisher does not control.

**What is inside.** `question` — in one phrase, the question the index was built for; `row_is` — what one row is; `schema` — the list of columns, each with a name and a one-phrase meaning; `coverage` — what is covered (for country indexes, the list of country codes), how many rows, how many coverage units are empty.

**How it was built.** `method` — the method in words: search order, languages, tools, stages; `confidence_levels` — what each confidence level in the index means, with the condition for granting the highest level.

**Row provenance.** `provenance_columns` — which index columns carry provenance: source address, quote, source date, search language, confidence, who checked. The passport declares the column names; the values themselves live in the index rows. The quote from the source is verbatim and no longer than ten words, so that it can be found on the page.

**Negative knowledge.** `negative` — coverage units where a search was made and nothing was found, with the list of attempts made. An entry "empty" without a list of attempts does not count as negative knowledge.

**Conflicts and dead entries.** `conflicts` — rows where two sources disagree, with both addresses; `dead` — what has closed, with the closing date and the source.

**Freshness.** `checked_at` — the date the index was last checked as a whole; `recheck_every_days` — the declared re-check interval; `changelog` — what changed between versions, one line per version.

**What we do not promise.** `limits` — in words, what the passport does not guarantee. For an index of publishing platforms this is, for example: that a platform will accept your article; that the rules have not changed since the check date.

**Where to get it.** `license`, `price`, `where` — addresses: page, llms.txt, MCP, payment method.

A passport missing any of the fields under "who and when", "row provenance", "freshness" or "what we do not promise" is not a passport. The other fields may be empty, but must be present and explicitly empty.

## The verification procedure

Anyone can run the check — the publisher, a buyer, a third party, an agent. The procedure is the same for all, and that is the point: a mark does not require trusting the verifier, because it can be repeated. Reference implementation: `cas26_check.py`.

**Integrity.** The index files exist; their size and sha256 match the passport. The number of rows and columns matches what is declared. Row identifiers are unique. The provenance columns declared in the passport are present.

**Coverage.** The coverage units from the passport are present in the index; the units listed as negative knowledge are absent from the index or marked as empty.

**Sample.** The verifier picks random rows — no fewer than thirty, or all rows if there are fewer. The randomness is fixed: the seed is written to the report so the sample can be reproduced. For each row: the source address is opened; the quote is found on the page; the source date is not later than the check date. A row counts as confirmed when all three conditions hold. A row marked as a conflict is confirmed if both addresses open.

**Threshold.** The index passes if at least nine rows out of every ten in the sample are confirmed. Unconfirmed rows are listed in the report by name, with the reason: address did not open, quote not found, date does not match.

**Freshness.** If more than `recheck_every_days` have passed since `checked_at`, the index fails regardless of the sample.

The check report is the file `cas26-report.json`: date, seed, sample size, number confirmed, the list of unconfirmed rows with reasons, the verdict. The report is public.

## The mark

The mark is the record of a passed check. The file `cas26.json` next to the passport:

```json
{
  "standard": "CAS-26",
  "standard_version": "0.1",
  "index": "<title>",
  "index_version": "<version>",
  "sha256": "<hash of the main index file>",
  "verified_at": "2026-10-18",
  "verifier": "<name or address>",
  "sample": 30,
  "confirmed": 29,
  "report": "<address of cas26-report.json>",
  "valid_until": "<verified_at + recheck_every_days>",
  "signature": "<signature>"
}
```

A mark refers to a specific hash. A new version of the index means a new mark. A mark expires at `valid_until`.

**Signature.** The verifier signs the mark with a key that can be checked publicly, without taking the verifier's word for it. The first supported method is a message signature by a wallet on the Base network: the verifier is identified by its address, the canonical mark string without the `signature` field is signed, and the signature can be checked by any tool that verifies Ethereum signatures. Other signature methods are allowed if the verification method is stated.

A publisher's mark (self-check) and a third party's mark look the same; the only difference is the `verifier` field. The buyer decides whose mark to trust — and may trust no one and run the procedure themselves.

## What CAS-26 does not do

It does not assess the quality, completeness or usefulness of the data. It does not guarantee that the sources are truthful — only that they exist and say what the index quotes. It does not replace a license and does not grant permission to use.

## How to join

Put a passport next to your index. Run the procedure — with your own program or the reference one. Put the report and the mark next to it. State in the listing on the marketplace: "CAS-26: checked <date>, <address of the mark>". The standard is open, without fees or registration. The first checked indexes are the standard publisher's own, under the same rules as for everyone else.

## Versions of the standard

0.1 — first publication, 18 October 2026. Changes come through new versions with a changelog; published versions are not edited retroactively. Marks issued under older versions remain valid until their `valid_until`.
