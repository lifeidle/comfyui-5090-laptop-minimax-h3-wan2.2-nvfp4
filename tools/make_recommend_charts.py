#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_recommend_charts.py — 顶部「三套方案」与授权矩阵共 4 张图（中英各一套）。

  chart7-recommend-quality.svg    方案一 · 画质/音质优先
  chart8-recommend-efficient.svg  方案二 · 效率优先
  chart9-recommend-scenario.svg   方案三 · 分场景矩阵
  chart10-licence-matrix.svg      授权矩阵

数据与主基准图（tools/make_charts.py）保持同一测量口径：服务端 execution_start→execution_success。
风格：920 宽、白底卡片、全部内联十六进制色、无 <style>。
"""
import os

W = 920
PAD = 24
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets")

FF = "-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
TXT, MUT, DIM, GRID = "#0f172a", "#64748b", "#94a3b8", "#e2e8f0"
IMG_C, VID_C, MUS_C, THREE_C = "#2563eb", "#7c3aed", "#d97706", "#059669"
EMERALD, RED, AMBER = "#059669", "#dc2626", "#d97706"


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def t(x, y, s, size=12, fill=MUT, weight=None):
    w = f' font-weight="{weight}"' if weight else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FF}" font-size="{size}" '
            f'fill="{fill}"{w}>{esc(s)}</text>')


def rect(x, y, w, h, fill, rx=5):
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w,0):.1f}" height="{max(h,0):.1f}" '
            f'rx="{rx}" fill="{fill}"/>')


def line(x1, y1, x2, y2, stroke=GRID):
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{stroke}" stroke-width="1"/>')


def save(lang, name, parts, h, title):
    parts = ([f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h}" width="{W}" '
              f'height="{h}" role="img" aria-label="{esc(title)}">',
              rect(0, 0, W, h, "#ffffff", rx=12)] + parts + ["</svg>"])
    d = os.path.join(OUT, lang)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(parts) + "\n")
    print(f"  {lang}/{name:38s} {W}x{h}")


def header(title, sub=None):
    p = [t(PAD, 34, title, 19, TXT, 700)]
    if sub:
        p.append(t(PAD, 56, sub, 12.5, MUT))
    return p


# ─────────────────────────────────────────────────────────── 方案一 / 方案二
# (领域, 模型, 规格, 耗时秒, 颜色)
PLAN_QUALITY = {
    "zh": [
        ("图像（满质量 · 中文 30/30）", "Qwen-Image 2.1 int8", "1328²，25 步 · 同提示词比 2512 快 2.8×", 72.7, IMG_C),
        ("图像（最快 · 中文 30/30）", "Qwen-Image 2512 + Lightning", "1328²，4 步", 12.2, IMG_C),
        ("图像（常驻显存）", "Z-Image-Turbo nvfp4", "1024²，8 步 · 8.33 GB 全常驻零 offload", 13.8, IMG_C),
        ("图像编辑（⚠ 非商用授权）", "FLUX.2 Klein 9B fp8", "1024²，双 pass，4 步", 18.9, IMG_C),
        ("2K 级超分 ★", "PixelDiT pid_flux2", "1024²→2048²，4 步 · 替代跑不动的 1080p 路径", 5.4, IMG_C),
        ("视频（质量 · 全球可商用）", "Wan 2.2 14B MoE + 4步 LoRA", "832×480，81 帧", 93.8, VID_C),
        ("视频（速度）", "LTX-Video 2B 蒸馏", "1216×704，121 帧 · ⚠ 提示词遵循弱", 19.2, VID_C),
        ("视频 + 音频（⚠ 排除欧美四地）", "MiniMax H3 + 4步 LoRA", "1344×768，124 帧 · 原生立体声", 286.2, VID_C),
        ("音乐（人声+编曲 · 可商用）", "ACE-Step 1.5 XL turbo", "60 s 歌曲，8 步", 20.8, MUS_C),
        ("图生 3D（⚠ 排除 EU/UK/KR）", "Hunyuan3D 2.1", "GLB 52 万面 · 30 步", 54.7, THREE_C),
    ],
    "en": [
        ("Image (full quality, Chinese 30/30)", "Qwen-Image 2.1 int8", "1328², 25 steps · 2.8× faster than 2512", 72.7, IMG_C),
        ("Image (fastest, Chinese 30/30)", "Qwen-Image 2512 + Lightning", "1328², 4 steps", 12.2, IMG_C),
        ("Image (resident VRAM)", "Z-Image-Turbo nvfp4", "1024², 8 steps · 8.33 GB resident, zero offload", 13.8, IMG_C),
        ("Image edit (⚠ non-commercial licence)", "FLUX.2 Klein 9B fp8", "1024², two-pass, 4 steps", 18.9, IMG_C),
        ("2K-class upscale ★", "PixelDiT pid_flux2", "1024²→2048², 4 steps · replaces the 1080p dead end", 5.4, IMG_C),
        ("Video (quality, global commercial)", "Wan 2.2 14B MoE + 4-step LoRA", "832×480, 81 frames", 93.8, VID_C),
        ("Video (speed)", "LTX-Video 2B distilled", "1216×704, 121 frames · ⚠ weak prompt adherence", 19.2, VID_C),
        ("Video + audio (⚠ excludes US/EU/UK/KR)", "MiniMax H3 + 4-step LoRA", "1344×768, 124 frames · native stereo", 286.2, VID_C),
        ("Music (vocals + arrangement, commercial)", "ACE-Step 1.5 XL turbo", "60 s song, 8 steps", 20.8, MUS_C),
        ("Image to 3D (⚠ excludes EU/UK/KR)", "Hunyuan3D 2.1", "GLB 520k triangles · 30 steps", 54.7, THREE_C),
    ],
}
PLAN_EFFICIENT = {
    "zh": [
        ("图像（最快 1024²）", "PixelDiT 1.3B", "1024²，30 步 cfg4 · 全表最快", 10.1, IMG_C),
        ("图像（中文海报）", "Qwen-Image 2512 + Lightning", "1328²，4 步 · 中文 30/30", 12.2, IMG_C),
        ("图像（常驻显存）", "Z-Image-Turbo nvfp4", "1024²，8 步 · 8.33 GB 全常驻", 13.8, IMG_C),
        ("2K 级超分", "PixelDiT pid_flux2", "1024²→2048²，4 步", 5.4, IMG_C),
        ("图像编辑（商用授权）", "FLUX.2 Klein 4B fp8", "1024² · Apache 2.0", 42.3, IMG_C),
        ("视频（旗舰画质）", "Wan 2.2 14B MoE + 4步 LoRA", "832×480，81 帧", 93.8, VID_C),
        ("视频（最轻 · 4.57 GB）", "Kandinsky 5 T2V Lite", "768×512，121 帧 · 最轻但慢", 884.5, VID_C),
        ("音乐（最快且可商用）", "ACE-Step 1.5 XL turbo", "60 s 歌曲，8 步", 20.8, MUS_C),
        ("音乐（最快 · 仅器乐）", "Stable Audio 3 Medium", "60 s 歌曲，8 步", 13.8, MUS_C),
    ],
    "en": [
        ("Image (fastest 1024²)", "PixelDiT 1.3B", "1024², 30 steps cfg4 · fastest in the table", 10.1, IMG_C),
        ("Image (Chinese poster)", "Qwen-Image 2512 + Lightning", "1328², 4 steps · Chinese 30/30", 12.2, IMG_C),
        ("Image (resident VRAM)", "Z-Image-Turbo nvfp4", "1024², 8 steps · 8.33 GB resident", 13.8, IMG_C),
        ("2K-class upscale", "PixelDiT pid_flux2", "1024²→2048², 4 steps", 5.4, IMG_C),
        ("Image edit (commercial licence)", "FLUX.2 Klein 4B fp8", "1024² · Apache 2.0", 42.3, IMG_C),
        ("Video (flagship quality)", "Wan 2.2 14B MoE + 4-step LoRA", "832×480, 81 frames", 93.8, VID_C),
        ("Video (lightest, 4.57 GB)", "Kandinsky 5 T2V Lite", "768×512, 121 frames · lightest but slow", 884.5, VID_C),
        ("Music (fastest and commercial)", "ACE-Step 1.5 XL turbo", "60 s song, 8 steps", 20.8, MUS_C),
        ("Music (fastest, instrumental only)", "Stable Audio 3 Medium", "60 s song, 8 steps", 13.8, MUS_C),
    ],
}
# ─────────────────────────────────────────────────────────── 方案三：分场景
# (场景, 推荐, 耗时, 授权)
SCENARIO = {
    "zh": [
        ("中文海报 / 图内大量文字", "Qwen-Image 2512 + Lightning", "12.2 s", "✅ Apache 2.0"),
        ("中文海报 · 要满质量", "Qwen-Image 2.1 int8", "72.7 s", "✅ Apache 2.0"),
        ("要最快出图（任何题材）", "PixelDiT 1.3B", "10.1 s", "⚠ 授权未核实"),
        ("结构化排版 / 文字最准", "ERNIE-Image Turbo", "37.3 s", "✅ Apache 2.0"),
        ("写实微距 / 产品图", "Chroma1-HD fp8mixed", "42.6 s", "⚠ 未核实"),
        ("图像放大到 2K", "PixelDiT pid_flux2", "5.4 s", "✅ Apache 2.0"),
        ("任意图 4× 放大修复", "SeedVR2 3B int8", "23.6 s", "✅ < $1M 营收"),
        ("短视频（全球可商用）", "Wan 2.2 14B MoE 4步", "93.8 s", "✅ Apache 2.0"),
        ("短视频 + 原生音轨", "MiniMax H3 4步 LoRA", "286.2 s", "⚠ 排除 US/EU/UK/KR"),
        ("最轻的视频模型", "Kandinsky 5 T2V Lite", "884.5 s", "⚠ 未核实"),
        ("整首歌（人声+编曲）", "ACE-Step 1.5 XL turbo", "20.8 s", "✅ Apache 2.0"),
        ("器乐 / 音效 / 背景乐", "Stable Audio 3 Medium", "13.8 s", "✅ < $1M 营收"),
        ("图生 3D 资产（GLB）", "Hunyuan3D 2.1", "54.7 s", "⚠ ≤100万月活 · 排除 EU/UK/KR"),
        ("整首歌（最高分，禁商用）", "YuE2-3B", "87.5 s", "❌ CC BY-NC"),
    ],
    "en": [
        ("Chinese poster / dense in-image text", "Qwen-Image 2512 + Lightning", "12.2 s", "✅ Apache 2.0"),
        ("Chinese poster, full quality", "Qwen-Image 2.1 int8", "72.7 s", "✅ Apache 2.0"),
        ("Fastest image of anything", "PixelDiT 1.3B", "10.1 s", "⚠ licence unverified"),
        ("Most accurate structured text", "ERNIE-Image Turbo", "37.3 s", "✅ Apache 2.0"),
        ("Photoreal macro / product", "Chroma1-HD fp8mixed", "42.6 s", "⚠ unverified"),
        ("Upscale an image to 2K", "PixelDiT pid_flux2", "5.4 s", "✅ Apache 2.0"),
        ("Any image, 4× upscale + restore", "SeedVR2 3B int8", "23.6 s", "✅ under $1M revenue"),
        ("Short clip (global commercial)", "Wan 2.2 14B MoE 4-step", "93.8 s", "✅ Apache 2.0"),
        ("Short clip + native audio", "MiniMax H3 4-step LoRA", "286.2 s", "⚠ excludes US/EU/UK/KR"),
        ("Lightest video model", "Kandinsky 5 T2V Lite", "884.5 s", "⚠ unverified"),
        ("Full song (vocals + arrangement)", "ACE-Step 1.5 XL turbo", "20.8 s", "✅ Apache 2.0"),
        ("Instrumental / SFX / backing", "Stable Audio 3 Medium", "13.8 s", "✅ under $1M revenue"),
        ("Image to 3D asset (GLB)", "Hunyuan3D 2.1", "54.7 s", "⚠ ≤1M MAU · excludes EU/UK/KR"),
        ("Highest-scoring song (non-commercial)", "YuE2-3B", "87.5 s", "❌ CC BY-NC"),
    ],
}
# ─────────────────────────────────────────────────────────── 授权矩阵
# (模型, 商用, 地域, 门槛, 授权)
LICENCE = {
    "zh": [
        ("Qwen-Image 2512 / 2.1", "✅", "无", "无", "Apache 2.0"),
        ("Z-Image-Turbo", "✅", "无", "无", "Apache 2.0"),
        ("ERNIE-Image / Turbo", "✅", "无", "无", "Apache 2.0"),
        ("Wan 2.2 (5B / 14B)", "✅", "无", "无", "Apache 2.0"),
        ("ACE-Step 1.5", "✅", "无", "无", "Apache 2.0"),
        ("FLUX.2 Klein 4B", "✅", "无", "无", "Apache 2.0"),
        ("FLUX.2 Klein 9B", "❌", "—", "—", "FLUX Non-Commercial"),
        ("FLUX.1-dev", "❌", "—", "—", "FLUX.1-dev Non-Commercial"),
        ("PixelDiT", "✅", "无", "无", "待官方页面确认（本手册按可商用处理）"),
        ("SeedVR2 3B", "✅", "无", "< $1M 营收", "Stability 社区授权同类"),
        ("Stable Audio 3 Medium", "✅", "无", "< $1M 营收", "Stability AI Community"),
        ("LTX-Video / LTX-2.3", "⚠", "无", "< $1000万 营收", "LTX Community"),
        ("MiniMax H3", "⚠", "排除 US/EU/UK/KR", "< $2000万 营收", "MiniMax Community"),
        ("MiniMax Music 3", "？", "？", "？", "信源冲突：CC BY-NC vs Community"),
        ("HunyuanVideo 1.5", "⚠", "排除 EU/UK/KR", "—", "Tencent Community"),
        ("Hunyuan3D 2.1", "⚠", "排除 EU/UK/KR", "≤ 100万 月活", "Tencent Community"),
        ("Chroma1-HD / Kandinsky 5", "？", "？", "？", "未核实"),
        ("YuE2-3B", "❌", "—", "—", "CC BY-NC 4.0"),
    ],
    "en": [
        ("Qwen-Image 2512 / 2.1", "✅", "none", "none", "Apache 2.0"),
        ("Z-Image-Turbo", "✅", "none", "none", "Apache 2.0"),
        ("ERNIE-Image / Turbo", "✅", "none", "none", "Apache 2.0"),
        ("Wan 2.2 (5B / 14B)", "✅", "none", "none", "Apache 2.0"),
        ("ACE-Step 1.5", "✅", "none", "none", "Apache 2.0"),
        ("FLUX.2 Klein 4B", "✅", "none", "none", "Apache 2.0"),
        ("FLUX.2 Klein 9B", "❌", "—", "—", "FLUX Non-Commercial"),
        ("FLUX.1-dev", "❌", "—", "—", "FLUX.1-dev Non-Commercial"),
        ("PixelDiT", "✅", "none", "none", "to be confirmed on the official page"),
        ("SeedVR2 3B", "✅", "none", "< $1M revenue", "Stability community family"),
        ("Stable Audio 3 Medium", "✅", "none", "< $1M revenue", "Stability AI Community"),
        ("LTX-Video / LTX-2.3", "⚠", "none", "< $10M revenue", "LTX Community"),
        ("MiniMax H3", "⚠", "excl. US/EU/UK/KR", "< $20M revenue", "MiniMax Community"),
        ("MiniMax Music 3", "?", "?", "?", "conflicting: CC BY-NC vs Community"),
        ("HunyuanVideo 1.5", "⚠", "excl. EU/UK/KR", "—", "Tencent Community"),
        ("Hunyuan3D 2.1", "⚠", "excl. EU/UK/KR", "≤ 1M MAU", "Tencent Community"),
        ("Chroma1-HD / Kandinsky 5", "?", "?", "?", "unverified"),
        ("YuE2-3B", "❌", "—", "—", "CC BY-NC 4.0"),
    ],
}
T7 = {"zh": ("方案一 · 画质 / 音质优先", "每个领域选「产出最好」的那一个；⚠ 标记的是有授权或地域限制的"),
      "en": ("Option 1 · Best quality", "The best producer per domain; ⚠ marks licence or territory limits")}
T8 = {"zh": ("方案二 · 效率优先", "时间 ÷ 质量最优；全部可商用或已标注条件"),
      "en": ("Option 2 · Efficiency first", "Best time-per-quality; all commercial or clearly flagged")}
T9 = {"zh": ("方案三 · 分场景选择矩阵", "左侧是你的场景，右侧是当前最优解与授权边界"),
      "en": ("Option 3 · Scenario matrix", "Your scenario on the left; the best answer and its licence on the right")}
T10 = {"zh": ("授权矩阵（商用前必查）", "✅ 可商用 · ⚠️ 有条件 · ❌ 禁商用 · ？ 未核实"),
       "en": ("Licence matrix (check before commercial use)", "✅ allowed · ⚠️ conditional · ❌ forbidden · ? unverified")}


def plan_card(lang, name, title, sub, rows, vmax=900):
    rowh, rh = 58, 18
    h = 122 + len(rows) * rowh + 26
    p = header(title, sub)
    x_bar = 470
    for i, (dom, model, spec, secs, col) in enumerate(rows):
        y = 100 + i * rowh
        p.append(rect(PAD, y - 8, W - PAD * 2, rowh - 6, "#f8fafc", rx=8))
        p.append(t(PAD + 10, y + 14, dom, 12.5, TXT, 700))
        p.append(t(PAD + 10, y + 32, model, 13, TXT, 600))
        for j, ln in enumerate([spec[:52], spec[52:]] if len(spec) > 52 else [spec]):
            if ln.strip():
                p.append(t(PAD + 10, y + 44 + j * rh, ln, 10.5, MUT))
        bw = (W - PAD - 74 - x_bar) * (secs ** 0.5) / (vmax ** 0.5)
        p.append(rect(x_bar, y + 6, max(bw, 3), 20, col, rx=4))
        p.append(t(x_bar + max(bw, 3) + 8, y + 22, f"{secs:.1f} s", 12, TXT, 700))
    p.append(line(PAD, h - 22, W - PAD, h - 22))
    p.append(t(PAD, h - 6, "所有耗时均为 ComfyUI 服务端 execution_start→execution_success 权威计时"
               if lang == "zh" else
               "All timings are ComfyUI server-side execution_start→execution_success", 10.5, DIM))
    save(lang, name, p, h, title)


def scenario_matrix(lang, name, title, sub, rows):
    rowh = 34
    h = 118 + len(rows) * rowh + 20
    p = header(title, sub)
    y0 = 100
    cx = [(PAD + 6, 320), (336, 268), (620, 84), (712, 190)]
    heads = (("场景 / Scenario", "推荐模型 / Pick", "耗时", "授权 / Licence") if lang == "zh"
             else ("Scenario", "Pick", "Time", "Licence"))
    for (x, _), lab in zip(cx, heads):
        p.append(t(x, y0 - 12, lab, 11, DIM, 700))
    for i, (scene, model, secs, lic) in enumerate(rows):
        y = y0 + i * rowh
        if i % 2 == 0:
            p.append(rect(PAD, y - 9, W - PAD * 2, rowh - 4, "#f8fafc", rx=4))
        col = EMERALD if lic.startswith("✅") else (RED if lic.startswith("❌") else AMBER)
        p.append(t(cx[0][0], y + 8, scene, 12, TXT))
        p.append(t(cx[1][0], y + 8, model, 12, TXT, 600))
        p.append(t(cx[2][0], y + 8, secs, 12, TXT, 700))
        p.append(t(cx[3][0], y + 8, lic, 12, col, 600))
    p.append(line(PAD, h - 16, W - PAD, h - 16))
    p.append(t(PAD, h - 2, "⚠ = 有条件：地域排除或营收门槛，商用前必须读该模型的 LICENSE"
               if lang == "zh" else
               "⚠ = conditional: territory exclusion or revenue threshold — read the model's LICENSE first", 10.5, DIM))
    save(lang, name, p, h, title)


def licence_matrix(lang, name, title, sub, rows):
    rowh = 30
    h = 122 + len(rows) * rowh + 20
    p = header(title, sub)
    y0 = 104
    cx = [PAD + 6, 336, 476, 646, 762]
    heads = (("模型 / Model", "商用", "地域", "门槛", "授权 / Licence") if lang == "zh"
             else ("Model", "Commercial", "Territory", "Threshold", "Licence"))
    for x, lab in zip(cx, heads):
        p.append(t(x, y0 - 14, lab, 11, DIM, 700))
    for i, (model, com, terr, thr, lic) in enumerate(rows):
        y = y0 + i * rowh
        if i % 2 == 0:
            p.append(rect(PAD, y - 9, W - PAD * 2, rowh - 4, "#f8fafc", rx=4))
        col = EMERALD if com == "✅" else (RED if com == "❌" else (DIM if com in ("？", "?") else AMBER))
        p.append(t(cx[0], y + 8, model, 12, TXT))
        p.append(t(cx[1], y + 8, com, 14, col, 700))
        p.append(t(cx[2], y + 8, terr, 10.5, MUT))
        p.append(t(cx[3], y + 8, thr, 10.5, MUT))
        p.append(t(cx[4], y + 8, lic, 10.5, MUT))
    p.append(line(PAD, h - 14, W - PAD, h - 14))
    p.append(t(PAD, h, "本表仅整理公开条款，不构成法律意见；商用前请回到各模型官方页面再确认。"
               if lang == "zh" else
               "This table only summarises published terms and is not legal advice; re-check each model page before commercial use.", 10.5, DIM))
    save(lang, name, p, h, title)


if __name__ == "__main__":
    print("generating recommendation charts ->", OUT)
    for lang in ("zh", "en"):
        plan_card(lang, "chart7-recommend-quality.svg",
                  *T7[lang], PLAN_QUALITY[lang])
        plan_card(lang, "chart8-recommend-efficient.svg",
                  *T8[lang], PLAN_EFFICIENT[lang])
        scenario_matrix(lang, "chart9-recommend-scenario.svg",
                        *T9[lang], SCENARIO[lang])
        licence_matrix(lang, "chart10-licence-matrix.svg",
                       *T10[lang], LICENCE[lang])
    print("done")
