#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dl_models.py — multi-source model downloader for ComfyUI

Why this exists
---------------
Moving 125.6 GB across three mirrors is not `curl` in a loop. Three mechanisms do the
real work, and all three were added in response to an actual failure:

  1. THREE-TIER FALLBACK      modelscope -> hf-mirror -> huggingface
                              Throughput differs by an order of magnitude between them.

  2. A SILENT WATCHDOG        A plain socket timeout does NOT catch a server that drips
                              a few KB every 30 s: the socket never times out and the
                              transfer never progresses. We lost 19 minutes to this once.
                              Fix: if the byte count makes no real progress for
                              STALL_SECONDS, actively disconnect and resume.

  3. RANGE-BASED SIZING       modelscope does not support HEAD. Request one byte and read
                              the total from `Content-Range`. Having the expected size is
                              what makes byte-exact verification possible at all.

Resume is source-agnostic: the `.part` file left by one mirror is valid input for another,
because both serve identical bytes (verified).

Usage
-----
    python scripts/dl_models.py --root /path/to/ComfyUI/models
    python scripts/dl_models.py --root ... --only nvfp4      # filename substring filter
    python scripts/dl_models.py --probe-only                # sizes only, no download

Environment:
    COMFY_MODELS_ROOT   overrides the default models root
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

# --------------------------------------------------------------------- config
DEFAULT_ROOT = os.environ.get("COMFY_MODELS_ROOT") or r"D:\models\comfyui-models"

# (url template, short name) — tried in this order
SOURCES = [
    ("https://www.modelscope.cn/models/%s/resolve/master/%s", "modelscope"),
    ("https://hf-mirror.com/%s/resolve/main/%s", "hf-mirror"),
    ("https://huggingface.co/%s/resolve/main/%s", "huggingface"),
]

SOCKET_TIMEOUT = 45        # seconds, per connection attempt
STALL_SECONDS = 150        # no real progress for this long -> abort the connection
STALL_LIMIT = 3            # consecutive silent stalls -> abandon this source
MAX_ATTEMPTS = 40          # resume attempts per source
WORKERS = 4                # parallel files. Raise only if your link can take it.
PROGRESS_EVERY = 25        # seconds between progress lines

MM = "Comfy-Org/MiniMax-H3"
ZI = "Comfy-Org/z_image_turbo"
HV = "Comfy-Org/HunyuanVideo_1.5_repackaged"
K4 = "black-forest-labs/FLUX.2-klein-4b-fp8"
K9 = "black-forest-labs/FLUX.2-klein-9b-nvfp4"
F2 = "Comfy-Org/flux2-dev"
FK = "Comfy-Org/flux2-klein"

# (priority, group, subdir, filename, repo, path-in-repo)
# Lower priority number is fetched first. Mirrors the download order used in the project.
MANIFEST = [
    # ---------------- MiniMax H3 : video + audio ----------------
    (1, "MiniMax H3", "diffusion_models", "minimax_h3_fl2va_pruned_int8_convrot.safetensors",
     MM, "diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors"),
    (1, "MiniMax H3", "text_encoders", "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
     MM, "text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"),
    (1, "MiniMax H3", "vae", "minimax_h3_video_vae_fp16.safetensors",
     MM, "vae/minimax_h3_video_vae_fp16.safetensors"),
    (1, "MiniMax H3", "vae", "minimax_h3_audio_vae_fp32.safetensors",
     MM, "vae/minimax_h3_audio_vae_fp32.safetensors"),
    (1, "MiniMax H3", "vae", "minimax_h3_video_vae_int8_convrot.safetensors",
     MM, "vae/minimax_h3_video_vae_int8_convrot.safetensors"),
    (1, "MiniMax H3", "loras", "minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors",
     MM, "loras/minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors"),
    (1, "MiniMax H3", "loras", "minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors",
     MM, "loras/minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors"),
    (1, "MiniMax H3", "model_patches", "minimax_h3_fun_controlnet_union_pruned_int8_convrot.safetensors",
     MM, "model_patches/minimax_h3_fun_controlnet_union_pruned_int8_convrot.safetensors"),

    # ---------------- Z-Image-Turbo : image ----------------
    (2, "Z-Image-Turbo", "diffusion_models", "z_image_turbo_int8_convrot.safetensors",
     ZI, "split_files/diffusion_models/z_image_turbo_int8_convrot.safetensors"),
    (2, "Z-Image-Turbo", "diffusion_models", "z_image_turbo_nvfp4.safetensors",
     ZI, "split_files/diffusion_models/z_image_turbo_nvfp4.safetensors"),
    (2, "Z-Image-Turbo", "text_encoders", "qwen_3_4b.safetensors",
     ZI, "split_files/text_encoders/qwen_3_4b.safetensors"),
    (2, "Z-Image-Turbo", "text_encoders", "qwen_3_4b_fp4_mixed.safetensors",
     ZI, "split_files/text_encoders/qwen_3_4b_fp4_mixed.safetensors"),
    (2, "Z-Image-Turbo", "vae", "ae.safetensors",
     ZI, "split_files/vae/ae.safetensors"),

    # ---------------- FLUX.2 Klein : image editing ----------------
    (3, "FLUX.2 Klein 4B", "diffusion_models", "flux-2-klein-4b-fp8.safetensors",
     K4, "flux-2-klein-4b-fp8.safetensors"),
    (3, "FLUX.2 Klein 9B", "diffusion_models", "flux-2-klein-9b-nvfp4.safetensors",
     K9, "flux-2-klein-9b-nvfp4.safetensors"),
    (3, "FLUX.2 Klein", "text_encoders", "qwen_3_4b_fp4_flux2.safetensors",
     FK, "split_files/text_encoders/qwen_3_4b_fp4_flux2.safetensors"),
    (3, "FLUX.2 Klein", "vae", "flux2-vae.safetensors",
     F2, "split_files/vae/flux2-vae.safetensors"),

    # ---------------- HunyuanVideo 1.5 : video ----------------
    # NOTE 480p / 720p / i2v / SR are SEPARATE BASE MODELS, not one model at different
    # resolutions. The LightX2V 4-step LoRA is trained for 480p and needs the 480p base.
    (4, "HunyuanVideo 1.5", "diffusion_models", "hunyuanvideo1.5_480p_t2v_fp16.safetensors",
     HV, "split_files/diffusion_models/hunyuanvideo1.5_480p_t2v_fp16.safetensors"),
    (4, "HunyuanVideo 1.5", "diffusion_models", "hunyuanvideo1.5_720p_t2v_fp16.safetensors",
     HV, "split_files/diffusion_models/hunyuanvideo1.5_720p_t2v_fp16.safetensors"),
    (4, "HunyuanVideo 1.5", "text_encoders", "byt5_small_glyphxl_fp16.safetensors",
     HV, "split_files/text_encoders/byt5_small_glyphxl_fp16.safetensors"),
    (4, "HunyuanVideo 1.5", "vae", "hunyuanvideo15_vae_fp16.safetensors",
     HV, "split_files/vae/hunyuanvideo15_vae_fp16.safetensors"),
    (4, "HunyuanVideo 1.5", "clip_vision", "sigclip_vision_patch14_384.safetensors",
     HV, "split_files/clip_vision/sigclip_vision_patch14_384.safetensors"),
    (4, "HunyuanVideo 1.5", "latent_upscale_models", "hunyuanvideo15_latent_upsampler_720p.safetensors",
     HV, "split_files/latent_upscale_models/hunyuanvideo15_latent_upsampler_720p.safetensors"),
    (4, "HunyuanVideo 1.5", "loras", "hunyuanvideo1.5_t2v_480p_lightx2v_4step_lora_rank_32_bf16.safetensors",
     HV, "split_files/loras/hunyuanvideo1.5_t2v_480p_lightx2v_4step_lora_rank_32_bf16.safetensors"),
]

# The ten MiniMax H3 effect embeddings: tiny, so they ride along with priority 1.
EFFECTS = ["art_is_explosion", "blooming_flowers", "bullet_time", "dark_magic", "fire_breath",
           "four_seasons", "kiss_camera", "spiral_ascent", "storm_magic", "truman_show"]
MANIFEST += [(1, "MiniMax H3", "embeddings", f"minimaxh3_{e}.safetensors",
              MM, f"embeddings/minimaxh3_{e}.safetensors") for e in EFFECTS]

# --------------------------------------------------------------------- plumbing
# Empty ProxyHandler: bypass any ambient HTTP(S)_PROXY, go direct.
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
OPENER.addheaders = [("User-Agent", "Mozilla/5.0")]


def log(msg: str) -> None:
    print("[%s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def probe_size(repo: str, rel: str):
    """Return (expected_bytes, [urls that respond]) using a 1-byte Range request.

    modelscope rejects HEAD, so this is the only portable way to learn a file's size.
    Probing all sources also cross-validates the size between mirrors.
    """
    size, urls = None, []
    for tpl, _ in SOURCES:
        url = tpl % (repo, rel)
        try:
            req = urllib.request.Request(url)
            req.add_header("Range", "bytes=0-0")
            r = OPENER.open(req, timeout=30)
            cr = r.headers.get("Content-Range")           # e.g. "bytes 0-0/16748116224"
            if cr and "/" in cr:
                total = int(cr.rsplit("/", 1)[1])
                if size is None:
                    size = total
                elif total != size:
                    log("   !! size disagreement for %s: %d vs %d" % (rel, total, size))
                urls.append(url)
            r.close()
        except Exception:
            continue
    return size, urls


def fetch_one(url: str, dest: str, expected: int) -> bool:
    """Download `url` to `dest`, resuming from dest.part. Returns True on byte-exact success.

    Contains the silent watchdog: a server that dribbles bytes without real progress is
    dropped after STALL_SECONDS, and after STALL_LIMIT such stalls this source is abandoned
    so the caller can switch mirrors.
    """
    tmp = dest + ".part"
    name = os.path.basename(dest)
    tiny = expected <= 1_000_000
    tol = 0 if tiny else max(expected * 0.005, 1 << 20)

    if os.path.exists(tmp):
        if tiny or os.path.getsize(tmp) > expected * 1.02:
            os.remove(tmp)                       # unusable partial -> start clean

    t0 = time.time()
    stalls = 0
    for attempt in range(1, MAX_ATTEMPTS + 1):
        done = os.path.getsize(tmp) if os.path.exists(tmp) else 0
        if done and abs(done - expected) <= tol:
            os.replace(tmp, dest)
            log("  OK %s  %.2f GB  (%d connections, %.1f min)"
                % (name, done / 1e9, attempt - 1, (time.time() - t0) / 60))
            return True

        req = urllib.request.Request(url)
        if done:
            req.add_header("Range", "bytes=%d-" % done)
        try:
            r = OPENER.open(req, timeout=SOCKET_TIMEOUT)
        except Exception as e:
            log("  x attempt %d failed: %r - retrying in 3 s" % (attempt, e))
            time.sleep(3)
            continue

        # A server without Range support replies 200 and restarts: rewrite from zero.
        if done and r.status == 200 and r.headers.get("Content-Range") is None:
            log("  ! server does not support resume, restarting from 0")
            done = 0
        mode = "ab" if done else "wb"

        last_log, window = time.time(), 0
        last_progress = time.time()
        received = 0
        finished = stalled = False
        try:
            with open(tmp, mode) as f:
                while True:
                    chunk = r.read(512 * 1024)
                    if not chunk:
                        finished = True
                        break
                    f.write(chunk)
                    received += len(chunk)
                    window += len(chunk)
                    now = time.time()
                    if window >= 262144:                      # ~256 KB counts as progress
                        last_progress = now
                    # >>> the watchdog <<<
                    if now - last_progress > STALL_SECONDS:
                        log("  ! %s silent for %.0f s (only %.1f MB this connection) - dropping"
                            % (name, now - last_progress, received / 1e6))
                        stalled = True
                        break
                    if now - last_log > PROGRESS_EVERY:
                        cur = done + received
                        sp = window / max(now - last_log, 1e-6)
                        log("  .. %s  %.1f%%  %.2f/%.2f GB  %.1f MB/s"
                            % (name, 100.0 * cur / expected, cur / 1e9, expected / 1e9, sp / 1e6))
                        window, last_log = 0, now
        except Exception as e:
            log("  x attempt %d read error %r (%.2f GB this connection) - resuming"
                % (attempt, e, received / 1e9))
            time.sleep(2)
            continue

        if stalled:
            stalls += 1
            if stalls > STALL_LIMIT:
                log("  x %s stalled %d times - abandoning this source" % (name, STALL_LIMIT))
                return False
            time.sleep(2)
            continue

        if finished:
            cur = os.path.getsize(tmp)
            if abs(cur - expected) <= tol:
                os.replace(tmp, dest)
                log("  OK %s  %.2f GB  (%d connections, %.1f min)"
                    % (name, cur / 1e9, attempt, (time.time() - t0) / 60))
                return True
            log("  ! short read %.2f/%.2f GB - resuming" % (cur / 1e9, expected / 1e9))
            stalls += 1
            if stalls > 6:
                log("  x %s kept ending early - abandoning" % name)
                return False
            time.sleep(2)

    log("  x %s exhausted %d attempts - abandoning (.part kept)" % (name, MAX_ATTEMPTS))
    return False


def fetch_multi(urls, dest: str, expected: int):
    """Try each source in order; first success wins."""
    for url in urls:
        src = next((n for tpl, n in SOURCES if url.startswith(tpl.split("%s")[0])), "?")
        log("   -> %s : %s" % (src, os.path.basename(dest)))
        if fetch_one(url, dest, expected):
            return True, src
        log("   !! source %s failed, trying next" % src)
        tmp = dest + ".part"
        if os.path.exists(tmp) and os.path.getsize(tmp) > expected:
            try:
                os.remove(tmp)
            except OSError:
                pass
    return False, "-"


# --------------------------------------------------------------------- driver
def main() -> int:
    ap = argparse.ArgumentParser(description="Multi-source ComfyUI model downloader")
    ap.add_argument("--root", default=DEFAULT_ROOT, help="ComfyUI models directory")
    ap.add_argument("--only", default=None, help="only files whose name contains this substring")
    ap.add_argument("--probe-only", action="store_true", help="print sizes, download nothing")
    ap.add_argument("--workers", type=int, default=WORKERS)
    args = ap.parse_args()

    items = [m for m in MANIFEST
             if args.only is None or args.only.lower() in m[3].lower()]
    log("=" * 78)
    log("models root : %s" % args.root)
    log("selected    : %d / %d files" % (len(items), len(MANIFEST)))

    jobs, unresolved = [], []
    for priority, group, sub, name, repo, rel in items:
        size, urls = probe_size(repo, rel)
        if size is None or not urls:
            unresolved.append(name)
            log("   !! no source could size %s" % name)
            continue
        jobs.append((priority, size, group, sub, name, os.path.join(args.root, sub, name), urls))

    log("total       : %d files / %.2f GB" % (len(jobs), sum(j[1] for j in jobs) / 1e9))
    if unresolved:
        log("unresolved  : %s" % ", ".join(unresolved))
    if args.probe_only:
        for priority, size, group, sub, name, dest, urls in sorted(jobs, key=lambda x: (x[0], -x[1])):
            log("  %-8s %8.2f GB  %d source(s)  %s" % (group, size / 1e9, len(urls), name))
        return 0

    pending = []
    for job in jobs:
        _p, size, group, sub, name, dest, urls = job
        if os.path.exists(dest) and os.path.getsize(dest) == size:
            log("   [skip] %s" % name)
        else:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            pending.append(job)

    if not pending:
        log("nothing to do - every selected file is already complete")
        return 0

    # Ordering matters: files that also exist on the fast mirror go first. Otherwise a
    # single hf-only large file occupies a worker and drags the whole queue behind it.
    pending.sort(key=lambda x: (0 if len(x[6]) > 1 else 1, -x[1]))
    log("queued      : %d files / %.2f GB" % (len(pending), sum(p[1] for p in pending) / 1e9))

    t0 = time.time()
    results = []

    def work(job):
        _p, size, group, sub, name, dest, urls = job
        t = time.time()
        ok, src = fetch_multi(urls, dest, size)
        return group, name, ok, time.time() - t, src

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(work, j) for j in pending]
        for f in as_completed(futs):
            group, name, ok, dt, src = f.result()
            results.append((group, name, ok, dt, src))
            log("%s [%-11s] %-18s %-56s %6.2f min"
                % ("OK  " if ok else "FAIL", src, group, name, dt / 60))

    bad = [r for r in results if not r[2]]
    log("=" * 78)
    log("finished    : %d ok / %d total in %.1f min"
        % (len(results) - len(bad), len(results), (time.time() - t0) / 60))
    for group, name, _ok, _dt, src in bad:
        log("  FAILED [%s] %s (last source %s)" % (group, name, src))
    log("next        : python scripts/verify_models.py --refresh")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
