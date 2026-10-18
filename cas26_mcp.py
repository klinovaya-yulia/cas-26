#!/usr/bin/env python3
"""
CAS-26 MCP server · MCP-сервер CAS-26
Version 0.1

Tools:
  check_index(base_url, sample, seed)   — run the CAS-26 procedure against an index published at base_url
                                          (a folder URL that contains passport.json and the index files)
  lookup_mark(sha256)                   — find a CAS-26 mark in the public registry by index file hash
  verify_mark(mark)                     — verify a mark's wallet signature on Base (ERC-1271)
  spec()                                — the standard, short form

Run:
  python3 cas26_mcp.py                  — stdio (for local clients)
  python3 cas26_mcp.py --http 8026      — streamable HTTP on port 8026 (for remote clients), path /mcp

Dependencies: mcp (pip install mcp), pycryptodome (for keccak256). cas26_check.py must sit next to this file.
"""

import hashlib
import json
import os
import re
import sys
import tempfile
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cas26_check as C  # noqa: E402

from mcp.server.fastmcp import FastMCP  # noqa: E402

REGISTRY_URL = "https://raw.githubusercontent.com/klinovaya-yulia/cas-26/main/registry.json"
SPEC_URL = "https://github.com/klinovaya-yulia/cas-26/blob/main/SPEC.md"
BASE_RPC = os.environ.get("CAS26_BASE_RPC", "https://mainnet.base.org")
ERC1271_MAGIC = "0x1626ba7e"

mcp = FastMCP("cas26", instructions=(
    "CAS-26 — standard for index passports and verification (provenance-bearing datasets). "
    "Use check_index to run the procedure on a published index, lookup_mark to find a mark by sha256, "
    "verify_mark to verify a mark's signature on Base."
))


def _get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "CAS-26-mcp/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


@mcp.tool()
def spec() -> str:
    """What CAS-26 is, in short, and where the full text lives."""
    return (
        "CAS-26: an index is a provenance-bearing dataset — every row carries source_url, a verbatim quote, "
        "a date and a confidence. A passport.json next to the index declares publisher, files with sha256, "
        "schema, coverage, method, negative knowledge, conflicts, dead entries, freshness and limits. "
        "Verification: integrity (hashes, rows, ids), coverage, a seeded random sample of rows whose source "
        "pages must contain the quote, threshold 9/10, freshness within recheck_every_days. "
        "A mark (cas26.json) ties a sha256 to a verifier, a date, a sample result and a signature; "
        "signatures by Base wallets are verified with ERC-1271 isValidSignature. Full text: " + SPEC_URL
    )


@mcp.tool()
def check_index(base_url: str, sample: int = 30, seed: int = 26, timeout: int = 20) -> dict:
    """Run the CAS-26 procedure on an index published at base_url (a folder URL containing passport.json
    and the index files it declares). Returns the cas26-report.json content. Network access to the
    index's source URLs is required; this can take a few minutes for 30 rows."""
    base = base_url.rstrip("/") + "/"
    passport = json.loads(_get(base + "passport.json").decode("utf-8"))
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "passport.json"), "w", encoding="utf-8") as f:
            json.dump(passport, f, ensure_ascii=False)
        for fe in passport.get("files") or []:
            name = fe.get("name", "")
            if not name or "/" in name or name.startswith("."):
                return {"error": "unsafe file name in passport: %r" % name}
            with open(os.path.join(d, name), "wb") as f:
                f.write(_get(base + name, timeout=120))

        class Args:  # mirror of the CLI arguments
            pass
        a = Args()
        a.sample, a.seed, a.threshold, a.timeout, a.delay, a.offline, a.out = sample, seed, 0.9, timeout, 1.0, False, "cas26-report.json"

        report = {
            "standard": C.STANDARD, "standard_version": C.STANDARD_VERSION, "checker": "cas26_mcp 0.1 / cas26_check 0.1.1",
            "index": passport.get("title"), "index_version": passport.get("version"),
            "checked_on": C.dt.date.today().isoformat(), "source": base,
            "integrity": {"files": [], "errors": [], "warnings": []}, "coverage": {}, "sample": {}, "freshness": {}, "result": None,
        }
        required = ("publisher", "title", "version", "built_at", "files", "provenance_columns",
                    "checked_at", "recheck_every_days", "limits")
        missing = [k for k in required if k not in passport]
        if missing:
            report["integrity"]["errors"].append("passport fields missing: %s" % ", ".join(missing))
        int_ok, main_path = C.check_integrity(d, passport, report)
        if main_path is None:
            report["integrity"]["errors"].append("no csv file declared")
            report["result"] = "failed"
            return report
        fieldnames, rows = C.load_rows(main_path)
        struct_ok = C.check_structure(passport, fieldnames, rows, report)
        cov_ok = C.check_coverage(passport, fieldnames, rows, report)
        fresh_ok = C.check_freshness(passport, report)
        sample_ok = C.check_sample(passport, rows, a, report)
        report["result"] = "passed" if (int_ok and struct_ok and cov_ok and fresh_ok and sample_ok and not missing) else "failed"
        report["main_sha256"] = C.sha256_of(main_path)
        return report


@mcp.tool()
def lookup_mark(sha256: str) -> dict:
    """Find CAS-26 marks in the public registry by the sha256 of the main index file."""
    sha = sha256.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", sha):
        return {"error": "sha256 must be 64 hex characters"}
    reg = json.loads(_get(REGISTRY_URL).decode("utf-8"))
    hits = [m for m in reg.get("marks", []) if m.get("sha256", "").lower() == sha]
    return {"sha256": sha, "found": len(hits), "marks": hits, "registry": REGISTRY_URL}


def _keccak256(data: bytes) -> bytes:
    from Crypto.Hash import keccak
    h = keccak.new(digest_bits=256)
    h.update(data)
    return h.digest()


def mark_message(mark: dict) -> str:
    """The short human-readable line that a CAS-26 verifier signs (personal_sign)."""
    sha = mark.get("sha256", "")
    return "CAS-26 | %s %s | sha256:%s…%s | %s | %s/%s" % (
        mark.get("index", ""), mark.get("index_version", ""), sha[:8], sha[-4:],
        mark.get("verified_at", ""), mark.get("confirmed", ""), mark.get("sample", ""))


@mcp.tool()
def verify_mark(mark: dict) -> dict:
    """Verify a CAS-26 mark's signature. The verifier field must be a Base wallet address (0x…);
    the signed text is the mark's short line (see mark_message). Verification is an ERC-1271
    isValidSignature call to the verifier's address on Base; works for smart wallets (Coinbase/Base Account)."""
    verifier = (mark.get("verifier") or "").strip()
    sig = (mark.get("signature") or "").strip()
    if not re.fullmatch(r"0x[0-9a-fA-F]{40}", verifier):
        return {"valid": None, "error": "verifier is not a Base address; only wallet signatures are verifiable here"}
    if not sig.startswith("0x"):
        return {"valid": None, "error": "signature missing or not hex"}
    msg = mark_message(mark).encode("utf-8")
    digest = _keccak256(b"\x19Ethereum Signed Message:\n" + str(len(msg)).encode() + msg)
    sigb = bytes.fromhex(sig[2:])
    data = ("0x1626ba7e" + digest.hex() + (64).to_bytes(32, "big").hex()
            + len(sigb).to_bytes(32, "big").hex() + sigb.hex() + "00" * ((32 - len(sigb) % 32) % 32))
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_call",
                       "params": [{"to": verifier, "data": data}, "latest"]}).encode()
    req = urllib.request.Request(BASE_RPC, data=body, headers={"Content-Type": "application/json", "User-Agent": "CAS-26-mcp/0.1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        res = json.loads(r.read().decode())
    result = (res.get("result") or "")[:10]
    return {"valid": result == ERC1271_MAGIC, "message": msg.decode(), "verifier": verifier, "rpc_result": result,
            "error": res.get("error")}


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--http":
        mcp.settings.host = "0.0.0.0"
        mcp.settings.port = int(sys.argv[2])
        mcp.run(transport="streamable-http")
    else:
        mcp.run()
