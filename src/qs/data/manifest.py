"""Run manifests: the fingerprint that makes "same run" a testable claim.

A backtest number is only meaningful together with the exact bytes that
produced it.  The manifest records

* sha256 of every input file,
* sha256 of the config,
* a short combined fingerprint,

so ``make run`` twice must produce the same fingerprint AND the same returns.
If they differ, something non-deterministic (or non-reproducible) crept in.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_obj(obj) -> str:
    payload = json.dumps(obj, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def build_manifest(cfg, root: str | Path = ".") -> dict:
    root = Path(root)
    files = {
        "prices": root / cfg.data.prices,
        "fundamentals": root / cfg.data.fundamentals,
        "universe": root / cfg.data.universe,
        "config": root / "config" / "strategy.yaml",
    }
    digests = {name: sha256_file(p) for name, p in files.items() if p.exists()}
    combined = sha256_obj(digests)
    return {
        "fingerprint": combined[:16],
        "inputs": digests,
        "config": cfg.to_dict(),
    }


def write_manifest(manifest: dict, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, default=str))


def returns_fingerprint(equity: pd.Series, decimals: int = 10) -> str:
    """Hash of the equity curve itself — the thing that must not change."""
    rounded = [round(float(x), decimals) for x in equity.to_numpy()]
    return sha256_obj(rounded)[:16]
