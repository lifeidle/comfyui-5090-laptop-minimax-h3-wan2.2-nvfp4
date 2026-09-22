# -*- coding: utf-8 -*-
"""probe_more.py — 探测待下载模型的体积（Range 请求，不下载），并测源速。

用法: python probe_more.py
"""
import urllib.request, concurrent.futures, time, json, os, sys

# (repo, path_in_repo, dest_folder)
MANIFEST = [
    # ---- ACE-Step 1.5 (Apache 2.0, ComfyUI 原生) ----
    ("Comfy-Org/ace_step_1.5_ComfyUI_files", "split_files/diffusion_models/acestep_v1.5_turbo.safetensors", "diffusion_models"),
    ("Comfy-Org/ace_step_1.5_ComfyUI_files", "split_files/diffusion_models/acestep_v1.5_xl_turbo_bf16.safetensors", "diffusion_models"),
    ("Comfy-Org/ace_step_1.5_ComfyUI_files", "split_files/text_encoders/qwen_0.6b_ace15.safetensors", "text_encoders"),
    ("Comfy-Org/ace_step_1.5_ComfyUI_files", "split_files/text_encoders/qwen_4b_ace15.safetensors", "text_encoders"),
    ("Comfy-Org/ace_step_1.5_ComfyUI_files", "split_files/vae/ace_1.5_vae.safetensors", "vae"),
    # ---- YuE2 (cc-by-nc) ----
    ("Comfy-Org/YuE2", "checkpoints/yue2_3b_int8_convrot.safetensors", "checkpoints"),
    # ---- MiniMax Music 3 ----
    ("Comfy-Org/MiniMax-Music-3", "diffusion_models/minimax_music3_dit_int8_convrot.safetensors", "diffusion_models"),
    ("Comfy-Org/MiniMax-Music-3", "text_encoders/minimax_music3_text_encoder_pruned_int8_convrot.safetensors", "text_encoders"),
    ("Comfy-Org/MiniMax-Music-3", "vae/minimax_music3_dav.safetensors", "vae"),
    # ---- Stable Audio 3 Medium ----
    ("Comfy-Org/stable-audio-3", "checkpoints/stable_audio_3_medium.safetensors", "checkpoints"),
    # ---- Wan 2.2 14B MoE (t2v) + LightX2V 4step LoRA ----
    ("Comfy-Org/Wan_2.2_ComfyUI_Repackaged", "split_files/diffusion_models/wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors", "diffusion_models"),
    ("Comfy-Org/Wan_2.2_ComfyUI_Repackaged", "split_files/diffusion_models/wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors", "diffusion_models"),
    ("Comfy-Org/Wan_2.2_ComfyUI_Repackaged", "split_files/loras/wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors", "loras"),
    ("Comfy-Org/Wan_2.2_ComfyUI_Repackaged", "split_files/loras/wan2.2_t2v_lightx2v_4steps_lora_v1.1_low_noise.safetensors", "loras"),
]

SOURCES = [
    ("modelscope", "https://www.modelscope.cn/models/{repo}/resolve/master/{path}"),
    ("hf-mirror",  "https://hf-mirror.com/{repo}/resolve/main/{path}"),
]


def opener():
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def probe(url, timeout=12):
    req = urllib.request.Request(url, headers={"Range": "bytes=0-0", "User-Agent": "probe/1.0"})
    t0 = time.time()
    try:
        with opener().open(req, timeout=timeout) as r:
            cr = r.headers.get("Content-Range") or ""
            total = int(cr.split("/")[-1]) if "/" in cr else int(r.headers.get("Content-Length", 0))
            return total, time.time() - t0
    except Exception as e:
        return None, str(e)[:60]


def main():
    rows = []
    for repo, path, dest in MANIFEST:
        name = os.path.basename(path)
        best = None
        for src, tpl in SOURCES:
            url = tpl.format(repo=repo, path=path)
            size, dt = probe(url)
            if size:
                best = (src, size)
                break
        if best:
            rows.append((name, dest, best[1] / 1e9, best[0]))
        else:
            rows.append((name, dest, None, "FAILED"))
    rows.sort(key=lambda r: -(r[2] or 0))
    print(f"{'file':62s} {'dest':18s} {'GB':>8s}  src")
    tot = 0.0
    for n, d, g, s in rows:
        gs = f"{g:8.2f}" if g else "     ???"
        if g: tot += g
        print(f"{n:62s} {d:18s} {gs}  {s}")
    print(f"\n合计 ≈ {tot:.1f} GB")
    print(f"@22 MB/s ≈ {tot*1000/22/60:.1f} 分钟   @4 路并发(~80MB/s) ≈ {tot*1000/80/60:.1f} 分钟")


if __name__ == "__main__":
    main()
