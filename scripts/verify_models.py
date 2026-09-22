#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_models.py — three-layer validation for downloaded ComfyUI models

Layer 1  BYTE SIZE    compare the file on disk against the size the remote declares
Layer 2  STRUCTURE    parse the safetensors header and check every tensor's data_offsets
Layer 3  DTYPE        list the distinct dtypes actually present, to prove what the file is

Layer 1 catches truncation. Layer 2 catches a file that has the right length but a broken
tensor table. Layer 3 is the only honest way to answer "is this really NVFP4?" — filenames
lie, dtype sets do not.

Expected sizes are probed from the remote and cached to expected_sizes.json, so repeat runs
are fast. Use --refresh after adding new models.

Usage
-----
    python scripts/verify_models.py --root /path/to/ComfyUI/models
    python scripts/verify_models.py --refresh        # re-probe every size
    python scripts/verify_models.py -v               # list every file
"""
from __future__ import annotations

import argparse
import json
import os
import struct
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import dl_models as D
except ImportError:
    print("error: dl_models.py must sit next to this script (it owns the manifest)")
    sys.exit(2)

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "expected_sizes.json")

# safetensors dtype codes -> human names
DTYPES = {
    "F64": "F64", "F32": "F32", "F16": "F16", "BF16": "BF16",
    "I64": "I64", "I32": "I32", "I16": "I16", "I8": "I8",
    "U8": "U8", "BOOL": "BOOL", "F8_E5M2": "F8_E5M2", "F8_E4M3": "F8_E4M3",
}
# Tensor keys that prove a file really carries NVFP4 weights.
NVFP4_KEYS = ("weight_scale", "weight_scale_2", "input_scale", "pre_quant_scale",
              "TensorCoreNVFP4Layout")


def load_cache() -> dict:
    if os.path.isfile(CACHE):
        try:
            with open(CACHE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_cache(d: dict) -> None:
    with open(CACHE, "w", encoding="utf-8", newline="\n") as f:
        json.dump(d, f, indent=1, sort_keys=True)


def structure(path: str):
    """Parse a safetensors header. Returns (n_tensors, {dtype: count}, nvfp4_key_hits)."""
    with open(path, "rb") as f:
        raw = f.read(8)
        if len(raw) < 8:
            return None, None, 0
        n = struct.unpack("<Q", raw)[0]
        if n <= 0 or n > 200 * 1024 * 1024:
            return None, None, 0
        header = f.read(n)
        file_size = os.path.getsize(path)
    try:
        meta = json.loads(header.decode("utf-8"))
    except Exception:
        return None, None, 0

    counts, bad = {}, 0
    for key, info in meta.items():
        if key == "__metadata__" or not isinstance(info, dict):
            continue
        dt = info.get("dtype")
        counts[dt] = counts.get(dt, 0) + 1
        offs = info.get("data_offsets")
        if not (isinstance(offs, list) and len(offs) == 2
                and offs[0] < offs[1] <= file_size):
            bad += 1
    if bad:
        return None, None, 0
    hits = sum(1 for k in meta if any(t in k for t in NVFP4_KEYS))
    return len(counts.values()) and sum(counts.values()), counts, hits


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate downloaded ComfyUI models")
    ap.add_argument("--root", default=D.DEFAULT_ROOT)
    ap.add_argument("--refresh", action="store_true", help="re-probe all remote sizes")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    cache = {} if args.refresh else load_cache()
    todo = [(p, g, s, n, r, rp) for (p, g, s, n, r, rp) in D.MANIFEST
            if f"{r}/{rp}" not in cache or args.refresh]
    if todo:
        print("probing %d remote size(s) ..." % len(todo))

        def probe(item):
            _p, _g, _s, n, repo, rel = item
            size, _urls = D.probe_size(repo, rel)
            return f"{repo}/{rel}", size

        with ThreadPoolExecutor(max_workers=8) as ex:
            for f in as_completed([ex.submit(probe, it) for it in todo]):
                key, size = f.result()
                if size:
                    cache[key] = size
        save_cache(cache)

    rows = []
    ok_n = missing_n = corrupt_n = 0
    ok_bytes = expected_total = 0

    for priority, group, sub, name, repo, rel in D.MANIFEST:
        dest = os.path.join(args.root, sub, name)
        expected = cache.get(f"{repo}/{rel}")
        if expected:
            expected_total += expected
        if not os.path.isfile(dest):
            rows.append({"name": name, "status": "MISSING", "size": 0,
                         "label": "-", "group": group})
            missing_n += 1
            continue

        actual = os.path.getsize(dest)
        if expected is None:
            status = "NO-EXPECTED"
        elif actual != expected:
            status = "SIZE-MISMATCH"
        else:
            status = "OK"

        _count, dtypes, hits = structure(dest)
        if status == "OK" and dtypes is None:
            status = "BAD-STRUCTURE"

        label = ",".join(sorted(d for d in (dtypes or {}) if d)) or "-"
        if hits:
            label += "  [NVFP4 keys:%d]" % hits
        if status == "OK":
            ok_n += 1
            ok_bytes += actual
        else:
            corrupt_n += 1
        rows.append({"name": name, "status": status, "size": actual,
                     "label": label, "group": group})

    print()
    print("%-60s %-14s %11s  %s" % ("file", "status", "size", "structure"))
    print("-" * 116)
    for r in rows:
        if not args.verbose and r["status"] == "OK":
            continue
        print("%-60s %-14s %8.2f GB  %s"
              % (r["name"][:60], r["status"], r["size"] / 1e9, r["label"]))
    print("-" * 116)

    pct = (100.0 * ok_bytes / expected_total) if expected_total else 0.0
    print("complete %d / %d   %.1f GB verified (%.1f%% of expected %.1f GB)"
          % (ok_n, len(rows), ok_bytes / 1e9, pct, expected_total / 1e9))
    print("missing %d   corrupt %d   not-checked %d"
          % (missing_n, sum(1 for r in rows if r["status"] in ("SIZE-MISMATCH", "BAD-STRUCTURE")),
             sum(1 for r in rows if r["status"] == "NO-EXPECTED")))
    return 1 if (missing_n or corrupt_n) else 0


if __name__ == "__main__":
    sys.exit(main())
