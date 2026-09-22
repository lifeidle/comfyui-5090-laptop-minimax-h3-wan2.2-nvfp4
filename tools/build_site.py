#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_site.py — build index.html from README.md + README_EN.md

Single source of truth: the two Markdown files. This script renders them to
HTML and wraps both languages into one page that:

  * picks the language from navigator.language on first visit (zh* -> Chinese)
  * remembers a manual choice in localStorage
  * honours an explicit ?lang=zh / ?lang=en override
  * rewrites internal .md links to GitHub blob URLs, and the two README
    cross-links into in-page language switches
  * adds GitHub-compatible heading anchors so the in-document TOC works

Requires: markdown-it-py   (pip install markdown-it-py)

    python tools/build_site.py
"""
import os
import re
from urllib.parse import unquote

from markdown_it import MarkdownIt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = "lifeidle/comfyui-5090-laptop-playbook"
SITE = f"https://{REPO.split('/')[0]}.github.io/{REPO.split('/')[1]}/"


# ------------------------------------------------------------------ markdown
def slug(text: str) -> str:
    """GitHub-compatible heading anchor."""
    s = text.strip().lower()
    s = re.sub(r"[^\w\s\u4e00-\u9fff\-]", "", s)      # drop punctuation, keep CJK
    s = s.replace(" ", "-")
    return s


def render(md_path: str) -> str:
    with open(md_path, encoding="utf-8") as f:
        src = f.read()

    md = MarkdownIt("commonmark").enable("table").enable("strikethrough")
    html = md.render(src)

    # 1) heading ids + collect the first h1
    def add_id(m):
        lvl, attrs, inner = m.group(1), m.group(2), m.group(3)
        plain = re.sub(r"<[^>]+>", "", inner)
        return f'<h{lvl} id="{slug(plain)}"{attrs}>{inner}</h{lvl}>'

    html = re.sub(r"<h([1-6])([^>]*)>(.*?)</h\1>", add_id, html, flags=re.S)

    # 2) drop the very first <h1> (the site header carries the title)
    html = re.sub(r"<h1\b[^>]*>.*?</h1>\s*", "", html, count=1, flags=re.S)

    # 2b) drop the standalone bold subtitle that follows it (the hero carries it)
    html = re.sub(r"^\s*<p><strong>.*?</strong></p>\s*", "", html, count=1, flags=re.S)

    # 3) drop the language-switcher paragraph
    html = re.sub(r"<p>(?:(?!</p>).)*?(?:README_EN\.md|README\.md)(?:(?!</p>).)*?</p>\s*",
                  "", html, count=1, flags=re.S)

    # 4) rewrite links
    html = html.replace('href="README_EN.md"', 'href="?lang=en" data-langlink="en"')
    html = html.replace('href="README.md"', 'href="?lang=zh" data-langlink="zh"')
    html = re.sub(r'href="(?!https?:|#|\?)([^"]+\.md)"',
                  lambda m: f'href="https://github.com/{REPO}/blob/main/{m.group(1)}"', html)

    # 4b) markdown-it percent-encodes fragments; decode them so they match the raw
    #     UTF-8 heading ids exactly (browsers cope either way, but exact is cleaner)
    html = re.sub(r'href="#([^"]+)"', lambda m: 'href="#' + unquote(m.group(1)) + '"', html)

    # 5) wrap tables so they can scroll horizontally on narrow screens
    html = html.replace("<table>", '<div class="tw"><table>').replace("</table>", "</table></div>")
    return html


# ------------------------------------------------------------------ page
PAGE = """<!DOCTYPE html>
<html lang="zh-CN" data-lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ComfyUI on an RTX 5090 Laptop — image, video and audio models</title>
<meta name="description" content="A field manual for running the newest image, video and audio generation models on a 24 GB RTX 5090 Laptop with ComfyUI, including a controlled A/B proving NVFP4 is the best quantization format.">
<style>
:root{
  --bg:#ffffff; --bg2:#f8fafc; --bg3:#f1f5f9;
  --fg:#0f172a; --fg2:#475569; --fg3:#94a3b8;
  --line:#e2e8f0; --line2:#cbd5e1;
  --accent:#2563eb; --accent2:#059669; --amber:#d97706; --red:#dc2626;
  --code-bg:#f1f5f9; --card:#ffffff;
  --shadow:0 1px 2px rgba(15,23,42,.06),0 8px 24px rgba(15,23,42,.04);
}
html[data-theme="dark"]{
  --bg:#0e1116; --bg2:#141922; --bg3:#1a2029;
  --fg:#e7edf5; --fg2:#a9b6c6; --fg3:#6b7889;
  --line:#252d38; --line2:#333d4b;
  --accent:#6ea8ff; --accent2:#3ecf8e; --amber:#e5a441; --red:#ef6b6b;
  --code-bg:#161c25; --card:#ffffff;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px rgba(0,0,0,.25);
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{
  margin:0;background:var(--bg);color:var(--fg);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans SC","PingFang SC","Hiragino Sans GB","Microsoft YaHei",Roboto,Helvetica,Arial,sans-serif;
  font-size:16px;line-height:1.78;-webkit-font-smoothing:antialiased;
}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
header.top{
  position:sticky;top:0;z-index:20;background:var(--bg);
  background:color-mix(in srgb,var(--bg) 88%,transparent);
  -webkit-backdrop-filter:saturate(180%) blur(12px);
  backdrop-filter:saturate(180%) blur(12px);border-bottom:1px solid var(--line);
}
.top-in{max-width:940px;margin:0 auto;padding:10px 22px;display:flex;align-items:center;gap:14px}
.brand{font-weight:650;font-size:14.5px;letter-spacing:.01em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.brand span{color:var(--fg3);font-weight:450}
.spacer{flex:1}
.seg{display:flex;border:1px solid var(--line2);border-radius:9px;overflow:hidden}
.seg button{
  font:inherit;font-size:12.5px;font-weight:600;padding:5px 12px;cursor:pointer;
  background:transparent;color:var(--fg2);border:0;line-height:1.5;
}
.seg button[aria-pressed="true"]{background:var(--fg);color:var(--bg)}
.icobtn{
  font:inherit;font-size:12.5px;padding:5px 10px;cursor:pointer;border:1px solid var(--line2);
  border-radius:9px;background:transparent;color:var(--fg2);line-height:1.5;
}
.icobtn:hover{border-color:var(--fg3)}
main{max-width:940px;margin:0 auto;padding:34px 22px 90px}
.hero{margin:0 0 30px}
.hero h1{font-size:clamp(26px,4.2vw,38px);line-height:1.22;margin:0 0 12px;letter-spacing:-.02em;font-weight:680}
.hero p.lede{font-size:17.5px;color:var(--fg2);margin:0 0 16px;line-height:1.65}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 6px}
.chip{
  font-size:12.5px;font-weight:600;padding:4px 11px;border-radius:999px;
  background:var(--bg3);color:var(--fg2);border:1px solid var(--line)
}
.doc h1{font-size:27px;margin:2.2rem 0 .9rem;letter-spacing:-.015em}
.doc h2{font-size:22px;margin:2.6rem 0 .9rem;padding-bottom:.45rem;border-bottom:1px solid var(--line);letter-spacing:-.01em}
.doc h3{font-size:18px;margin:2rem 0 .7rem}
.doc h4{font-size:16px;margin:1.6rem 0 .6rem}
.doc p{margin:0 0 1.05rem}
.doc ul,.doc ol{margin:0 0 1.1rem;padding-left:1.35rem}
.doc li{margin:.32rem 0}
.doc li>ul,.doc li>ol{margin:.35rem 0 .35rem}
.doc hr{border:0;border-top:1px solid var(--line);margin:2.4rem 0}
.doc blockquote{
  margin:1.3rem 0;padding:.9rem 1.15rem;background:var(--bg2);
  border-left:3px solid var(--accent);border-radius:0 8px 8px 0;color:var(--fg2)
}
.doc blockquote p:last-child{margin-bottom:0}
.doc code{
  font-family:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,"Liberation Mono",monospace;
  font-size:.885em;background:var(--code-bg);padding:.14em .42em;border-radius:5px;
  border:1px solid var(--line)
}
.doc pre{
  background:var(--bg2);border:1px solid var(--line);border-radius:11px;
  padding:14px 16px;overflow:auto;margin:0 0 1.2rem;line-height:1.6
}
.doc pre code{background:none;border:0;padding:0;font-size:12.8px}
.tw{overflow-x:auto;margin:0 0 1.3rem;-webkit-overflow-scrolling:touch}
.doc table{border-collapse:collapse;width:100%;font-size:14px;min-width:520px}
.doc th,.doc td{border:1px solid var(--line);padding:8px 11px;text-align:left;vertical-align:top}
.doc th{background:var(--bg3);font-weight:640;white-space:nowrap}
.doc tr:nth-child(even) td{background:var(--bg2)}
.doc img{
  max-width:100%;height:auto;display:block;margin:1.5rem auto;border-radius:12px;
  background:var(--card);box-shadow:var(--shadow)
}
.doc details{border:1px solid var(--line);border-radius:11px;padding:10px 15px;margin:0 0 1.3rem;background:var(--bg2)}
.doc summary{cursor:pointer;font-weight:600;font-size:14.5px}
.doc details[open] summary{margin-bottom:.7rem}
[data-lang="zh"] .i-en{display:none}
[data-lang="en"] .i-zh{display:none}
footer{border-top:1px solid var(--line);margin-top:60px;padding:22px 0 0;color:var(--fg3);font-size:13px}
@media(max-width:640px){
  body{font-size:15.5px}
  main{padding:24px 16px 70px}
  .top-in{padding:9px 16px;gap:8px}
  .brand span{display:none}
  .doc table{min-width:460px}
}
@media print{header.top,.seg,.icobtn{display:none}main{padding:0}}
</style>
</head>
<body>
<header class="top">
  <div class="top-in">
    <div class="brand i-zh">RTX 5090 笔记本 · ComfyUI 生成模型实战<span> — 图像 / 视频 / 音频</span></div>
    <div class="brand i-en">ComfyUI Generative Models on an RTX 5090 Laptop<span> — image / video / audio</span></div>
    <div class="spacer"></div>
    <div class="seg" role="group" aria-label="Language">
      <button id="btn-zh" onclick="__lang('zh')" aria-pressed="true">中文</button>
      <button id="btn-en" onclick="__lang('en')" aria-pressed="false">EN</button>
    </div>
    <button class="icobtn" id="btn-theme" onclick="__theme()" title="Toggle theme">Aa</button>
  </div>
</header>
<main>
  <div class="hero">
    <div class="i-zh">
      <h1>用 ComfyUI 在 RTX 5090 笔记本上跑通最新的图像 / 视频 / 音乐生成模型</h1>
      <p class="lede">一份从选型、下载、搭图、实测到定论的完整手册。含一个受控实验，证明 NVFP4 是这台机器上的最佳量化格式。</p>
    </div>
    <div class="i-en">
      <h1>Running the newest image, video and audio models on an RTX 5090 Laptop with ComfyUI</h1>
      <p class="lede">A complete field manual: model selection, downloads, graph construction, measurement, and the verdict — including a controlled experiment proving NVFP4 is the best quantization here.</p>
    </div>
    <div class="chips">
      <span class="chip">RTX 5090 Laptop · 24 GB · sm_120</span>
      <span class="chip">ComfyUI 0.37.0</span>
      <span class="chip">34 files · 125.6 GB</span>
      <span class="chip">NVFP4 +22% / −27%</span>
    </div>
  </div>
  <article class="doc i-zh">__BODY_ZH__</article>
  <article class="doc i-en">__BODY_EN__</article>
  <footer>
    <span class="i-zh">所有数据均为本机实测。源码与原始数据：<a href="https://github.com/__REPO__">github.com/__REPO__</a></span>
    <span class="i-en">Every number here is measured on the machine. Source and raw data: <a href="https://github.com/__REPO__">github.com/__REPO__</a></span>
    <br>MIT License.
  </footer>
</main>
<script>
(function(){
  var ZH='zh', EN='en';
  function detect(){
    var q=new URLSearchParams(location.search).get('lang');
    if(q===ZH||q===EN) return {l:q,pin:true};
    try{ var s=localStorage.getItem('cqp-lang'); if(s===ZH||s===EN) return {l:s,pin:false}; }catch(e){}
    var n=(navigator.language||navigator.userLanguage||'en').toLowerCase();
    var list=(navigator.languages||[]).join(',').toLowerCase();
    return {l:(n.indexOf('zh')===0||list.indexOf('zh')>-1)?ZH:EN,pin:false};
  }
  function theme(){
    try{ return localStorage.getItem('cqp-theme'); }catch(e){ return null; }
  }
  function applyTheme(t){
    document.documentElement.setAttribute('data-theme',t);
    var m=document.querySelector('meta[name="theme-color"]');
    if(!m){ m=document.createElement('meta'); m.name='theme-color'; document.head.appendChild(m); }
    m.content = t==='dark' ? '#0e1116' : '#ffffff';
  }
  var d=detect();
  window.__lang=function(l){
    try{ localStorage.setItem('cqp-lang',l); }catch(e){}
    document.documentElement.setAttribute('data-lang',l);
    document.documentElement.setAttribute('lang', l===ZH?'zh-CN':'en');
    document.getElementById('btn-zh').setAttribute('aria-pressed', l===ZH);
    document.getElementById('btn-en').setAttribute('aria-pressed', l===EN);
    document.title = l===ZH
      ? 'RTX 5090 笔记本 · ComfyUI 图像/视频/音频生成模型实战手册'
      : 'ComfyUI on an RTX 5090 Laptop — image, video and audio models';
  };
  window.__theme=function(){
    var cur=document.documentElement.getAttribute('data-theme')==='dark'?'light':'dark';
    try{ localStorage.setItem('cqp-theme',cur); }catch(e){}
    applyTheme(cur);
  };
  // initial language
  window.__lang(d.l);
  // initial theme: stored choice, else follow the OS
  var t=theme();
  if(!t){ t = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark':'light'; }
  applyTheme(t);
  if(window.matchMedia){
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change',function(e){
      if(!theme()) applyTheme(e.matches?'dark':'light');
    });
  }
  // in-page language links
  document.querySelectorAll('a[data-langlink]').forEach(function(a){
    a.addEventListener('click',function(ev){
      ev.preventDefault(); window.__lang(a.getAttribute('data-langlink'));
      window.scrollTo({top:0,behavior:'smooth'}); history.replaceState(null,'','?lang='+a.getAttribute('data-langlink'));
    });
  });
})();
</script>
</body>
</html>
"""


def main():
    zh = render(os.path.join(ROOT, "README.md"))
    en = render(os.path.join(ROOT, "README_EN.md"))
    page = (PAGE.replace("__BODY_ZH__", zh)
                .replace("__BODY_EN__", en)
                .replace("__REPO__", REPO))
    out = os.path.join(ROOT, "index.html")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(page)
    print(f"wrote {out}  ({len(page)/1024:.1f} KB)   zh={len(zh)/1024:.1f} KB  en={len(en)/1024:.1f} KB")


if __name__ == "__main__":
    main()
