#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_charts.py — generate every SVG chart used by the READMEs and the site.

Two language variants are emitted so the Chinese document gets Chinese charts
and the English document gets English ones:

    assets/zh/chartN-*.svg   <- referenced by README.md
    assets/en/chartN-*.svg   <- referenced by README_EN.md

(a plain <img> cannot be swapped by CSS, so the localisation has to happen at
build time, in two files.)

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
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets")

FF = "-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
TXT, MUT, DIM, GRID, SUBTLE, CARD = "#0f172a", "#64748b", "#94a3b8", "#e2e8f0", "#f8fafc", "#ffffff"
AMBER, BLUE, EMERALD, RED = "#d97706", "#2563eb", "#059669", "#dc2626"

LANGS = ("zh", "en")


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


def save(lang, name, parts, w, h, title):
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
             f'width="{w}" height="{h}" role="img" aria-label="{esc(title)}">',
             rect(0, 0, w, h, CARD, rx=12)] + parts + ['</svg>']
    d = os.path.join(OUT, lang)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(parts) + "\n")
    print(f"  {lang}/{name:34s} {w}x{h}")


def header(title, subtitle=None):
    p = [t(PAD, 34, esc(title), 19, TXT, 700)]
    if subtitle:
        p.append(t(PAD, 56, esc(subtitle), 12.5, MUT))
    return p


# ==================================================================== strings
# Only prose is localised. Model names, file names, dtype names, CLI flags and
# numbers are language-neutral and stay identical in both variants.
S = {
    # ---------------------------------------------------------------- chart 1
    "c1_title": {"zh": "下载源吞吐实测",
                 "en": "Download source throughput"},
    "c1_sub": {"zh": "实测于 2026-09-22，单连接；累计搬运 125.6 GB",
               "en": "Measured 2026-09-22, single connection, 125.6 GB moved in total"},
    "c1_head": {"zh": "标称速度，浅色尾段为实测到的波动区间",
                "en": "Nominal speed, with the observed range shown as a lighter tail"},
    "c1_notes": {"zh": ["4 路并发可跑满 ~80 MB/s",
                        "存在静默挂死：每 30 秒滴几 KB",
                        "可达，但从不是最快的"],
                 "en": ["4 parallel connections saturate ~80 MB/s",
                        "has a silent-stall failure mode: drips KB every 30 s",
                        "reachable but never the fastest"]},
    "c1_f1": {"zh": "modelscope 是主源。hf-mirror 与 huggingface 只作为回退。",
              "en": "modelscope is the primary source. hf-mirror and huggingface exist only as fallbacks."},
    "c1_f2": {"zh": "注意下方 7 倍与 12 倍的差距 —— 多源下载器不是可选项。",
              "en": "Note the 7x and 12x penalties below it - a multi-source downloader is not optional."},

    # ---------------------------------------------------------------- chart 2
    "c2_title": {"zh": "单个权重文件能装进 24 GB 吗？",
                 "en": "Does a single weight file fit in 24 GB?"},
    "c2_sub": {"zh": "越过红线者无法单独常驻显存 —— ComfyUI 每一步都得把它 offload 出去",
               "en": "Anything crossing the red line cannot stay resident on its own - ComfyUI must offload it every step"},
    "c2_items": {"zh": ["MiniMax H3 DiT（int8 + ConvRot）",
                        "HunyuanVideo 1.5（720p / 480p）",
                        "Qwen3-VL 32B · MiniMax H3 编码器",
                        "Z-Image-Turbo + bf16 编码器",
                        "Z-Image-Turbo int8 + fp4 编码器",
                        "Z-Image-Turbo nvfp4 + fp4 编码器",
                        "FLUX.2 Klein 4B fp8"],
                 "en": ["MiniMax H3 DiT (int8 + ConvRot)",
                        "HunyuanVideo 1.5 (720p / 480p)",
                        "Qwen3-VL 32B - MiniMax H3 encoder",
                        "Z-Image-Turbo + bf16 encoder",
                        "Z-Image-Turbo int8 + fp4 encoder",
                        "Z-Image-Turbo nvfp4 + fp4 encoder",
                        "FLUX.2 Klein 4B fp8"]},
    "c2_off": {"zh": "需要 offload", "en": "offload required"},

    # ---------------------------------------------------------------- chart 3
    "c3_title": {"zh": "受控 A/B：量化的画质损失是真的吗？",
                 "en": "Controlled A/B: is the quantization loss real?"},
    "c3_sub": {"zh": "Z-Image-Turbo。同一编码器、同一提示词、同一 1024×1024 / 8 步配置 —— 只改 DiT 的量化格式。",
               "en": "Z-Image-Turbo. Identical encoder, prompt and 1024x1024 / 8 steps - only the DiT quantization changes."},
    "c3_tags": {"zh": ["跨量化", "种子噪声", "种子噪声"],
                "en": ["cross-quant", "seed noise", "seed noise"]},
    "c3_notes": {"zh": ["NVFP4 vs INT8，同种子", "NVFP4，换种子", "INT8，换种子"],
                 "en": ["NVFP4 vs INT8, same seed", "NVFP4, different seed", "INT8, different seed"]},
    "c3_axis": {"zh": "PSNR（dB）—— 越高表示两张图越相似",
                "en": "PSNR (dB) - higher means the two images are more alike"},
    "c3_floor": {"zh": "种子噪声地板", "en": "seed-noise floor"},
    "c3_f1": {"zh": "同量化 + 同种子重跑，实测 PSNR = ∞（逐字节完全一致）。",
              "en": "Same quantization + same seed re-run measured PSNR = infinity (byte-identical)."},
    "c3_f2": {"zh": "所以跨量化的差异 100% 可归因于量化 —— 而它仍然小于换一次种子的差异。",
              "en": "So the cross-quantization gap is 100% attributable to quantization - and it is still smaller than a seed change."},

    # ---------------------------------------------------------------- chart 4
    "c4_title": {"zh": "该选哪种量化？", "en": "Which quantization should you pick?"},
    "c4_sub": {"zh": "两个问题就能定下几乎全部情况。这正是本项目实际走过的路径。",
               "en": "Two questions settle almost every case. This is the exact path used in this project."},
    "c4_fit": {"zh": ["能装进 24 GB 吗？", "权重 + 编码器 + VAE"],
               "en": ["Fits inside 24 GB?", "weights + encoder + VAE"]},
    "c4_bw": {"zh": ["显卡是 Blackwell？", "sm_120 / sm_121"],
              "en": ["GPU is Blackwell?", "sm_120 / sm_121"]},
    "c4_nvfp4": {"zh": ["NVFP4", "原生 4-bit 张量核"],
                 "en": ["NVFP4", "native 4-bit tensor cores"]},
    "c4_int8": {"zh": ["INT8 + ConvRot", "走 BF16 路径，任何显卡都能跑"],
                "en": ["INT8 + ConvRot", "runs the BF16 path, any GPU"]},
    "c4_over": {"zh": ["权重溢出", "必须 offload 或拆分"],
                "en": ["Weights overflow", "must be offloaded or split"]},
    "c4_w4a16": {"zh": ["W4A16（GGUF / NF4）", "省显存，但不会更快"],
                 "en": ["W4A16 (GGUF / NF4)", "saves VRAM, is NOT faster"]},
    "c4_yes": {"zh": "是", "en": "yes"},
    "c4_no": {"zh": "否", "en": "no"},
    "c4_f1": {"zh": "W4A16 只省显存，不提速。W4A4 / NVFP4 既省显存、又更快。",
              "en": "W4A16 saves memory but speeds nothing up. W4A4 / NVFP4 save memory AND go faster."},
    "c4_f2": {"zh": "别信文件名 —— NVFP4 靠张量键识别（weight_scale、weight_scale_2、input_scale、pre_quant_scale + TensorCoreNVFP4Layout）。",
              "en": "Never trust the filename - NVFP4 is identified by tensor keys "
                    "(weight_scale, weight_scale_2, input_scale, pre_quant_scale + TensorCoreNVFP4Layout)."},

    # ---------------------------------------------------------------- chart 5
    "c5_title": {"zh": "各工作流实测耗时（对数坐标）",
                 "en": "Measured generation time (log scale)"},
    "c5_sub": {"zh": "RTX 5090 Laptop 24 GB，ComfyUI 0.37.0 —— 计时取自 execution_start / execution_success，绝不用墙钟时间",
               "en": "RTX 5090 Laptop 24 GB, ComfyUI 0.37.0 - timing read from execution_start / execution_success, never wall clock"},
    "c5_axis": {"zh": "秒", "en": "seconds"},
    "c5_unit": {"zh": " 秒", "en": " s"},
    "c5_items": {"zh": [["MiniMax H3 · 文生视频 + 音频", "1344×768，124 帧，5.17 s 含立体声"],
                        ["HunyuanVideo 1.5 · 480p，4 步", "848×480，121 帧，5.04 s"],
                        ["MiniMax H3 · 冒烟测试", "768×448，56 帧"],
                        ["FLUX.2 Klein 4B · fp8 图像编辑", "单张 1024×1024"],
                        ["Z-Image-Turbo · int8", "1024×1024，8 步"],
                        ["Z-Image-Turbo · nvfp4", "1024×1024，8 步"]],
                 "en": [["MiniMax H3 - text to video + audio", "1344x768, 124 frames, 5.17 s clip with stereo audio"],
                        ["HunyuanVideo 1.5 - 480p, 4 steps", "848x480, 121 frames, 5.04 s clip"],
                        ["MiniMax H3 - smoke test", "768x448, 56 frames"],
                        ["FLUX.2 Klein 4B - fp8 image edit", "single 1024x1024 image"],
                        ["Z-Image-Turbo - int8", "1024x1024, 8 steps"],
                        ["Z-Image-Turbo - nvfp4", "1024x1024, 8 steps"]]},

    # ---------------------------------------------------------------- chart 6
    "c6_title": {"zh": "NVFP4 实际带来什么", "en": "What NVFP4 actually buys you"},
    "c6_sub": {"zh": "Z-Image-Turbo，同编码器、同 1024×1024 / 8 步、同种子",
               "en": "Z-Image-Turbo, same encoder, same 1024x1024 / 8 steps, same seed"},
    "c6_groups": {"zh": [["生成耗时", " 秒"], ["DiT 权重文件", " GB"]],
                  "en": [["Generation time", "seconds"], ["DiT weight file", "GB"]]},
    "c6_better": {"zh": "更优", "en": "better"},
    "c6_f1": {"zh": "时间与体积都变好，而实测画质差异始终落在种子噪声地板之下（见图 3）。",
              "en": "Both time and size improve, and the measured quality gap stays below the seed-noise floor (see chart 3)."},
}


def g(key, lang):
    """Look up a localised string."""
    return S[key][lang]


# ==================================================================== chart 1
def chart_download_sources(lang):
    h = 316
    notes = g("c1_notes", lang)
    rows = [("www.modelscope.cn", 11, 27, 22, EMERALD),
            ("hf-mirror.com", 2, 4, 3, AMBER),
            ("huggingface.co", 1.6, 2.2, 1.9, DIM)]
    p = header(g("c1_title", lang), g("c1_sub", lang))
    p.append(t(PAD, 84, g("c1_head", lang), 13.5, TXT, 600))
    x0, x1 = 300, 800
    y0, rowh, vmax = 106, 56, 30
    for gv in range(0, vmax + 1, 5):
        gx = x0 + (x1 - x0) * gv / vmax
        p.append(line(gx, y0 - 12, gx, y0 + len(rows) * rowh - 26))
        p.append(t(gx, y0 + len(rows) * rowh - 12, gv, 11.5, DIM, anchor="middle"))
    p.append(t((x0 + x1) / 2, y0 + len(rows) * rowh + 6, "MB/s", 11.5, MUT, anchor="middle"))
    for i, (name, lo, hi, nom, col) in enumerate(rows):
        y = y0 + i * rowh
        p.append(t(PAD, y + 8, esc(name), 14, TXT, 600))
        p.append(t(PAD, y + 25, esc(notes[i]), 11, MUT))
        xn = x0 + (x1 - x0) * nom / vmax
        xh = x0 + (x1 - x0) * hi / vmax
        p.append(rect(x0, y - 4, xn - x0, 22, col, rx=5))
        p.append(rect(xn, y + 3, xh - xn, 8, col, rx=4, opacity=0.3))
        p.append(t(xh + 8, y + 13, f"{lo}-{hi}", 14, TXT, 700))
    p.append(line(PAD, h - 42, W - PAD, h - 42, GRID))
    p.append(t(PAD, h - 24, g("c1_f1", lang), 11.5, TXT, 600))
    p.append(t(PAD, h - 8, g("c1_f2", lang), 11, MUT))
    save(lang, "chart1-download-sources.svg", p, W, h, g("c1_title", lang))


# ==================================================================== chart 2
def chart_model_footprint(lang):
    vram = 24.0
    names = g("c2_items", lang)
    meta = [(20.97, RED, True), (16.65, DIM, True), (15.69, BLUE, True),
            (8.04 + 0.34, AMBER, False), (6.20 + 3.48, DIM, False),
            (4.51 + 3.48, EMERALD, False), (4.07, EMERALD, False)]
    items = [(n, gb, col, over) for n, (gb, col, over) in zip(names, meta)]
    h = 300
    p = header(g("c2_title", lang), g("c2_sub", lang))
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
        p.append(t(x0 + wpx + 7, y + 12,
                   f"{gb:.2f}" + ("  " + g("c2_off", lang) if over else ""),
                   11.5, TXT if not over else MUT, 700 if not over else None))
    save(lang, "chart2-model-footprint.svg", p, W, h, g("c2_title", lang))


# ==================================================================== chart 3
def chart_quant_ab(lang):
    h = 336
    tags, notes = g("c3_tags", lang), g("c3_notes", lang)
    vals = [16.84, 12.45, 12.10]
    cols = [EMERALD, DIM, DIM]
    hi = [True, False, False]
    rows = list(zip(tags, notes, vals, cols, hi))
    p = header(g("c3_title", lang), g("c3_sub", lang))
    x0, x1 = 268, 812
    y0, rowh, vmax = 116, 56, 20
    for gv in range(0, vmax + 1, 5):
        gx = x0 + (x1 - x0) * gv / vmax
        p.append(line(gx, y0 - 16, gx, y0 + len(rows) * rowh - 14))
        p.append(t(gx, y0 + len(rows) * rowh + 2, gv, 11.5, DIM, anchor="middle"))
    p.append(t((x0 + x1) / 2, y0 + len(rows) * rowh + 20, g("c3_axis", lang),
               11.5, MUT, anchor="middle"))
    lo = x0 + (x1 - x0) * 12.10 / vmax
    hh = x0 + (x1 - x0) * 12.45 / vmax
    p.append(rect(lo, y0 - 16, hh - lo, len(rows) * rowh - 14, DIM, rx=0, opacity=0.16))
    p.append(t((lo + hh) / 2, y0 - 24, g("c3_floor", lang), 11, MUT, anchor="middle"))
    for i, (tag, note, v, col, hi_) in enumerate(rows):
        y = y0 + i * rowh
        p.append(t(PAD, y + 9, tag, 14, TXT, 600))
        p.append(t(PAD, y + 26, note, 11, MUT))
        wpx = (x1 - x0) * v / vmax
        p.append(rect(x0, y - 5, wpx, 24, col, rx=5, opacity=1 if hi_ else 0.45))
        p.append(t(x0 + wpx + 9, y + 13, f"{v:.2f}", 15, TXT, 700))
    p.append(line(PAD, h - 52, W - PAD, h - 52, GRID))
    p.append(t(PAD, h - 32, g("c3_f1", lang), 11.5, TXT, 600))
    p.append(t(PAD, h - 15, g("c3_f2", lang), 11.5, MUT))
    save(lang, "chart3-quant-ab-psnr.svg", p, W, h, g("c3_title", lang))


# ==================================================================== chart 4
def chart_decision_tree(lang):
    h = 400

    def node(x, y, w, hh, pair, col):
        title, sub = pair
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

    p = header(g("c4_title", lang), g("c4_sub", lang))
    p.append(f'<defs><marker id="a" markerWidth="9" markerHeight="9" refX="7.5" refY="4.5" '
             f'orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="{DIM}"/></marker></defs>')

    p += node(340, 78, 250, 52, g("c4_fit", lang), BLUE)
    p += node(340, 176, 250, 52, g("c4_bw", lang), BLUE)
    p += node(672, 176, 224, 52, g("c4_nvfp4", lang), EMERALD)
    p += node(340, 274, 250, 52, g("c4_int8", lang), AMBER)
    p += node(28, 78, 232, 52, g("c4_over", lang), RED)
    p += node(28, 274, 232, 52, g("c4_w4a16", lang), RED)

    p += arrow(340, 104, 262, 104, g("c4_no", lang), 292, 98)
    p += arrow(465, 130, 465, 176, g("c4_yes", lang), 473, 156)
    p += arrow(590, 202, 670, 202, g("c4_yes", lang), 624, 196)
    p += arrow(465, 228, 465, 274, g("c4_no", lang), 473, 254)
    p += arrow(144, 130, 144, 274)

    p.append(line(PAD, 348, W - PAD, 348, GRID, dash="4 4"))
    p.append(t(PAD, 370, g("c4_f1", lang), 12, TXT, 600))
    p.append(t(PAD, 390, g("c4_f2", lang), 11, MUT))
    save(lang, "chart4-quant-decision-tree.svg", p, W, h, g("c4_title", lang))


# ==================================================================== chart 5
def chart_benchmarks(lang):
    import math
    vals = [519.06, 117.0, 76.31, 42.32, 17.70, 13.80]
    cols = [RED, BLUE, BLUE, AMBER, DIM, EMERALD]
    items = [(n, c, v, col) for (n, c), v, col in zip(g("c5_items", lang), vals, cols)]
    h = 330
    p = header(g("c5_title", lang), g("c5_sub", lang))
    x0, x1 = 340, 812
    lo, hi = math.log10(10), math.log10(600)
    y0, rowh = 106, 32

    def sx(v):
        return x0 + (x1 - x0) * (math.log10(v) - lo) / (hi - lo)

    for gv in [10, 20, 30, 50, 100, 200, 300, 500]:
        gx = sx(gv)
        p.append(line(gx, y0 - 12, gx, y0 + len(items) * rowh - 6))
        p.append(t(gx, y0 + len(items) * rowh + 8, gv, 11, DIM, anchor="middle"))
    p.append(t((x0 + x1) / 2, y0 + len(items) * rowh + 26, g("c5_axis", lang),
               11, MUT, anchor="middle"))
    for i, (name, cfg, v, col) in enumerate(items):
        y = y0 + i * rowh
        p.append(t(PAD, y + 11, esc(name), 12.5, TXT, 600))
        p.append(t(PAD, y + 26, esc(cfg), 10.5, MUT))
        wpx = sx(v) - x0
        p.append(rect(x0, y - 1, wpx, 18, col, rx=4))
        p.append(t(x0 + wpx + 8, y + 13, f"{v:.1f}" + g("c5_unit", lang), 13, TXT, 700))
    save(lang, "chart5-model-benchmark.svg", p, W, h, g("c5_title", lang))


# ==================================================================== chart 6
def chart_nvfp4_gain(lang):
    h = 250
    p = header(g("c6_title", lang), g("c6_sub", lang))
    names = g("c6_groups", lang)
    data = [(17.70, 13.80, 22.0), (6.20, 4.51, 27.3)]
    groups = [(n, u, a, b, gain) for (n, u), (a, b, gain) in zip(names, data)]
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
        p.append(t(x0 + barw + 46 + 52, y + 32, g("c6_better", lang), 11, MUT))
    p.append(t(PAD, h - 14, g("c6_f1", lang), 11, MUT))
    save(lang, "chart6-nvfp4-gain.svg", p, W, h, g("c6_title", lang))


if __name__ == "__main__":
    print("generating charts ->", OUT)
    for lang in LANGS:
        for fn in (chart_download_sources, chart_model_footprint, chart_quant_ab,
                   chart_decision_tree, chart_benchmarks, chart_nvfp4_gain):
            fn(lang)
    print("done")
