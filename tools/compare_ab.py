#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compare_ab.py — two-image PSNR comparison for quantization A/B work

Reports:
  * global PSNR and mean absolute error
  * per-pixel difference distribution (percentiles)
  * a 4x4 tile PSNR grid, to tell a distributed difference (trajectory divergence) apart
    from a localised one (a structural artifact)
  * a side-by-side PNG and an 8x-amplified difference heatmap

IMPORTANT — read this before drawing conclusions
------------------------------------------------
A low PSNR between two generative-model outputs does NOT mean one of them is worse. Diffusion
sampling is chaotic: a difference in the 4th decimal place of a matmul amplifies into a
completely different composition after a handful of steps. Two different samples of the same
prompt routinely measure 12-17 dB.

Global PSNR is therefore only meaningful in the presence of a NOISE BASELINE. Always run the
same pair with a different random seed, and compare. If the cross-quantization PSNR is *higher*
than the seed PSNR, quantization is not a factor. See tools/ab_metrics.py for that workflow.

Requires: numpy, Pillow

Usage
-----
    python tools/compare_ab.py a.png b.png --outdir out/ --label-a INT8 --label-b NVFP4
"""
from __future__ import annotations

import argparse
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def load(path: str):
    im = Image.open(path).convert("RGB")
    return im, np.asarray(im).astype(np.float64)


def psnr(a: np.ndarray, b: np.ndarray, peak: float = 255.0) -> float:
    mse = float(np.mean((a - b) ** 2))
    return float("inf") if mse == 0 else 20 * np.log10(peak) - 10 * np.log10(mse)


def font(size: int):
    for name in ("/System/Library/Fonts/Supplemental/Arial.ttf",
                 "C:/Windows/Fonts/arial.ttf",
                 "C:/Windows/Fonts/msyh.ttc",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.isfile(name):
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                pass
    return ImageFont.load_default()


def main() -> int:
    ap = argparse.ArgumentParser(description="PSNR comparison of two generated images")
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--label-a", default="A")
    ap.add_argument("--label-b", default="B")
    ap.add_argument("--tiles", type=int, default=4)
    ap.add_argument("--amplify", type=float, default=8.0)
    args = ap.parse_args()

    ia, na = load(args.a)
    ib, nb = load(args.b)
    if ia.size != ib.size:
        print("size differs (%s vs %s) - resizing B" % (ia.size, ib.size))
        ib = ib.resize(ia.size, Image.LANCZOS)
        nb = np.asarray(ib).astype(np.float64)

    diff = np.abs(na - nb)
    dmax = diff.max(axis=2)
    mae = float(diff.mean())          # mean over every channel
    mmax = float(dmax.mean())         # mean of the per-pixel worst channel

    print("%s : %s  %s" % (args.label_a, args.a, ia.size))
    print("%s : %s  %s" % (args.label_b, args.b, ib.size))
    print("-" * 62)
    print("global PSNR          : %.2f dB" % psnr(na, nb))
    print("mean abs error       : %.3f / 255  (%.3f%%)" % (mae, mae / 255 * 100))
    print("mean worst-channel   : %.3f / 255  (%.3f%%)" % (mmax, mmax / 255 * 100))
    print("max channel diff     : %.0f" % dmax.max())
    print("percentiles of the per-pixel worst-channel difference:")
    for p in (50, 90, 95, 99, 99.9):
        print("  P%-6s : %.1f" % (p, np.percentile(dmax, p)))

    n = args.tiles
    h, w = dmax.shape
    print("-" * 62)
    print("%dx%d tile PSNR (dB)" % (n, n))
    for i in range(n):
        row = []
        for j in range(n):
            ys, ye = h * i // n, h * (i + 1) // n
            xs, xe = w * j // n, w * (j + 1) // n
            row.append("%6.1f" % psnr(na[ys:ye, xs:xe], nb[ys:ye, xs:xe]))
        print("  " + " ".join(row))
    print("  (a grid with no near-zero tile means the difference is distributed, "
          "which is what sampling divergence looks like)")

    os.makedirs(args.outdir, exist_ok=True)
    gap = 12
    side = Image.new("RGB", (ia.width * 2 + gap, ia.height), (24, 24, 28))
    side.paste(ia, (0, 0))
    side.paste(ib, (ia.width + gap, 0))
    d = ImageDraw.Draw(side)
    f = font(max(14, ia.width // 48))
    d.text((10, 8), args.label_a, fill=(255, 255, 255), font=f)
    d.text((ia.width + gap + 10, 8), args.label_b, fill=(255, 255, 255), font=f)
    p_side = os.path.join(args.outdir, "ab_sidebyside.png")
    side.save(p_side)

    heat = np.clip(dmax * args.amplify, 0, 255).astype(np.uint8)
    p_heat = os.path.join(args.outdir, "ab_diff_x%d.png" % int(args.amplify))
    Image.fromarray(heat).convert("L").convert("RGB").save(p_heat)

    print("-" * 62)
    print("wrote %s" % p_side)
    print("wrote %s  (difference amplified x%g)" % (p_heat, args.amplify))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
