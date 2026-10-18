#!/usr/bin/env python3
"""CAS-26 pre-check 0.1 — for catalogs that have no passport.

Takes a list of rows with at least a URL and a name, draws a seeded sample,
opens each URL and records: reachable, name found on the page, last-modified.
Also reports how far the catalog is from a CAS-26 passport (which fields exist).
This is NOT the CAS-26 check: without quotes nothing can be confirmed, only
reachability and naming. Output: cas26-precheck.json next to the input.
"""
import csv, json, random, re, sys, time, hashlib, datetime, urllib.request, urllib.error, html, io

UA = "CAS-26-precheck/0.1 (+https://github.com/klinovaya-yulia/cas-26)"

def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*;q=0.8"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read(600_000)
            ct = r.headers.get("Content-Type", "")
            enc = "utf-8"
            m = re.search(r"charset=([\w-]+)", ct)
            if m: enc = m.group(1)
            try: text = raw.decode(enc, "replace")
            except LookupError: text = raw.decode("utf-8", "replace")
            return {"status": r.status, "final_url": r.geturl(), "last_modified": r.headers.get("Last-Modified"),
                    "content_type": ct.split(";")[0], "text": text, "seconds": round(time.time()-t0, 1)}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "final_url": url, "error": f"HTTP {e.code}", "seconds": round(time.time()-t0, 1)}
    except Exception as e:
        return {"status": None, "final_url": url, "error": type(e).__name__, "seconds": round(time.time()-t0, 1)}

def visible_text(doc):
    doc = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", doc)
    doc = re.sub(r"(?s)<[^>]+>", " ", doc)
    return html.unescape(re.sub(r"\s+", " ", doc)).lower()

def name_found(name, text):
    toks = [t for t in re.findall(r"[a-z0-9À-ɏЀ-ӿ]+", name.lower()) if len(t) >= 3]
    if not toks: return None
    hit = sum(1 for t in toks if t in text)
    return hit >= max(1, (len(toks) + 1) // 2)

def load_rows(src, path):
    rows = []
    if src == "public-apis":
        for line in open(path, encoding="utf-8"):
            m = re.match(r"\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|\s*([^|]*)\|", line)
            if m: rows.append({"name": m.group(1).strip(), "url": m.group(2).strip(), "note": m.group(3).strip()})
    elif src == "universities":
        for u in json.load(open(path, encoding="utf-8")):
            if u.get("web_pages"): rows.append({"name": u["name"], "url": u["web_pages"][0], "note": u.get("country", "")})
    elif src == "awesome-public-datasets":  # RST: * |OK_ICON| `Name - description <url>`_ [`Meta <...>`_]
        for line in open(path, encoding="utf-8"):
            m = re.match(r"\s*\*\s*(?:\|(\w+)\|\s*)?`(.+?)\s+<(https?://[^>]+)>`_", line)
            if m:
                name = m.group(2).split(" - ")[0].strip()
                rows.append({"name": name, "url": m.group(3).strip(), "note": (m.group(1) or "")})
    elif src == "csv":
        for r in csv.DictReader(open(path, encoding="utf-8")):
            rows.append({"name": r.get("name", ""), "url": r.get("url", ""), "note": r.get("note", "")})
    return rows

def main():
    if len(sys.argv) < 4:
        print("usage: cas26_precheck.py <source: public-apis|universities|awesome-public-datasets|csv> <file> <title> [--sample 30] [--seed 26] [--delay 1]"); sys.exit(2)
    src, path, title = sys.argv[1], sys.argv[2], sys.argv[3]
    def opt(k, d):
        return type(d)(sys.argv[sys.argv.index(k)+1]) if k in sys.argv else d
    n, seed, delay = opt("--sample", 30), opt("--seed", 26), opt("--delay", 1.0)
    raw = open(path, "rb").read()
    rows = load_rows(src, path)
    rows = [r for r in rows if r["url"].startswith("http")]
    rnd = random.Random(seed)
    sample = rnd.sample(rows, min(n, len(rows)))
    results = []
    for i, r in enumerate(sample, 1):
        f = fetch(r["url"])
        res = {"name": r["name"], "url": r["url"], "status": f["status"], "final_url": f["final_url"],
               "seconds": f["seconds"], "last_modified": f.get("last_modified"), "error": f.get("error")}
        if f.get("text") is not None and f["status"] and 200 <= f["status"] < 300:
            res["reachable"] = True
            res["name_found"] = name_found(r["name"], visible_text(f["text"]))
        else:
            res["reachable"] = False; res["name_found"] = None
        results.append(res)
        print(f"{i:>2}/{len(sample)} {'ok ' if res['reachable'] else 'NO '} {'name+' if res['name_found'] else 'name-' if res['name_found'] is False else '     '} {res['status'] or res['error']:<12} {r['name'][:38]:<38} {r['url'][:60]}", flush=True)
        time.sleep(delay)
    reach = sum(1 for x in results if x["reachable"]); named = sum(1 for x in results if x["name_found"])
    report = {
        "standard": "CAS-26", "tool": "cas26_precheck.py 0.1", "kind": "pre-check (no passport)",
        "catalog": title, "source_file": path, "source_sha256": hashlib.sha256(raw).hexdigest(), "source_bytes": len(raw),
        "checked_on": datetime.date.today().isoformat(), "rows_with_url": len(rows), "sample": len(sample), "seed": seed,
        "reachable": reach, "name_found": named,
        "unreachable_by_reason": {}, "passport_distance": {
            "publisher": "known (repository owner)", "files_sha256": "computed here, not declared by publisher",
            "question_row_is_schema": "absent", "coverage": "absent", "method": "absent",
            "provenance_columns": "url only; no quote, no source date, no confidence, no checker",
            "negative_knowledge": "absent", "conflicts_dead": "absent", "checked_at_recheck": "absent", "limits": "absent",
            "verdict": "cannot be checked under CAS-26 until a passport with quotes and dates exists"},
        "results": results}
    for x in results:
        if not x["reachable"]:
            k = x["error"] or f"HTTP {x['status']}"; report["unreachable_by_reason"][k] = report["unreachable_by_reason"].get(k, 0) + 1
    out = path.rsplit("/", 1)[0] + "/cas26-precheck.json" if "/" in path else "cas26-precheck.json"
    json.dump(report, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n{title}: rows {len(rows)} · sample {len(sample)} (seed {seed}) · reachable {reach}/{len(sample)} · name found {named}/{len(sample)} · unreachable {report['unreachable_by_reason']}\nreport: {out}")

if __name__ == "__main__":
    main()
