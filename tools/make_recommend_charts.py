#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_recommend_charts.py — 顶部「三套方案」与授权矩阵共 4 张图（中英各一套）。

  chart7-recommend-quality.svg    画质/音质优先（仅商用可用模型）
  chart8-recommend-efficient.svg  效率优先（综合最佳性价比）
  chart9-recommend-scenario.svg   分场景选择矩阵
  chart10-licence-matrix.svg      授权矩阵（可商用 / 地域 / 营收门槛）

风格契约与 make_charts.py 一致：920 宽、白底卡片、全部内联十六进制色、无 <style>。
"""
import os
import json

W = 920
PAD = 24
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets")

FF = "-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
TXT, MUT, DIM, GRID = "#0f172a", "#64748b", "#94a3b8", "#e2e8f0"
AMBER, BLUE, EMERALD, RED, PURPLE = "#d97706", "#2563eb", "#059669", "#dc2626", "#7c3aed"
LANGS = ("zh", "en")

S = {
 "c7_title": {"zh": "方案一 · 画质 / 音质优先（仅含可商用模型）",
              "en": "Option 1 · Best quality (commercially usable models only)"},
 "c7_sub": {"zh": "每个领域选「产出最好」的那一个。YuE2（禁商用）、MiniMax Music 3（授权存疑）已排除",
            "en": "The best producer per domain. YuE2 (non-commercial) and MiniMax Music 3 (licence unclear) are excluded"},
 "c7_rows": {"zh": [
    ["图像", "Qwen-Image 2512 + Lightning", "1328² · 4 步 · 像素比 1024² 多 68% · 中文 30/30 逐字全对", 12.2, BLUE],
    ["图像编辑", "FLUX.2 Klein 4B fp8（9B 禁商用，已排除）", "1024² · 4 步 · 双 pass", 42.3, BLUE],
    ["视频 + 音频", "MiniMax H3 8 步（⚠ 排除欧美四地）", "1344×768 · 124 帧 · 原生立体声音轨", 539.5, PURPLE],
    ["视频（全球商用替代）", "Wan 2.2 5B TI2V", "1280×704 · 121 帧 · Apache 2.0 无地域限制", 355.1, EMERALD],
    ["音乐（含人声+编曲）", "ACE-Step 1.5 XL turbo", "60 s 歌曲 · 8 步 · Apache 2.0", 28.6, AMBER],
    ["图生 3D", "Hunyuan3D 2.1", "GLB · 202,768 顶点 / 522,140 三角面 · ⚠ 排除 EU/UK/KR", 54.7, EMERALD]],
  "en": [
    ["Image", "Qwen-Image 2512 + Lightning", "1328² · 4 steps · 68% more pixels than 1024² · Chinese text 30/30 exact", 12.2, BLUE],
    ["Image edit", "FLUX.2 Klein 4B fp8 (9B is non-commercial — excluded)", "1024² · 4 steps · two-pass", 42.3, BLUE],
    ["Video + audio", "MiniMax H3 8-step (⚠ excludes US/EU/UK/KR)", "1344×768 · 124 frames · native stereo audio", 539.5, PURPLE],
    ["Video (global-safe alt.)", "Wan 2.2 5B TI2V", "1280×704 · 121 frames · Apache 2.0, no territory limit", 355.1, EMERALD],
    ["Music (vocals + arrangement)", "ACE-Step 1.5 XL turbo", "60 s song · 8 steps · Apache 2.0", 28.6, AMBER],
    ["Image → 3D", "Hunyuan3D 2.1", "GLB · 202,768 verts / 522,140 tris · ⚠ excludes EU/UK/KR", 54.7, EMERALD]]},

 "c8_title": {"zh": "方案二 · 效率优先（综合性价比最高）",
              "en": "Option 2 · Efficiency first (best overall value)"},
 "c8_sub": {"zh": "每个领域选「时间 ÷ 质量」最优的那一个，全部可商用、无地域限制（MiniMax H3 除外）",
            "en": "The best time-per-quality pick per domain — all commercial, no territory limits (except MiniMax H3)"},
 "c8_rows": {"zh": [
    ["图像（常驻显存）", "Z-Image-Turbo nvfp4", "1024² · 8 步 · 8.33 GB 全常驻零 offload · 中英双语文本", 13.8, BLUE],
    ["图像编辑", "FLUX.2 Klein 4B fp8", "1024² · 双 pass · Apache 2.0（9B 禁商用）", 42.3, BLUE],
    ["视频（旗舰画质）", "Wan 2.2 14B MoE + 4步 LoRA", "832×480 · 81 帧 · 4 步比 20 步快 7.9×", 93.8, EMERALD],
    ["音乐", "ACE-Step 1.5 turbo", "60 s 歌曲 · 8 步 · Apache 2.0 无门槛", 22.9, AMBER],
    ["图生 3D", "Hunyuan3D 2.1", "GLB 52 万面 · 一个文件全包", 54.7, EMERALD]],
  "en": [
    ["Image (resident VRAM)", "Z-Image-Turbo nvfp4", "1024² · 8 steps · 8.33 GB fully resident, zero offload · bilingual text", 13.8, BLUE],
    ["Image edit", "FLUX.2 Klein 4B fp8", "1024² · two-pass · Apache 2.0 (9B is non-commercial)", 42.3, BLUE],
    ["Video (flagship quality)", "Wan 2.2 14B MoE + 4-step LoRA", "832×480 · 81 frames · 4 steps is 7.9× faster than 20", 93.8, EMERALD],
    ["Music", "ACE-Step 1.5 turbo", "60 s song · 8 steps · Apache 2.0, no strings", 22.9, AMBER],
    ["Image → 3D", "Hunyuan3D 2.1", "GLB 520k triangles · one file does it all", 54.7, EMERALD]]},

 "c9_title": {"zh": "方案三 · 分场景选择矩阵（按需求直接查）",
              "en": "Option 3 · Scenario matrix (look up by need)"},
 "c9_sub": {"zh": "左侧是你的场景，右侧是当前最优解与它的授权边界。✅=可商用 ⚠️=有条件 ❌=禁商用",
            "en": "Your scenario on the left; the current best answer and its licence boundary on the right. ✅ commercial ⚠️ conditional ❌ non-commercial"},
 "c9_rows": {"zh": [
    ["中文海报 / 图内大量文字", "Qwen-Image 2512 + Lightning", "12.2 s", "✅ Apache 2.0"],
    ["快速草稿 / 高频迭代", "Z-Image-Turbo nvfp4", "13.8 s", "✅ Apache 2.0"],
    ["结构化排版 / 文字渲染最准", "ERNIE-Image Turbo", "37.3 s", "✅ Apache 2.0"],
    ["短视频 + 原生音轨（国内）", "MiniMax H3 4步 LoRA", "286.2 s", "⚠ 排除 US/EU/UK/KR"],
    ["短视频（全球商用）", "Wan 2.2 14B MoE 4步", "93.8 s", "✅ Apache 2.0"],
    ["带人声和编曲的整首歌", "ACE-Step 1.5 XL turbo", "28.6 s", "✅ Apache 2.0"],
    ["器乐 / 音效 / 背景乐", "Stable Audio 3 Medium", "13.8 s", "✅ < $1M 营收"],
    ["整首歌（最高分，禁商用）", "YuE2-3B", "93.7 s", "❌ CC BY-NC"],
    ["图生 3D 资产（GLB）", "Hunyuan3D 2.1", "54.7 s", "⚠ ≤100万月活 · 排除 EU/UK/KR"]],
  "en": [
    ["Chinese poster / dense in-image text", "Qwen-Image 2512 + Lightning", "12.2 s", "✅ Apache 2.0"],
    ["Fast drafts / frequent iteration", "Z-Image-Turbo nvfp4", "13.8 s", "✅ Apache 2.0"],
    ["Most accurate structured text", "ERNIE-Image Turbo", "37.3 s", "✅ Apache 2.0"],
    ["Short clip + native audio (China)", "MiniMax H3 4-step LoRA", "286.2 s", "⚠ excludes US/EU/UK/KR"],
    ["Short clip (global commercial)", "Wan 2.2 14B MoE 4-step", "93.8 s", "✅ Apache 2.0"],
    ["Full song with vocals", "ACE-Step 1.5 XL turbo", "28.6 s", "✅ Apache 2.0"],
    ["Instrumental / SFX / backing", "Stable Audio 3 Medium", "13.8 s", "✅ under $1M revenue"],
    ["Highest-scoring song (non-comm.)", "YuE2-3B", "93.7 s", "❌ CC BY-NC"],
    ["Image → 3D asset (GLB)", "Hunyuan3D 2.1", "54.7 s", "⚠ ≤1M MAU · excludes EU/UK/KR"]]},

 "c10_title": {"zh": "授权矩阵（商用前必查）",
               "en": "Licence matrix (check before commercial use)"},
 "c10_sub": {"zh": "「权重能下载」不等于「产出能商用」。✅ 可商用 · ⚠️ 有条件 · ❌ 禁商用 · ？ 未核实",
             "en": "\"The weights download\" ≠ \"the output is commercial\". ✅ allowed · ⚠️ conditional · ❌ forbidden · ? unverified"},
 "c10_rows": {"zh": [
    ["Qwen-Image 2512", "✅", "无", "无", "Apache 2.0"],
    ["Z-Image-Turbo", "✅", "无", "无", "Apache 2.0"],
    ["ERNIE-Image / Turbo", "✅", "无", "无", "Apache 2.0"],
    ["Wan 2.2 (5B / 14B)", "✅", "无", "无", "Apache 2.0"],
    ["ACE-Step 1.5", "✅", "无", "无", "Apache 2.0"],
    ["FLUX.2 Klein 4B", "✅", "无", "无", "Apache 2.0"],
    ["FLUX.2 Klein 9B", "❌", "—", "—", "FLUX Non-Commercial"],
    ["FLUX.1-dev", "❌", "—", "—", "FLUX.1-dev Non-Commercial"],
    ["Stable Audio 3 Medium", "✅", "无", "< $1M 营收", "Stability Community"],
    ["LTX-Video / LTX-2.3", "⚠", "无", "< $1000万 营收", "LTX Community"],
    ["MiniMax H3", "⚠", "排除 US/EU/UK/KR", "< $2000万 营收", "MiniMax Community"],
    ["MiniMax Music 3", "？", "？", "？", "信源冲突：CC BY-NC vs Community"],
    ["HunyuanVideo 1.5", "⚠", "排除 EU/UK/KR", "—", "Tencent Community"],
    ["Hunyuan3D 2.1", "⚠", "排除 EU/UK/KR", "≤ 100万 月活", "Tencent Community"],
    ["YuE2-3B", "❌", "—", "—", "CC BY-NC 4.0"]],
  "en": [
    ["Qwen-Image 2512", "✅", "none", "none", "Apache 2.0"],
    ["Z-Image-Turbo", "✅", "none", "none", "Apache 2.0"],
    ["ERNIE-Image / Turbo", "✅", "none", "none", "Apache 2.0"],
    ["Wan 2.2 (5B / 14B)", "✅", "none", "none", "Apache 2.0"],
    ["ACE-Step 1.5", "✅", "none", "none", "Apache 2.0"],
    ["FLUX.2 Klein 4B", "✅", "none", "none", "Apache 2.0"],
    ["FLUX.2 Klein 9B", "❌", "—", "—", "FLUX Non-Commercial"],
    ["FLUX.1-dev", "❌", "—", "—", "FLUX.1-dev Non-Commercial"],
    ["Stable Audio 3 Medium", "✅", "none", "< $1M revenue", "Stability Community"],
    ["LTX-Video / LTX-2.3", "⚠", "none", "< $10M revenue", "LTX Community"],
    ["MiniMax H3", "⚠", "excl. US/EU/UK/KR", "< $20M revenue", "MiniMax Community"],
    ["MiniMax Music 3", "?", "?", "?", "conflicting: CC BY-NC vs Community"],
    ["HunyuanVideo 1.5", "⚠", "excl. EU/UK/KR", "—", "Tencent Community"],
    ["Hunyuan3D 2.1", "⚠", "excl. EU/UK/KR", "≤ 1M MAU", "Tencent Community"],
    ["YuE2-3B", "❌", "—", "—", "CC BY-NC 4.0"]]},
}


def g(k, lang):
    return S[k][lang]


def t(x, y, s, size=12, fill=MUT, weight=None, anchor=None):
    a = f' text-anchor="{anchor}"' if anchor else ""
    w = f' font-weight="{weight}"' if weight else ""
    return (f'<text x="{x}" y="{y}" font-family="{FF}" font-size="{size}" '
            f'fill="{fill}"{w}{a}>{s}</text>')


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def rect(x, y, w, h, fill, rx=5, opacity=None, stroke=None, sw=1, dash=None):
    o = f' opacity="{opacity}"' if opacity is not None else ""
    st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w,0):.1f}" height="{max(h,0):.1f}" '
            f'rx="{rx}" fill="{fill}"{o}{st}{d}/>')


def line(x1, y1, x2, y2, stroke=GRID, sw=1, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{stroke}" stroke-width="{sw}"{d}/>')


def save(lang, name, parts, h, title):
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h}" width="{W}" height="{h}" '
             f'role="img" aria-label="{esc(title)}">', rect(0, 0, W, h, "#ffffff", rx=12)] + parts + ["</svg>"]
    d = os.path.join(OUT, lang)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(parts) + "\n")
    print(f"  {lang}/{name:36s} {W}x{h}")


def header(title, sub=None):
    p = [t(PAD, 34, esc(title), 19, TXT, 700)]
    if sub:
        p.append(t(PAD, 56, esc(sub), 12.5, MUT))
    return p


import math
def _bar(p, x0, x1, v, vmax, y, h, col, label, vmax_cap=None):
    w = (x1 - x0) * (math.log10(v) - math.log10(10)) / (math.log10(vmax_cap or vmax) - math.log10(10))
    p.append(rect(x0, y, max(w, 2), h, col, rx=4))
    p.append(t(x0 + max(w, 2) + 8, y + h - 4, label, 12, TXT, 700))


def recommend_card(lang, name, title, sub, rows, vmax=600):
    rowh = 62
    h = 118 + len(rows) * rowh + 26
    p = header(title, sub)
    y0 = 100
    x_txt, x_bar = PAD, 470
    for i, (dom, model, spec, secs, col) in enumerate(rows):
        y = y0 + i * rowh
        p.append(rect(PAD, y - 8, W - PAD * 2, rowh - 6, "#f8fafc", rx=8))
        p.append(t(PAD + 10, y + 14, esc(dom), 12.5, TXT, 700))
        p.append(t(PAD + 10, y + 32, esc(model), 13, TXT, 600))
        # 规格文字（右侧栏，自动换两行）
        spec_lines = [spec]
        if len(spec) > 52:
            cut = spec[:52].rfind(" ")
            spec_lines = [spec[:cut], spec[cut:].strip()]
        for j, ln in enumerate(spec_lines):
            p.append(t(PAD + 10, y + 44 + j * 13, esc(ln), 10.5, MUT))
        # 时间条（对数）
        _bar(p, x_bar, W - PAD - 74, secs, vmax, y + 6, 20, col, f"{secs:.1f} s")
        p.append(t(W - PAD - 60, y + 44, "server time", 9.5, DIM))
    p.append(line(PAD, h - 22, W - PAD, h - 22, GRID))
    p.append(t(PAD, h - 6, "所有耗时均为 ComfyUI 服务端 execution_start→execution_success 权威计时"
               if lang == "zh" else
               "All timings are ComfyUI server-side execution_start→execution_success", 10.5, DIM))
    save(lang, name, p, h, title)


def scenario_matrix(lang, name, title, sub, rows):
    rowh = 34
    h = 118 + len(rows) * rowh + 20
    p = header(title, sub)
    y0 = 100
    cols = [(PAD + 6, 300), (320, 260), (600, 90), (700, 196)]
    p.append(t(cols[0][0], y0 - 12, "场景 / Scenario" if lang == "zh" else "Scenario", 11, DIM, 700))
    p.append(t(cols[1][0], y0 - 12, "推荐模型 / Pick" if lang == "zh" else "Pick", 11, DIM, 700))
    p.append(t(cols[2][0], y0 - 12, "耗时" if lang == "zh" else "Time", 11, DIM, 700))
    p.append(t(cols[3][0], y0 - 12, "授权 / Licence" if lang == "zh" else "Licence", 11, DIM, 700))
    for i, (scene, model, secs, lic) in enumerate(rows):
        y = y0 + i * rowh
        if i % 2 == 0:
            p.append(rect(PAD, y - 9, W - PAD * 2, rowh - 4, "#f8fafc", rx=4))
        col = EMERALD if lic.startswith("✅") else (RED if lic.startswith("❌") else AMBER)
        p.append(t(cols[0][0], y + 8, esc(scene), 12, TXT))
        p.append(t(cols[1][0], y + 8, esc(model), 12, TXT, 600))
        p.append(t(cols[2][0], y + 8, f"{secs} s", 12, TXT, 700))
        p.append(t(cols[3][0], y + 8, esc(lic), 12, col, 600))
    p.append(line(PAD, h - 16, W - PAD, h - 16, GRID))
    p.append(t(PAD, h - 2, "⚠ = 有条件：地域排除或营收门槛，商用前必须读该模型的 LICENSE"
               if lang == "zh" else
               "⚠ = conditional: territory exclusion or revenue threshold — read the model's LICENSE first", 10.5, DIM))
    save(lang, name, p, h, title)


def licence_matrix(lang, name, title, sub, rows):
    rowh = 30
    h = 122 + len(rows) * rowh + 18
    p = header(title, sub)
    y0 = 104
    cx = [PAD + 6, 330, 470, 640, 760]
    p.append(t(cx[0], y0 - 14, "模型 / Model" if lang == "zh" else "Model", 11, DIM, 700))
    p.append(t(cx[1], y0 - 14, "商用" if lang == "zh" else "Commercial", 11, DIM, 700))
    p.append(t(cx[2], y0 - 14, "地域" if lang == "zh" else "Territory", 11, DIM, 700))
    p.append(t(cx[3], y0 - 14, "门槛" if lang == "zh" else "Threshold", 11, DIM, 700))
    p.append(t(cx[4], y0 - 14, "授权 / Licence" if lang == "zh" else "Licence", 11, DIM, 700))
    for i, (model, com, terr, thr, lic) in enumerate(rows):
        y = y0 + i * rowh
        if i % 2 == 0:
            p.append(rect(PAD, y - 9, W - PAD * 2, rowh - 4, "#f8fafc", rx=4))
        col = EMERALD if com == "✅" else (RED if com == "❌" else (DIM if com == "？" else AMBER))
        p.append(t(cx[0], y + 8, esc(model), 12, TXT))
        p.append(t(cx[1], y + 8, com, 14, col, 700))
        p.append(t(cx[2], y + 8, esc(terr), 10.5, MUT))
        p.append(t(cx[3], y + 8, esc(thr), 10.5, MUT))
        p.append(t(cx[4], y + 8, esc(lic), 10.5, MUT))
    p.append(line(PAD, h - 14, W - PAD, h - 14, GRID))
    note = ("本表仅整理公开条款，不构成法律意见；商用前请回到各模型官方页面再确认。"
            if lang == "zh" else
            "This table only summarises published terms and is not legal advice; re-check each model page before commercial use.")
    p.append(t(PAD, h, esc(note), 10.5, DIM))
    save(lang, name, p, h, title)


if __name__ == "__main__":
    print("generating recommendation charts ->", OUT)
    for lang in LANGS:
        recommend_card(lang, "chart7-recommend-quality.svg",
                       g("c7_title", lang), g("c7_sub", lang), g("c7_rows", lang))
        recommend_card(lang, "chart8-recommend-efficient.svg",
                       g("c8_title", lang), g("c8_sub", lang), g("c8_rows", lang), vmax=600)
        scenario_matrix(lang, "chart9-recommend-scenario.svg",
                        g("c9_title", lang), g("c9_sub", lang), g("c9_rows", lang))
        licence_matrix(lang, "chart10-licence-matrix.svg",
                       g("c10_title", lang), g("c10_sub", lang), g("c10_rows", lang))
    print("done")
