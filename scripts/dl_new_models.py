# -*- coding: utf-8 -*-
"""最新模型线批量下载 v2（modelscope 优先，并行 4 通道，断点续传 + 自动重连）。

选型依据：以「DiT 单体能塞进 24GB」为硬门槛，逐步筛掉放不下的：
  ❌ FLUX.2-dev        DiT fp8mixed 35.46GB  → 放不下，改走 Klein 4B
  ❌ LTX-2.3           DiT fp8       29.15GB  → 放不下
  ⚠️ LTX-2.5           Lightricks 仓库 gated（401）→ 需先在 HF 接受许可
  ✅ Z-Image-Turbo     int8_convrot   6.20GB
  ✅ FLUX.2 Klein 4B   distilled      7.75GB
  ✅ HunyuanVideo 1.5  fp16          16.65GB
  ⚠️ MiniMax H3        int8 pruned   20.97GB  （+ 15.69GB NVFP4 文本编码器 → 必须 offload）

源速度实测（2026-09-22）：modelscope 11.0-11.8 MB/s > hf-mirror 2.1-4.2 > huggingface 1.6-2.2
"""
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, r"D:\aigc")
import dl_models                                       # noqa: E402
from dl_models import ROOT, fetch, log                # noqa: E402

# (host, 路径模板) —— modelscope 用 resolve/master；三级回退
SOURCES = [
    ("https://www.modelscope.cn/models/%s/resolve/master/%s", "modelscope"),
    ("https://hf-mirror.com/%s/resolve/main/%s", "hf-mirror"),
    ("https://huggingface.co/%s/resolve/main/%s", "huggingface"),
]

# (优先级, 分组, 本地子目录, 文件名, 仓库, 仓库内路径)
MANIFEST = [
    # ============ 优先级 1：MiniMax H3（用户点名）============
    (1, "MiniMax H3", "diffusion_models", "minimax_h3_fl2va_pruned_int8_convrot.safetensors",
     "Comfy-Org/MiniMax-H3", "diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors"),
    (1, "MiniMax H3", "text_encoders", "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
     "Comfy-Org/MiniMax-H3", "text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"),
    (1, "MiniMax H3", "vae", "minimax_h3_video_vae_fp16.safetensors",
     "Comfy-Org/MiniMax-H3", "vae/minimax_h3_video_vae_fp16.safetensors"),
    (1, "MiniMax H3", "vae", "minimax_h3_audio_vae_fp32.safetensors",
     "Comfy-Org/MiniMax-H3", "vae/minimax_h3_audio_vae_fp32.safetensors"),
    (1, "MiniMax H3", "loras", "minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors",
     "Comfy-Org/MiniMax-H3", "loras/minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors"),

    # ============ 优先级 2：Z-Image-Turbo（快、小、新）============
    (2, "Z-Image-Turbo", "diffusion_models", "z_image_turbo_int8_convrot.safetensors",
     "Comfy-Org/z_image_turbo", "split_files/diffusion_models/z_image_turbo_int8_convrot.safetensors"),
    (2, "Z-Image-Turbo", "vae", "ae.safetensors",
     "Comfy-Org/z_image_turbo", "split_files/vae/ae.safetensors"),
    (2, "共用·编码器", "text_encoders", "qwen_3_4b.safetensors",
     "Comfy-Org/z_image_turbo", "split_files/text_encoders/qwen_3_4b.safetensors"),

    # ============ 优先级 3：FLUX.2 Klein 4B（复用上面的 qwen_3_4b）============
    # 注意：bf16 版（7.75GB）已从清单移除 —— 官方蓝图实际用的是 fp8 版，
    # 且 BFL 官方 fp8 单文件只有 4.07GB（见 dl_new_models_2.py），bf16 属冗余。
    (3, "FLUX.2 Klein 4B", "vae", "flux2-vae.safetensors",
     "Comfy-Org/flux2-dev", "split_files/vae/flux2-vae.safetensors"),

    # ============ 优先级 4：HunyuanVideo 1.5（编码器复用已有 qwen_2.5_vl_7b_fp8_scaled）============
    (4, "HunyuanVideo 1.5", "diffusion_models", "hunyuanvideo1.5_720p_t2v_fp16.safetensors",
     "Comfy-Org/HunyuanVideo_1.5_repackaged", "split_files/diffusion_models/hunyuanvideo1.5_720p_t2v_fp16.safetensors"),
    (4, "HunyuanVideo 1.5", "text_encoders", "byt5_small_glyphxl_fp16.safetensors",
     "Comfy-Org/HunyuanVideo_1.5_repackaged", "split_files/text_encoders/byt5_small_glyphxl_fp16.safetensors"),
    (4, "HunyuanVideo 1.5", "vae", "hunyuanvideo15_vae_fp16.safetensors",
     "Comfy-Org/HunyuanVideo_1.5_repackaged", "split_files/vae/hunyuanvideo15_vae_fp16.safetensors"),
]

TIMEOUT_MIN = 90.0     # 硬上限：超过就停下交付已完成部分


def head_size(repo, rel):
    """取精确字节数 + 可用 URL 列表（modelscope 优先）。

    modelscope 不支持 HEAD，但支持 Range，用 bytes=0-0 读 Content-Range 拿总大小。
    """
    import urllib.request as _ur
    size, urls = None, []
    for tpl, src in SOURCES:
        u = tpl % (repo, rel)
        try:
            req = _ur.Request(u)
            req.add_header("Range", "bytes=0-0")
            r = dl_models.opener.open(req, timeout=30)
            cr = r.headers.get("Content-Range")   # bytes 0-0/1956192992
            if cr and "/" in cr:
                tot = int(cr.rsplit("/", 1)[1])
                if size is None:
                    size = tot
                elif tot != size:
                    log("   !! %s 两源大小不一致（%d vs %d），以本地期望为准" % (rel, tot, size))
                urls.append(u)
        except Exception:
            continue
    return size, urls


def fetch_multi(urls, dest, expected):
    """依次尝试多个源（modelscope → hf-mirror → huggingface），任一个成功即返回。"""
    for u in urls:
        if "modelscope" in u:
            src = "modelscope"
        elif "hf-mirror" in u:
            src = "hf-mirror"
        else:
            src = "huggingface"
        log("   -> 从 %s 下载 %s" % (src, os.path.basename(dest)))
        if fetch(u, dest, expected):
            return True, src
        log("   !! %s 源失败，切换下一个源" % src)
        # 大小不对说明该源文件有问题，丢掉 .part 再试
        tmp = dest + ".part"
        if os.path.exists(tmp) and os.path.getsize(tmp) > expected:
            try:
                os.remove(tmp)
            except Exception:
                pass
    return False, "-"


def main():
    log("=" * 70)
    log("最新模型线批量下载启动（modelscope 优先，4 通道并行）")

    jobs, missing = [], []
    for pr, grp, sub, name, repo, rel in MANIFEST:
        dest = os.path.join(ROOT, sub, name)
        size, urls = head_size(repo, rel)
        if size is None or not urls:
            missing.append((grp, name))
            log("   !! %-56s 两源均取不到大小" % name)
            continue
        jobs.append((pr, size, grp, sub, name, dest, urls))

    if missing:
        log("无法定位 %d 个文件：%s" % (len(missing), ", ".join(n for _, n in missing)))

    total = sum(j[1] for j in jobs)
    log("合计 %d 个文件 / %.2f GB" % (len(jobs), total / 1e9))

    pending = []
    for pr, size, grp, sub, name, dest, urls in jobs:
        if os.path.exists(dest) and os.path.getsize(dest) == size:
            log("   [skip] 已完成 %s" % name)
        else:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            pending.append((pr, size, grp, sub, name, dest, urls))
    # 先下优先级高的；同优先级先下大的（避免长尾）
    pending.sort(key=lambda x: (x[0], -x[1]))

    if not pending:
        log("全部已完成，无需下载")
        return 0

    todo_gb = sum(p[1] for p in pending) / 1e9
    log("待下载 %d 个文件，共 %.2f GB（预计 50-75 分钟，硬上限 %.0f 分钟）"
        % (len(pending), todo_gb, TIMEOUT_MIN))
    t0 = time.time()
    results = []

    def work(j):
        pr, size, grp, sub, name, dest, urls = j
        if (time.time() - t0) / 60 > TIMEOUT_MIN:
            return (grp, name, False, 0.0, "timeout")
        t = time.time()
        ok, src = fetch_multi(urls, dest, size)
        return (grp, name, ok, time.time() - t, src)

    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(work, j) for j in pending]
        for f in as_completed(futs):
            grp, name, ok, dt, src = f.result()
            results.append((grp, name, ok, dt, src))
            log("%s [%-10s] %-30s %-54s %6.1f 分"
                % ("OK  " if ok else "FAIL", src, grp, name, dt / 60))

    log("=" * 70)
    bad = [r for r in results if not r[2]]
    log("全部结束：成功 %d / %d，总用时 %.1f 分"
        % (len(results) - len(bad), len(results), (time.time() - t0) / 60))
    for grp, name, ok, dt, src in bad:
        log("  失败: [%s] %s（最后源 %s）" % (grp, name, src))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
