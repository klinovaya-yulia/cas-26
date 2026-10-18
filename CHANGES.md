# CAS-26 — changes

## 0.2 (in preparation, decided 2026-10-18)

**Sampling: three draws, pooled.** 0.1 fixes the sample seed in the standard (26). That is a hole: a publisher knows in advance which thirty rows will be drawn and can polish exactly those. 0.2 replaces the single draw with three draws of thirty rows under three different seeds; at least one seed is chosen by the verifier at check time and never published beforehand. All seeds go into the report afterwards, so the check stays reproducible. The three draws are pooled into one sample of ninety; the index passes if at least 81 of 90 rows are confirmed. An index with fewer than ninety rows is checked in full, threshold nine in ten.

Why pooled rather than "all three must pass separately" (hypergeometric, index of 256 rows): one draw of thirty passes an index with 15 % bad rows 31 % of the time and one with 20 % bad rows 11 % of the time. Requiring three separate passes rejects a decent index with 5 % bad rows 15 % of the time. Pooling to 81 of 90 passes a 5 %-bad index in 99.8 % of cases, a 15 %-bad one in 7 %, a 20 %-bad one in 0.2 %. Index size barely matters above a few hundred rows (100 to 10 000 rows give the same picture); the number of draws is set by the error one accepts, not by the row count.

**Unreachable is not "quote not found".** A source that does not answer the verifier (timeout, 403, 5xx, connection error) says nothing about the index. 0.2 lists such rows separately, replaces each by the next candidate under the same seed, caps replacements at one fifth of the sample, and writes every replacement into the report. A row whose page opens and does not contain the quote remains unconfirmed.

**Signature verification.** The reference verifier address is a smart wallet on Base; signatures are checked through ERC-1271 (`isValidSignature(bytes32, bytes)`, EIP-191 hash of the mark string), not by recovering a key. The signed string is the short mark line, not the mark JSON.

## 0.1 — 2026-10-18

First publication. Marks issued under 0.1 remain valid until their `valid_until`.
