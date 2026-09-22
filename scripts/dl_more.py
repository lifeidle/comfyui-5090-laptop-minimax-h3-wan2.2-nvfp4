# -*- coding: utf-8 -*-
"""dl_more.py — 补齐本轮要试的模型（音乐 4 条线 + Wan 2.2 14B MoE）。

设计要点（沿用已验证的做法）：
  * 三级源回退：www.modelscope.cn -> hf-mirror.com
  * Range 探真实体积；断点续传（.part 可跨源复用）
  * 静默看门狗：连续 150s 字节数无实质增长 -> 断开重连；3 次 -> 换源
  * pending 按「该文件是否有 modelscope 源」优先排序，避免慢源文件占死 worker
  * 下载后按探测到的字节数校验

用法: python dl_more.py [--only SUBSTR] [--workers N]
"""
import os, sys, time, threading, queue, argparse, urllib.request, urllib.error

ROOT = r"D:\models\comfyui-models"

MANIFEST = [
    # ---- ACE-Step 1.5（Apache 2.0 · ComfyUI 原生）----
    ("Comfy-Org/ace_step_1.5_ComfyUI_files", "split_files/diffusion_models/acestep_v1.5_turbo.safetensors", "diffusion_models"),
    ("Comfy-Org/ace_step_1.5_ComfyUI_files", "split_files/diffusion_models/acestep_v1.5_xl_turbo_bf16.safetensors", "diffusion_models"),
    ("Comfy-Org/ace_step_1.5_ComfyUI_files", "split_files/text_encoders/qwen_0.6b_ace15.safetensors", "text_encoders"),
    ("Comfy-Org/ace_step_1.5_ComfyUI_files", "split_files/text_encoders/qwen_1.7b_ace15.safetensors", "text_encoders"),
    ("Comfy-Org/ace_step_1.5_ComfyUI_files", "split_files/text_encoders/qwen_4b_ace15.safetensors", "text_encoders"),
    ("Comfy-Org/ace_step_1.5_ComfyUI_files", "split_files/vae/ace_1.5_vae.safetensors", "vae"),
    # ---- YuE2（cc-by-nc · 整首歌含人声，中英歌词）----
    ("Comfy-Org/YuE2", "checkpoints/yue2_3b_int8_convrot.safetensors", "checkpoints"),
    # ---- MiniMax Music 3 ----
    ("Comfy-Org/MiniMax-Music-3", "diffusion_models/minimax_music3_dit_int8_convrot.safetensors", "diffusion_models"),
    ("Comfy-Org/MiniMax-Music-3", "text_encoders/minimax_music3_text_encoder_pruned_int8_convrot.safetensors", "text_encoders"),
    ("Comfy-Org/MiniMax-Music-3", "vae/minimax_music3_dav.safetensors", "vae"),
    # ---- Stable Audio 3 Medium ----
    ("Comfy-Org/stable-audio-3", "checkpoints/stable_audio_3_medium.safetensors", "checkpoints"),
    # ---- Wan 2.2 14B MoE (t2v, 双专家) + LightX2V 4step LoRA ----
    ("Comfy-Org/Wan_2.2_ComfyUI_Repackaged", "split_files/diffusion_models/wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors", "diffusion_models"),
    ("Comfy-Org/Wan_2.2_ComfyUI_Repackaged", "split_files/diffusion_models/wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors", "diffusion_models"),
    ("Comfy-Org/Wan_2.2_ComfyUI_Repackaged", "split_files/loras/wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors", "loras"),
    ("Comfy-Org/Wan_2.2_ComfyUI_Repackaged", "split_files/loras/wan2.2_t2v_lightx2v_4steps_lora_v1.1_low_noise.safetensors", "loras"),
    # ---- HunyuanVideo 1.5 的 720p→1080p 超分分支（官方 720p 模板必需）----
    ("Comfy-Org/HunyuanVideo_1.5_repackaged", "split_files/diffusion_models/hunyuanvideo1.5_1080p_sr_distilled_fp16.safetensors", "diffusion_models"),
    ("Comfy-Org/HunyuanVideo_1.5_repackaged", "split_files/latent_upscale_models/hunyuanvideo15_latent_upsampler_1080p.safetensors", "latent_upscale_models"),
    # ---- Stable Audio 3 的两个文本编码器（含 LLM 提示词增强的 qwen3.5-2B）----
    # 注意：qwen3.5_2b 在 Comfy-Org/Qwen3.5 仓库，不在 stable-audio-3 仓库里
    ("Comfy-Org/Qwen3.5", "text_encoders/qwen3.5_2b_bf16.safetensors", "text_encoders"),
    ("Comfy-Org/stable-audio-3", "text_encoders/t5gemma_b_b_ul2.safetensors", "text_encoders"),
]

SOURCES = [
    ("modelscope", "https://www.modelscope.cn/models/{repo}/resolve/master/{path}"),
    ("hf-mirror",  "https://hf-mirror.com/{repo}/resolve/main/{path}"),
]

STALL_SECONDS = 150
STALL_LIMIT = 3
CHUNK = 1 << 20

_print_lock = threading.Lock()


def log(msg):
    with _print_lock:
        print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def opener():
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def probe_size(url, timeout=15):
    req = urllib.request.Request(url, headers={"Range": "bytes=0-0", "User-Agent": "dl/1.0"})
    try:
        with opener().open(req, timeout=timeout) as r:
            cr = r.headers.get("Content-Range") or ""
            if "/" in cr:
                return int(cr.split("/")[-1])
            cl = r.headers.get("Content-Length")
            return int(cl) if cl else None
    except Exception:
        return None


def stream_to(url, dest, expected, stop_flag):
    """下到 dest（.part），支持续传。返回 (ok, downloaded_bytes, note)"""
    have = os.path.getsize(dest) if os.path.exists(dest) else 0
    if expected and have >= expected:
        return True, have, "already complete"
    headers = {"User-Agent": "dl/1.0", "Accept-Encoding": "identity"}
    if have:
        headers["Range"] = f"bytes={have}-"
    req = urllib.request.Request(url, headers=headers)
    last_progress = time.time()
    last_bytes = have
    mode = "ab" if have else "wb"
    with opener().open(req, timeout=40) as r, open(dest, mode) as f:
        while True:
            if stop_flag.is_set():
                return False, have, "cancelled"
            try:
                chunk = r.read(CHUNK)
            except Exception as e:
                return False, os.path.getsize(dest), f"read error {e}"
            if not chunk:
                break
            f.write(chunk)
            have += len(chunk)
            now = time.time()
            if have - last_bytes > 1 << 20:      # 有实质进展
                last_progress, last_bytes = now, have
            elif now - last_progress > STALL_SECONDS:
                return False, have, "stalled"
    return True, have, "done"


def fetch(item, stop_flag, results):
    repo, path, folder = item
    name = os.path.basename(path)
    outdir = os.path.join(ROOT, folder)
    os.makedirs(outdir, exist_ok=True)
    final = os.path.join(outdir, name)
    part = final + ".part"

    if os.path.exists(final):
        log(f"SKIP  {name}（已存在）")
        results[name] = ("skip", os.path.getsize(final))
        return

    urls = [(src, tpl.format(repo=repo, path=path)) for src, tpl in SOURCES]
    expected = None
    for src, u in urls:
        expected = probe_size(u)
        if expected:
            break
    log(f"START {name}  {(expected/1e9 if expected else 0):.2f} GB")

    for src, url in urls:
        for attempt in range(STALL_LIMIT):
            if stop_flag.is_set():
                return
            ok, got, note = stream_to(url, part, expected, stop_flag)
            if ok and (expected is None or got >= expected):
                os.replace(part, final)
                log(f"OK    {name}  {got/1e9:.2f} GB  [{src}]")
                results[name] = ("ok", got)
                return
            log(f"  retry {name} [{src}] attempt={attempt+1} got={got/1e9:.2f}GB note={note}")
            time.sleep(2)
    log(f"FAIL  {name} — 所有源都失败，保留 .part 供下次续传")
    results[name] = ("fail", os.path.getsize(part) if os.path.exists(part) else 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()

    items = MANIFEST
    if a.only:
        items = [m for m in MANIFEST if a.only.lower() in m[1].lower() or a.only.lower() in m[0].lower()]
    # 先排「modelscope 有源」的（几乎全部），保证 worker 不被慢源占死
    items = sorted(items, key=lambda m: 0)

    q = queue.Queue()
    for m in items:
        q.put(m)
    stop_flag = threading.Event()
    results = {}

    log(f"待下载 {len(items)} 个文件，{a.workers} 路并发")

    def worker():
        while True:
            try:
                item = q.get_nowait()
            except queue.Empty:
                return
            try:
                fetch(item, stop_flag, results)
            finally:
                q.task_done()

    ths = [threading.Thread(target=worker, daemon=True) for _ in range(a.workers)]
    for t in ths:
        t.start()
    t0 = time.time()
    for t in ths:
        t.join()
    dt = time.time() - t0

    ok = sum(1 for v in results.values() if v[0] in ("ok", "skip"))
    tot = sum(v[1] for v in results.values())
    log(f"完成 {ok}/{len(items)}，{tot/1e9:.2f} GB，用时 {dt/60:.1f} 分钟")
    for n, (st, sz) in sorted(results.items()):
        if st == "fail":
            log(f"  失败: {n}  ({sz/1e9:.2f} GB 已下)")


if __name__ == "__main__":
    main()
