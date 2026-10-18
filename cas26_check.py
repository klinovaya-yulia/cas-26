#!/usr/bin/env python3
"""
CAS-26 reference checker · эталонный проверяльщик CAS-26
Version 0.1.1

Usage:
    python3 cas26_check.py <folder> [--sample 30] [--seed N] [--threshold 0.9]
                                    [--timeout 20] [--offline] [--out cas26-report.json]

The folder must contain passport.json and the index file(s) it declares.
Writes cas26-report.json next to the passport. Exit code 0 = passed, 1 = failed,
2 = could not run (missing passport, unreadable files).

No dependencies beyond the Python 3 standard library.
"""

import argparse
import csv
import datetime as dt
import hashlib
import html
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request

STANDARD = "CAS-26"
STANDARD_VERSION = "0.1"
USER_AGENT = "CAS-26-checker/0.1.1 (+https://github.com/klinovaya-yulia/cas-26)"


# ---------- helpers ----------

def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_date(s):
    """Accepts YYYY-MM-DD, DD.MM.YYYY, YYYY-MM, YYYY. Returns date or None."""
    if not s:
        return None
    s = str(s).strip()
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)  # ISO date anywhere in the value
    if m:
        try:
            return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", s)  # DD.MM.YYYY
    if m:
        try:
            return dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            return None
    m = re.fullmatch(r"(\d{4})(?:-(\d{2}))?", s)  # YYYY or YYYY-MM
    if m:
        try:
            return dt.date(int(m.group(1)), int(m.group(2) or 1), 1)
        except ValueError:
            return None
    return None


_TAG_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)
_HTML_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_QUOTES = {
    "«": '"', "»": '"', "“": '"', "”": '"', "„": '"', "‘": "'", "’": "'",
    "…": "...", "—": "-", "–": "-", " ": " ",
}


def normalize(text):
    text = html.unescape(text or "")
    for k, v in _QUOTES.items():
        text = text.replace(k, v)
    text = text.lower()
    text = _WS_RE.sub(" ", text)
    return text.strip()


def page_text(raw_bytes, content_type=""):
    enc = "utf-8"
    m = re.search(r"charset=([\w-]+)", content_type or "", re.I)
    if m:
        enc = m.group(1)
    try:
        text = raw_bytes.decode(enc, errors="replace")
    except LookupError:
        text = raw_bytes.decode("utf-8", errors="replace")
    text = _TAG_RE.sub(" ", text)
    text = _HTML_RE.sub(" ", text)
    return normalize(text)


def fetch(url, timeout):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        ctype = resp.headers.get("Content-Type", "")
        body = resp.read(5 * 1024 * 1024)  # 5 MB is enough to find a 10-word quote
        return resp.status, ctype, body


def quote_found(quote, text):
    q = normalize(quote).strip('"\'. ')
    if not q:
        return False, "empty quote"
    if q in text:
        return True, ""
    # tolerate a punctuation-only difference: compare word sequences
    qw = re.findall(r"\w+", q)
    tw = " ".join(re.findall(r"\w+", text))
    if qw and " ".join(qw) in tw:
        return True, ""
    return False, "quote not found"


# ---------- checks ----------

def check_integrity(folder, passport, report):
    ok = True
    files = passport.get("files") or []
    if not files:
        report["integrity"]["errors"].append("passport.files is empty")
        return False, None
    main_path = None
    for f in files:
        name = f.get("name", "")
        path = os.path.join(folder, name)
        entry = {"name": name}
        if not os.path.isfile(path):
            entry["error"] = "file missing"
            ok = False
        else:
            size = os.path.getsize(path)
            digest = sha256_of(path)
            entry["bytes"] = size
            entry["sha256"] = digest
            if f.get("bytes") not in (None, 0, "") and int(f["bytes"]) != size:
                entry["error"] = "bytes mismatch (passport %s, actual %s)" % (f["bytes"], size)
                ok = False
            if f.get("sha256") and f["sha256"].lower() != digest:
                entry["error"] = "sha256 mismatch"
                ok = False
            if main_path is None and name.lower().endswith(".csv"):
                main_path = path
        report["integrity"]["files"].append(entry)
    return ok, main_path


def load_rows(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return reader.fieldnames or [], rows


def check_structure(passport, fieldnames, rows, report):
    ok = True
    prov = passport.get("provenance_columns") or {}
    needed = [prov.get(k) for k in ("id", "source_url", "source_quote", "source_date") if prov.get(k)]
    for col in needed:
        if col not in fieldnames:
            report["integrity"]["errors"].append("provenance column missing: %s" % col)
            ok = False
    schema_cols = [c.get("column") for c in (passport.get("schema") or []) if c.get("column")]
    if schema_cols:
        missing = [c for c in schema_cols if c not in fieldnames]
        extra = [c for c in fieldnames if c not in schema_cols]
        if missing:
            report["integrity"]["errors"].append("schema columns missing in index: %s" % ", ".join(missing))
            ok = False
        if extra:
            report["integrity"]["warnings"].append("columns in index not in schema: %s" % ", ".join(extra))
    cov = passport.get("coverage") or {}
    if cov.get("rows") not in (None, 0, "") and int(cov["rows"]) != len(rows):
        report["integrity"]["errors"].append("row count mismatch (passport %s, actual %s)" % (cov["rows"], len(rows)))
        ok = False
    id_col = prov.get("id", "id")
    if id_col in fieldnames:
        ids = [r.get(id_col, "") for r in rows]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            report["integrity"]["errors"].append("duplicate ids: %s" % ", ".join(dupes[:20]))
            ok = False
        if any(not i for i in ids):
            report["integrity"]["errors"].append("empty ids present")
            ok = False
    report["integrity"]["rows"] = len(rows)
    report["integrity"]["columns"] = len(fieldnames)
    return ok


def check_coverage(passport, fieldnames, rows, report):
    cov = passport.get("coverage") or {}
    col = cov.get("column")
    units = cov.get("units") or []
    if not col or col not in fieldnames or not units:
        report["coverage"]["skipped"] = "no coverage column/units declared"
        return True
    filled = [r for r in rows if not is_empty_row(passport, r)]
    present = {r.get(col, "").strip() for r in filled}
    missing = [u for u in units if u not in present]
    report["coverage"]["declared"] = len(units)
    report["coverage"]["present"] = len([u for u in units if u in present])
    report["coverage"]["empty_rows"] = len(rows) - len(filled)
    if missing:
        report["coverage"]["missing"] = missing
    neg_units = [n.get("unit") for n in (passport.get("negative") or []) if n.get("unit")]
    leaked = [u for u in neg_units if u in present]
    if leaked:
        report["coverage"]["warnings"] = ["units declared empty but present with data: %s" % ", ".join(leaked)]
    return not missing


def is_empty_row(passport, row):
    """A row that records 'nothing found' for a unit, as declared by coverage.empty_marker
    ({"column": ..., "value": ...}). Such rows are negative knowledge, not sample candidates."""
    marker = (passport.get("coverage") or {}).get("empty_marker") or {}
    col, val = marker.get("column"), marker.get("value")
    return bool(col) and row.get(col, "").strip() == str(val)


def check_sample(passport, rows, args, report):
    prov = passport.get("provenance_columns") or {}
    id_col = prov.get("id", "id")
    url_col = prov.get("source_url", "source_url")
    quote_col = prov.get("source_quote", "source_quote")
    date_col = prov.get("source_date", "source_date")
    checked_at = parse_date(passport.get("checked_at"))

    conflicts = {c.get("id"): c for c in (passport.get("conflicts") or []) if c.get("id")}

    candidates = [r for r in rows if not is_empty_row(passport, r)]
    n = min(args.sample, len(candidates))
    rng = random.Random(args.seed)
    sample = rng.sample(candidates, n) if n < len(candidates) else list(candidates)
    report["sample"]["size"] = n
    report["sample"]["seed"] = args.seed
    report["sample"]["population"] = len(candidates)

    confirmed = 0
    failures = []
    for r in sample:
        rid = r.get(id_col, "")
        url = (r.get(url_col) or "").strip()
        quote = r.get(quote_col) or ""
        sdate = parse_date(r.get(date_col))
        reasons = []

        if not url:
            reasons.append("no source url")
        if not quote.strip():
            reasons.append("no quote")
        if sdate is None:
            reasons.append("source date unreadable")
        elif checked_at and sdate > checked_at:
            reasons.append("source date after checked_at")

        if url and quote.strip() and not args.offline:
            urls = [url]
            if rid in conflicts:
                urls = [u for u in (conflicts[rid].get("a"), conflicts[rid].get("b")) if u] or urls
            for u in urls:
                try:
                    status, ctype, body = fetch(u, args.timeout)
                    text = page_text(body, ctype)
                    found, why = quote_found(quote, text)
                    if not found:
                        reasons.append("%s: %s" % (u, why))
                except urllib.error.HTTPError as e:
                    reasons.append("%s: HTTP %s" % (u, e.code))
                except Exception as e:  # noqa: BLE001
                    reasons.append("%s: %s" % (u, type(e).__name__))
                time.sleep(args.delay)
        elif args.offline:
            reasons.append("offline: source not fetched")

        if reasons:
            failures.append({"id": rid, "url": url, "reasons": reasons})
        else:
            confirmed += 1

    report["sample"]["confirmed"] = confirmed
    report["sample"]["failures"] = failures
    ratio = (confirmed / n) if n else 0.0
    report["sample"]["ratio"] = round(ratio, 3)
    return ratio >= args.threshold


def check_freshness(passport, report):
    checked_at = parse_date(passport.get("checked_at"))
    every = passport.get("recheck_every_days")
    today = dt.date.today()
    if not checked_at or not every:
        report["freshness"]["error"] = "checked_at or recheck_every_days missing"
        return False
    valid_until = checked_at + dt.timedelta(days=int(every))
    report["freshness"]["checked_at"] = checked_at.isoformat()
    report["freshness"]["valid_until"] = valid_until.isoformat()
    report["freshness"]["fresh"] = today <= valid_until
    return today <= valid_until


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(description="CAS-26 reference checker")
    ap.add_argument("folder")
    ap.add_argument("--sample", type=int, default=30)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--threshold", type=float, default=0.9)
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between requests")
    ap.add_argument("--offline", action="store_true", help="skip network; sample rows will not be confirmed")
    ap.add_argument("--out", default="cas26-report.json")
    args = ap.parse_args()
    if args.seed is None:
        args.seed = random.SystemRandom().randrange(1, 2**31)

    folder = os.path.abspath(args.folder)
    ppath = os.path.join(folder, "passport.json")
    if not os.path.isfile(ppath):
        print("no passport.json in", folder, file=sys.stderr)
        return 2
    with open(ppath, encoding="utf-8") as f:
        passport = json.load(f)

    report = {
        "standard": STANDARD,
        "standard_version": STANDARD_VERSION,
        "checker": "cas26_check.py 0.1.1",
        "index": passport.get("title"),
        "index_version": passport.get("version"),
        "checked_on": dt.date.today().isoformat(),
        "integrity": {"files": [], "errors": [], "warnings": []},
        "coverage": {},
        "sample": {},
        "freshness": {},
        "result": None,
    }

    required = ("publisher", "title", "version", "built_at", "files", "provenance_columns",
                "checked_at", "recheck_every_days", "limits")
    missing = [k for k in required if k not in passport]
    if missing:
        report["integrity"]["errors"].append("passport fields missing: %s" % ", ".join(missing))

    int_ok, main_path = check_integrity(folder, passport, report)
    if main_path is None:
        report["integrity"]["errors"].append("no csv file declared")
        report["result"] = "failed"
        _write(folder, args.out, report)
        return 1

    try:
        fieldnames, rows = load_rows(main_path)
    except Exception as e:  # noqa: BLE001
        report["integrity"]["errors"].append("cannot read index: %s" % e)
        report["result"] = "failed"
        _write(folder, args.out, report)
        return 2

    struct_ok = check_structure(passport, fieldnames, rows, report)
    cov_ok = check_coverage(passport, fieldnames, rows, report)
    fresh_ok = check_freshness(passport, report)
    sample_ok = check_sample(passport, rows, args, report)

    passed = int_ok and struct_ok and cov_ok and fresh_ok and sample_ok and not missing
    report["result"] = "passed" if passed else "failed"
    report["main_sha256"] = sha256_of(main_path)
    _write(folder, args.out, report)

    s = report["sample"]
    print("%s · %s v%s · sample %s/%s confirmed · fresh: %s · %s" % (
        STANDARD, report["index"], report["index_version"],
        s.get("confirmed"), s.get("size"), report["freshness"].get("fresh"), report["result"].upper()))
    for e in report["integrity"]["errors"]:
        print("  error:", e)
    for fl in s.get("failures", [])[:50]:
        print("  not confirmed:", fl["id"], "—", "; ".join(fl["reasons"]))
    return 0 if passed else 1


def _write(folder, out, report):
    path = os.path.join(folder, out)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("report:", path)


if __name__ == "__main__":
    sys.exit(main())
