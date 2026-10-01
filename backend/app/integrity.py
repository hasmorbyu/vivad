"""SHA-256 integrity helpers and a tamper-evident append-only hash chain.

SHA-256 verifies integrity and detects change. It does not by itself establish chain of
custody or provenance, and the UI and reports must not claim otherwise. No case data or
evidence is ever written to a public ledger; only hashes are eligible for anchoring.
"""
import hashlib
import json
from pathlib import Path


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_json(payload) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def chain_hash(prev_hash: str, payload) -> str:
    """Hash of (previous record hash || canonical payload). Links a record to all before it."""
    return sha256_text((prev_hash or "") + canonical_json(payload))
