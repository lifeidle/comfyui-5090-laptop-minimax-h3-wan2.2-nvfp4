#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_charts.py — generate every SVG chart used by the README and the site.

Style contract (matches the existing chart set in this account)
--------------------------------------------------------------
* 920 x H canvas, rounded white card background  -> renders identically on
  GitHub light theme, GitHub dark theme, and a standalone browser tab.
* NO <style>, NO CSS custom properties, NO media queries. Every visual
  attribute is an explicit inline attribute. This is deliberate: an SVG
  loaded through GitHub's image proxy does not reliably inherit page theme,
  and CSS variables silently resolve to nothing -> washed-out labels.
* Palette
      #0f172a text      #64748b muted     #94a3b8 dim
      #e2e8f0 grid      #f8fafc subtle    #ffffff card
      #d97706 amber     #2563eb blue      #059669 emerald   #dc2626 red
* Fonts: -apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif

Usage
-----
    python tools/make_charts.py
"""
import os

W = 920
PAD = 24
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

FF = "-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
TXT, MUT, DIM, GRID, SUBTLE, CARD = "#0f172a", "#64748b", "#94a3b8", "#e2e8f0", "#f8fafc", "#ffffff"
AMBER, BLUE, EMERALD, RED = "#d97706", "#2563eb", "#059669", "#dc2626"


def t(x, y, s, size=12, fill=MUT, weight=None, anchor=None, ff=FF):
    a = f' text-anchor="{anchor}"' if anchor else ""
    w = f' font-weight="{weight}"' if weight else ""
    return (f'<text x="{x}" y="{y}" font-family="{ff}" font-size="{size}" '
            f'fill="{fill}"{w}{a}>{s}</text>')


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def rect(x, y, w, h, fill, rx=5, opacity=None, stroke=None, sw=1, dash=None):
    o = f' opacity="{opacity}"' if opacity is not None else ""
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w,0):.1f}" height="{max(h,0):.1f}" '
            f'rx="{rx}" fill="{fill}"{o}{s}{d}/>')


def line(x1, y1, x2, y2, stroke=GRID, sw=1, dash=None, cap=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    c = f' stroke-linecap="{cap}"' if cap else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{stroke}" stroke-width="{sw}"{d}{c}/>')


def save(name, parts, w, h, title):
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
             f'width="{w}" height="{h}" role="img" aria-label="{esc(title)}">',
             rect(0, 0, w, h, CARD, rx=12)] + parts + ['</svg>']
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(parts) + "\n")
    print(f"  {name:38s} {w}x{h}")


def header(title, subtitle=None):
    p = [t(PAD, 34, esc(title), 19, TXT, 700)]
    if subtitle:
        p.append(t(PAD, 56, esc(subtitle), 12.5, MUT))
    return p


# ==================================================================== chart 1
def chart_download_sources():
    h = 316
    rows = [("www.modelscope.cn", 11, 27, 22, EMERALD, "4 parallel connections saturate ~80 MB/s"),
            ("hf-mirror.com", 2, 4, 3, AMBER, "has a silent-stall failure mode: drips KB every 30 s"),
            ("huggingface.co", 1.6, 2.2, 1.9, DIM, "reachable but never the fastest")]
    p = header("Download source throughput",
               "Measured 2026-09-22, single connection, 125.6 GB moved in total")
    p.append(t(PAD, 84, "Nominal speed, with the observed range shown as a lighter tail",
               13.5, TXT, 600))
    x0, x1 = 300, 800
    y0, rowh, vmax = 106, 56, 30
    for gv in range(0, vmax + 1, 5):
        gx = x0 + (x1 - x0) * gv / vmax
        p.append(line(gx, y0 - 12, gx, y0 + len(rows) * rowh - 26))
        p.append(t(gx, y0 + len(rows) * rowh - 12, gv, 11.5, DIM, anchor="middle"))
    p.append(t((x0 + x1) / 2, y0 + len(rows) * rowh + 6, "MB/s", 11.5, MUT, anchor="middle"))
    for i, (name, lo, hi, nom, col, note) in enumerate(rows):
        y = y0 + i * rowh
        p.append(t(PAD, y + 8, esc(name), 14, TXT, 600))
        p.append(t(PAD, y + 25, esc(note), 11, MUT))
        xn = x0 + (x1 - x0) * nom / vmax
        xh = x0 + (x1 - x0) * hi / vmax
        p.append(rect(x0, y - 4, xn - x0, 22, col, rx=5))
        p.append(rect(xn, y + 3, xh - xn, 8, col, rx=4, opacity=0.3))
        p.append(t(xh + 8, y + 13, f"{lo}-{hi}", 14, TXT, 700))
    p.append(line(PAD, h - 42, W - PAD, h - 42, GRID))
    p.append(t(PAD, h - 24, "modelscope is the primary source. hf-mirror and huggingface exist only as fallbacks.",
               11.5, TXT, 600))
    p.append(t(PAD, h - 8, "Note the 7x and 12x penalties below it - a multi-source downloader is not optional.",
               11, MUT))
    save("chart1-download-sources.svg", p, W, h, "Download source throughput")


# ==================================================================== chart 2
def chart_model_footprint():
    vram = 24.0
    items = [("MiniMax H3 DiT (int8 + ConvRot)", 20.97, RED, True),
             ("HunyuanVideo 1.5 (720p / 480p)", 16.65, DIM, True),
             ("Qwen3-VL 32B - MiniMax H3 encoder", 15.69, BLUE, True),
             ("Z-Image-Turbo + bf16 encoder", 8.04 + 0.34, AMBER, False),
             ("Z-Image-Turbo int8 + fp4 encoder", 6.20 + 3.48, DIM, False),
             ("Z-Image-Turbo nvfp4 + fp4 encoder", 4.51 + 3.48, EMERALD, False),
             ("FLUX.2 Klein 4B fp8", 4.07, EMERALD, False)]
    h = 300
    p = header("Does a single weight file fit in 24 GB?",
               "Anything crossing the red line cannot stay resident on its own - ComfyUI must offload it every step")
    x0, x1 = 320, 820
    y0, rowh, vmax = 106, 26, 24
    xv = x0 + (x1 - x0) * vram / vmax
    for gv in [0, 4, 8, 12, 16, 20, 24]:
        gx = x0 + (x1 - x0) * gv / vmax
        p.append(line(gx, y0 - 12, gx, y0 + len(items) * rowh - 4))
        p.append(t(gx, y0 + len(items) * rowh + 10, gv, 11, DIM, anchor="middle"))
    p.append(t((x0 + x1) / 2, y0 + len(items) * rowh + 26, "GB", 11, MUT, anchor="middle"))
    p.append(line(xv, y0 - 20, xv, y0 + len(items) * rowh - 4, RED, 2, dash="5 3"))
    p.append(t(xv + 5, y0 - 24, "24 GB", 11, RED, 700))
    for i, (name, gb, col, over) in enumerate(items):
        y = y0 + i * rowh
        p.append(t(PAD, y + 11, esc(name), 12, TXT))
        wpx = (x1 - x0) * min(gb, vmax) / vmax
        p.append(rect(x0, y, wpx, 16, col, rx=4, opacity=0.45 if over else 1))
        p.append(t(x0 + wpx + 7, y + 12, f"{gb:.2f}" + ("  offload required" if over else ""),
                   11.5, TXT if not over else MUT, 700 if not over else None))
    save("chart2-model-footprint.svg", p, W, h, "Weight file size against 24 GB of VRAM")


# ==================================================================== chart 3
def chart_quant_ab():
    h = 336
    rows = [("cross-quant", "NVFP4 vs INT8, same seed", 16.84, EMERALD, True),
            ("seed noise", "NVFP4, different seed", 12.45, DIM, False),
            ("seed noise", "INT8, different seed", 12.10, DIM, False)]
    p = header("Controlled A/B: is the quantization loss real?",
               "Z-Image-Turbo. Identical encoder, prompt and 1024x1024 / 8 steps - only the DiT quantization changes.")
    x0, x1 = 268, 812
    y0, rowh, vmax = 116, 56, 20
    for gv in range(0, vmax + 1, 5):
        gx = x0 + (x1 - x0) * gv / vmax
        p.append(line(gx, y0 - 16, gx, y0 + len(rows) * rowh - 14))
        p.append(t(gx, y0 + len(rows) * rowh + 2, gv, 11.5, DIM, anchor="middle"))
    p.append(t((x0 + x1) / 2, y0 + len(rows) * rowh + 20,
               "PSNR (dB) - higher means the two images are more alike", 11.5, MUT, anchor="middle"))
    lo = x0 + (x1 - x0) * 12.10 / vmax
    hi = x0 + (x1 - x0) * 12.45 / vmax
    p.append(rect(lo, y0 - 16, hi - lo, len(rows) * rowh - 14, DIM, rx=0, opacity=0.16))
    p.append(t((lo + hi) / 2, y0 - 24, "seed-noise floor", 11, MUT, anchor="middle"))
    for i, (tag, note, v, col, hi_) in enumerate(rows):
        y = y0 + i * rowh
        p.append(t(PAD, y + 9, tag, 14, TXT, 600))
        p.append(t(PAD, y + 26, note, 11, MUT))
        wpx = (x1 - x0) * v / vmax
        p.append(rect(x0, y - 5, wpx, 24, col, rx=5, opacity=1 if hi_ else 0.45))
        p.append(t(x0 + wpx + 9, y + 13, f"{v:.2f}", 15, TXT, 700))
    p.append(line(PAD, h - 52, W - PAD, h - 52, GRID))
    p.append(t(PAD, h - 32,
               "Same quantization + same seed re-run measured PSNR = infinity (byte-identical).",
               11.5, TXT, 600))
    p.append(t(PAD, h - 15,
               "So the cross-quantization gap is 100% attributable to quantization - and it is still smaller than a seed change.",
               11.5, MUT))
    save("chart3-quant-ab-psnr.svg", p, W, h, "Controlled A/B PSNR, quantization versus seed noise")


# ==================================================================== chart 4
def chart_decision_tree():
    h = 400

    def node(x, y, w, hh, title, sub, col):
        o = [rect(x, y, w, hh, col, rx=8, opacity=0.10),
             rect(x, y, w, hh, "none", rx=8, stroke=col, sw=1.5),
             t(x + w / 2, y + 23, esc(title), 13.5, TXT, 600, anchor="middle")]
        if sub:
            o.append(t(x + w / 2, y + 41, esc(sub), 11, MUT, anchor="middle"))
        return o

    def arrow(x1, y1, x2, y2, label=None, lx=None, ly=None):
        o = [f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{DIM}" stroke-width="1.4" '
             f'marker-end="url(#a)"/>']
        if label:
            o.append(t(lx if lx else (x1 + x2) / 2 + 7, ly if ly else (y1 + y2) / 2 + 4,
                       label, 11, MUT))
        return o

    p = header("Which quantization should you pick?",
               "Two questions settle almost every case. This is the exact path used in this project.")
    p.append(f'<defs><marker id="a" markerWidth="9" markerHeight="9" refX="7.5" refY="4.5" '
             f'orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="{DIM}"/></marker></defs>')

    # A: fits?   B: blackwell?   C: nvfp4   D: int8   E: overflow   F: gguf
    p += node(340, 78, 250, 52, "Fits inside 24 GB?", "weights + encoder + VAE", BLUE)
    p += node(340, 176, 250, 52, "GPU is Blackwell?", "sm_120 / sm_121", BLUE)
    p += node(672, 176, 224, 52, "NVFP4", "native 4-bit tensor cores", EMERALD)
    p += node(340, 274, 250, 52, "INT8 + ConvRot", "runs the BF16 path, any GPU", AMBER)
    p += node(28, 78, 232, 52, "Weights overflow", "must be offloaded or split", RED)
    p += node(28, 274, 232, 52, "W4A16 (GGUF / NF4)", "saves VRAM, is NOT faster", RED)

    p += arrow(340, 104, 262, 104, "no", 292, 98)
    p += arrow(465, 130, 465, 176, "yes", 473, 156)
    p += arrow(590, 202, 670, 202, "yes", 624, 196)
    p += arrow(465, 228, 465, 274, "no", 473, 254)
    p += arrow(144, 130, 144, 274)

    p.append(line(PAD, 348, W - PAD, 348, GRID, dash="4 4"))
    p.append(t(PAD, 370, "W4A16 saves memory but speeds nothing up. W4A4 / NVFP4 save memory AND go faster.",
               12, TXT, 600))
    p.append(t(PAD, 390, "Never trust the filename - NVFP4 is identified by tensor keys "
                         "(weight_scale, weight_scale_2, input_scale, pre_quant_scale + TensorCoreNVFP4Layout).",
               11, MUT))
    save("chart4-quant-decision-tree.svg", p, W, h, "Quantization selection decision tree")


# ==================================================================== chart 5
def chart_benchmarks():
    import math
    items = [("MiniMax H3 - text to video + audio", "1344x768, 124 frames, 5.17 s clip with stereo audio", 519.06, RED),
             ("HunyuanVideo 1.5 - 480p, 4 steps", "848x480, 121 frames, 5.04 s clip", 117.0, BLUE),
             ("MiniMax H3 - smoke test", "768x448, 56 frames", 76.31, BLUE),
             ("FLUX.2 Klein 4B - fp8 image edit", "single 1024x1024 image", 42.32, AMBER),
             ("Z-Image-Turbo - int8", "1024x1024, 8 steps", 17.70, DIM),
             ("Z-Image-Turbo - nvfp4", "1024x1024, 8 steps", 13.80, EMERALD)]
    h = 330
    p = header("Measured generation time (log scale)",
               "RTX 5090 Laptop 24 GB, ComfyUI 0.37.0 - timing read from execution_start / execution_success, never wall clock")
    x0, x1 = 340, 812
    lo, hi = math.log10(10), math.log10(600)
    y0, rowh = 106, 32

    def sx(v):
        return x0 + (x1 - x0) * (math.log10(v) - lo) / (hi - lo)

    for gv in [10, 20, 30, 50, 100, 200, 300, 500]:
        gx = sx(gv)
        p.append(line(gx, y0 - 12, gx, y0 + len(items) * rowh - 6))
        p.append(t(gx, y0 + len(items) * rowh + 8, gv, 11, DIM, anchor="middle"))
    p.append(t((x0 + x1) / 2, y0 + len(items) * rowh + 26, "seconds", 11, MUT, anchor="middle"))
    for i, (name, cfg, v, col) in enumerate(items):
        y = y0 + i * rowh
        p.append(t(PAD, y + 11, esc(name), 12.5, TXT, 600))
        p.append(t(PAD, y + 26, esc(cfg), 10.5, MUT))
        wpx = sx(v) - x0
        p.append(rect(x0, y - 1, wpx, 18, col, rx=4))
        p.append(t(x0 + wpx + 8, y + 13, f"{v:.1f} s", 13, TXT, 700))
    save("chart5-model-benchmark.svg", p, W, h, "Measured generation time per workflow")


# ==================================================================== chart 6
def chart_nvfp4_gain():
    h = 250
    p = header("What NVFP4 actually buys you",
               "Z-Image-Turbo, same encoder, same 1024x1024 / 8 steps, same seed")
    groups = [("Generation time", "seconds", 17.70, 13.80, 22.0),
              ("DiT weight file", "GB", 6.20, 4.51, 27.3)]
    x0, barw = 268, 380
    rowh = 78
    for i, (name, unit, a, b, gain) in enumerate(groups):
        y = 92 + i * rowh
        p.append(t(PAD, y - 2, esc(name), 13.5, TXT, 600))
        wa = barw * a / max(a, b)
        wb = barw * b / max(a, b)
        p.append(t(PAD, y + 18, "INT8 + ConvRot", 11.5, MUT))
        p.append(rect(x0, y + 6, wa, 18, DIM, rx=4, opacity=0.5))
        p.append(t(x0 + wa + 8, y + 20, f"{a:.2f} {unit}", 13, TXT, 700))
        p.append(t(PAD, y + 42, "NVFP4", 11.5, MUT))
        p.append(rect(x0, y + 30, wb, 18, EMERALD, rx=4))
        p.append(t(x0 + wb + 8, y + 44, f"{b:.2f} {unit}", 13, TXT, 700))
        p.append(t(x0 + barw + 46, y + 32, f"{gain:.0f}%", 20, EMERALD, 700))
        p.append(t(x0 + barw + 46 + 52, y + 32, "better", 11, MUT))
    p.append(t(PAD, h - 14,
               "Both time and size improve, and the measured quality gap stays below the seed-noise floor (see chart 3).",
               11, MUT))
    save("chart6-nvfp4-gain.svg", p, W, h, "NVFP4 gains in speed and size")


if __name__ == "__main__":
    print("generating charts ->", OUT)
    for fn in (chart_download_sources, chart_model_footprint, chart_quant_ab,
               chart_decision_tree, chart_benchmarks, chart_nvfp4_gain):
        fn()
    print("done")
