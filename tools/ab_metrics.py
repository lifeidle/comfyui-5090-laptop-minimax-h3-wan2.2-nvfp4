#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ab_metrics.py — the four-arm controlled A/B for quantization, in one command

Why four arms
-------------
A naive comparison runs two variants and reports a PSNR. That number is uninterpretable,
because diffusion sampling is chaotic — two samples of the same model and prompt already
differ enormously. You need a baseline to compare against.

          arm        variable                       purpose
          ---------  -----------------------------  --------------------------------
          det        none (re-run)                  determinism check
          seed       random seed, quantization A     noise floor
          cross      quantization only (fixed seed)  the thing being measured
          seedB      random seed, quantization B     noise floor

Decision rule
-------------
    cross similarity  >=  seed similarity   ->  quantization is not a factor
    cross similarity  <<  seed similarity   ->  quantization introduces real distortion

If the `det` arm is not infinity (byte-identical), the pipeline is not deterministic, and no
cross-quantization difference can be attributed to anything. Fix that first.

Requires: numpy, Pillow

Usage
-----
    python tools/ab_metrics.py \
        --int8-a  ctl_int8_00001_.png   --int8-rep ctl_int8_rep_00001_.png \
        --int8-b  ctl_int8_s2_00001_.png \
        --nvfp4-a ctl_nvfp4_00001_.png  --nvfp4-b  ctl_nvfp4_s2_00001_.png
"""
from __future__ import annotations

import argparse
import os

import numpy as np
from PIL import Image


def load(path: str):
    im = Image.open(path).convert("RGB")
    return np.asarray(im).astype(np.float64)


def psnr(a, b, peak=255.0):
    mse = float(np.mean((a - b) ** 2))
    return float("inf") if mse == 0 else 20 * np.log10(peak) - 10 * np.log10(mse)


# ---- quality proxies that survive trajectory divergence ----------------------
def sharpness(a):
    """Variance of a Laplacian response, on the luminance channel."""
    g = a.mean(axis=2)
    lap = (np.roll(g, 1, 0) + np.roll(g, -1, 0)
           + np.roll(g, 1, 1) + np.roll(g, -1, 1) - 4 * g)
    return float(lap[1:-1, 1:-1].var())


def entropy(a, bins=64):
    h, _ = np.histogram(a, bins=bins, range=(0, 255))
    p = h / h.sum()
    p = p[p > 0]
    return float(-(p * np.log2(p)).sum())


def hf_ratio(a):
    """High-frequency energy relative to overall contrast."""
    g = a.mean(axis=2)
    blur = (np.roll(g, 1, 0) + np.roll(g, -1, 0)
            + np.roll(g, 1, 1) + np.roll(g, -1, 1) + 4 * g) / 8.0
    return float(np.abs(g - blur)[2:-2, 2:-2].mean() / (g.std() + 1e-6))


def hist_l1(a, b, bins=64):
    total = 0.0
    for c in range(3):
        ha, _ = np.histogram(a[..., c], bins=bins, range=(0, 255), density=True)
        hb, _ = np.histogram(b[..., c], bins=bins, range=(0, 255), density=True)
        total += np.abs(ha - hb).sum()
    return float(total / 3)


def main() -> int:
    ap = argparse.ArgumentParser(description="Four-arm controlled quantization A/B")
    ap.add_argument("--int8-a", required=True)
    ap.add_argument("--int8-rep", help="same quantization, same seed, re-run (determinism check)")
    ap.add_argument("--int8-b", help="int8, different seed")
    ap.add_argument("--nvfp4-a", required=True)
    ap.add_argument("--nvfp4-b", help="nvfp4, different seed")
    args = ap.parse_args()

    paths = {
        "int8_A": args.int8_a, "int8_rep": args.int8_rep, "int8_B": args.int8_b,
        "nvfp4_A": args.nvfp4_a, "nvfp4_B": args.nvfp4_b,
    }
    img = {}
    for k, p in paths.items():
        if p:
            if not os.path.isfile(p):
                print("missing: %s (%s)" % (p, k))
                return 2
            img[k] = load(p)

    pairs = [
        ("det    same quant, same seed, re-run", "int8_rep", "int8_A"),
        ("seed   int8, different seed",          "int8_B",   "int8_A"),
        ("cross  NVFP4 vs INT8, same seed",      "nvfp4_A",  "int8_A"),
        ("seedB  NVFP4, different seed",         "nvfp4_B",  "nvfp4_A"),
    ]

    print("=" * 74)
    print("PSNR / mean absolute error")
    print("=" * 74)
    for label, x, y in pairs:
        if x in img and y in img:
            if img[x].shape != img[y].shape:
                print("%-40s size mismatch" % label)
                continue
            mae = float(np.abs(img[x] - img[y]).mean())
            print("%-40s PSNR %7.2f dB   MAE %5.2f/255 (%5.2f%%)"
                  % (label, psnr(img[x], img[y]), mae, mae / 255 * 100))
        else:
            print("%-40s (not provided)" % label)

    print()
    print("=" * 74)
    print("Quality proxies (robust to trajectory divergence)")
    print("=" * 74)
    print("%-10s %14s %9s %10s" % ("sample", "sharpness", "entropy", "hf ratio"))
    for k in ("int8_A", "int8_rep", "int8_B", "nvfp4_A", "nvfp4_B"):
        if k in img:
            a = img[k]
            print("%-10s %14.1f %9.3f %10.4f" % (k, sharpness(a), entropy(a), hf_ratio(a)))

    print()
    print("Colour histogram L1 distance (0 = identical distributions)")
    for label, x, y in pairs:
        if x in img and y in img and img[x].shape == img[y].shape:
            print("  %-40s %.4f" % (label, hist_l1(img[x], img[y])))

    print()
    print("-" * 74)
    print("Read it this way: if 'cross' scores HIGHER than both 'seed' arms, then changing the")
    print("quantization format perturbs the image less than changing the random seed does.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
