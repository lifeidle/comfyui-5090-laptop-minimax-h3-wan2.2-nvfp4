# -*- coding: utf-8 -*-
"""补充下载：修正选型偏差 + 补齐 NVFP4/fp4 对比组。

依据（全部来自本机 ComfyUI 0.37.0 的官方蓝图 definitions 与仓库真实 tree）：

【MiniMax H3】
  官方蓝图 imgs/2v 用 8step turbo LoRA；主下载拿了 4step → 两个都留，做 A/B。
  fun_controlnet_union_pruned_int8（2.30GB）解锁 MiniMaxH3FunControlNetApply。
  embeddings/ 10 个特效 embedding（每个约 5MB）非常便宜，顺手拿下。
  video_vae_int8_convrot（2.81GB）比 fp16（5.21GB）省 2.4GB。

【Z-Image-Turbo】
  官方蓝图默认 bf16 DiT(12.31GB)；主下载拿了 int8_convrot(6.20GB)。
  这里再补 nvfp4(4.51GB) —— sm_120 原生 FP4，用来验证「NVFP4 是否最优」。
  编码器补 qwen_3_4b_fp4_mixed(3.48GB)，与 fp4 DiT 配成完整低比特链。

【HunyuanVideo 1.5】
  ★ 关键修正：本机 CLIPLoader 的 29 个类型里【没有】hunyuan_video_15；
    必须用 DualCLIPLoader(type=hunyuan_video_15) = qwen_2.5_vl_7b_fp8_scaled + byt5_small_glyphxl。
    两者都已有/在下载，无需重复。
  T2V 可行：HunyuanVideo15ImageToVideo 的 start_image 是 optional，不接即纯文生视频。
  补 clip_vision(0.86GB)（I2V 用）、latent_upsampler_720p(0.09GB)、LightX2V 4step LoRA(0.34GB)。

【FLUX.2 Klein】
  官方蓝图用 flux-2-klein-base-4b-fp8；本机主下载是 flux-2-klein-4b.bf16(7.75GB)。
  BFL 官方 fp8 单文件 4.07GB；另发现 klein-9b-nvfp4 仅 5.76GB（更大模型反而更小）。
"""
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, r"D:\aigc")
import dl_new_models as D                                   # noqa: E402
from dl_models import ROOT, log                             # noqa: E402

MM = "Comfy-Org/MiniMax-H3"
HV = "Comfy-Org/HunyuanVideo_1.5_repackaged"
ZI = "Comfy-Org/z_image_turbo"

SUPP = [
    # ---------- MiniMax H3 补齐 ----------
    ("MiniMax H3", "loras", "minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors",
     MM, "loras/minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors"),
    ("MiniMax H3", "model_patches", "minimax_h3_fun_controlnet_union_pruned_int8_convrot.safetensors",
     MM, "model_patches/minimax_h3_fun_controlnet_union_pruned_int8_convrot.safetensors"),
    ("MiniMax H3", "vae", "minimax_h3_video_vae_int8_convrot.safetensors",
     MM, "vae/minimax_h3_video_vae_int8_convrot.safetensors"),
    # ---------- MiniMax H3 特效 embeddings（10 个，极小）----------
    ("MiniMax H3", "embeddings", "minimaxh3_art_is_explosion.safetensors", MM, "embeddings/minimaxh3_art_is_explosion.safetensors"),
    ("MiniMax H3", "embeddings", "minimaxh3_blooming_flowers.safetensors", MM, "embeddings/minimaxh3_blooming_flowers.safetensors"),
    ("MiniMax H3", "embeddings", "minimaxh3_bullet_time.safetensors", MM, "embeddings/minimaxh3_bullet_time.safetensors"),
    ("MiniMax H3", "embeddings", "minimaxh3_dark_magic.safetensors", MM, "embeddings/minimaxh3_dark_magic.safetensors"),
    ("MiniMax H3", "embeddings", "minimaxh3_fire_breath.safetensors", MM, "embeddings/minimaxh3_fire_breath.safetensors"),
    ("MiniMax H3", "embeddings", "minimaxh3_four_seasons.safetensors", MM, "embeddings/minimaxh3_four_seasons.safetensors"),
    ("MiniMax H3", "embeddings", "minimaxh3_kiss_camera.safetensors", MM, "embeddings/minimaxh3_kiss_camera.safetensors"),
    ("MiniMax H3", "embeddings", "minimaxh3_spiral_ascent.safetensors", MM, "embeddings/minimaxh3_spiral_ascent.safetensors"),
    ("MiniMax H3", "embeddings", "minimaxh3_storm_magic.safetensors", MM, "embeddings/minimaxh3_storm_magic.safetensors"),
    ("MiniMax H3", "embeddings", "minimaxh3_truman_show.safetensors", MM, "embeddings/minimaxh3_truman_show.safetensors"),
    # ---------- Z-Image：NVFP4 / FP4 对比组 ----------
    ("Z-Image-NVFP4", "diffusion_models", "z_image_turbo_nvfp4.safetensors",
     ZI, "split_files/diffusion_models/z_image_turbo_nvfp4.safetensors"),
    ("Z-Image-NVFP4", "text_encoders", "qwen_3_4b_fp4_mixed.safetensors",
     ZI, "split_files/text_encoders/qwen_3_4b_fp4_mixed.safetensors"),
    # ---------- HunyuanVideo 1.5 补齐 ----------
    # ★ 480p t2v 主模型：LightX2V 4step LoRA 是给 480p 训练的，必须配 480p 基模，
    #   不能拿 720p 基模凑（720p/i2v/SR 都是不同的基模，不是同一模型的不同分辨率）
    ("HunyuanVideo 1.5", "diffusion_models", "hunyuanvideo1.5_480p_t2v_fp16.safetensors",
     HV, "split_files/diffusion_models/hunyuanvideo1.5_480p_t2v_fp16.safetensors"),
    ("HunyuanVideo 1.5", "clip_vision", "sigclip_vision_patch14_384.safetensors",
     HV, "split_files/clip_vision/sigclip_vision_patch14_384.safetensors"),
    ("HunyuanVideo 1.5", "latent_upscale_models", "hunyuanvideo15_latent_upsampler_720p.safetensors",
     HV, "split_files/latent_upscale_models/hunyuanvideo15_latent_upsampler_720p.safetensors"),
    ("HunyuanVideo 1.5", "loras", "hunyuanvideo1.5_t2v_480p_lightx2v_4step_lora_rank_32_bf16.safetensors",
     HV, "split_files/loras/hunyuanvideo1.5_t2v_480p_lightx2v_4step_lora_rank_32_bf16.safetensors"),
    # ---------- FLUX.2 Klein：fp8 / 9B NVFP4 ----------
    ("FLUX.2 Klein", "diffusion_models", "flux-2-klein-4b-fp8.safetensors",
     "black-forest-labs/FLUX.2-klein-4b-fp8", "flux-2-klein-4b-fp8.safetensors"),
    ("FLUX.2 Klein 9B", "diffusion_models", "flux-2-klein-9b-nvfp4.safetensors",
     "black-forest-labs/FLUX.2-klein-9b-nvfp4", "flux-2-klein-9b-nvfp4.safetensors"),
    ("FLUX.2 Klein 9B", "text_encoders", "qwen_3_4b_fp4_flux2.safetensors",
     "Comfy-Org/flux2-klein", "split_files/text_encoders/qwen_3_4b_fp4_flux2.safetensors"),
]


def main():
    log("=" * 70)
    # 可选：python dl_new_models_2.py 480p   → 只下文件名含 "480p" 的项
    only = sys.argv[1] if len(sys.argv) > 1 else None
    items = [s for s in SUPP if (only is None or only.lower() in s[2].lower())]
    log("补充下载启动（%d / %d 项%s）"
        % (len(items), len(SUPP), ("，过滤=%s" % only) if only else ""))

    jobs, missing = [], []
    for grp, sub, name, repo, rel in items:
        dest = os.path.join(ROOT, sub, name)
        size, urls = D.head_size(repo, rel)
        if size is None or not urls:
            missing.append(name)
            log("   !! %-64s 两源均取不到" % name)
            continue
        jobs.append((size, grp, sub, name, dest, urls))

    total = sum(j[0] for j in jobs)
    log("合计 %d 项 / %.2f GB" % (len(jobs), total / 1e9))
    if missing:
        log("取不到的文件：%s" % ", ".join(missing))

    pending = []
    for size, grp, sub, name, dest, urls in jobs:
        if os.path.exists(dest) and os.path.getsize(dest) == size:
            log("   [skip] %s" % name)
        else:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            pending.append((size, grp, sub, name, dest, urls))
    # 关键排序：有 modelscope 源的先下（快），hf-only 的排最后（慢/易卡），
    # 否则 2 个 BFL 大件会占住 worker 把整条队列拖死。
    pending.sort(key=lambda x: (0 if len(x[5]) > 1 else 1, -x[0]))

    if not pending:
        log("全部已完成")
        return 0

    log("待下载 %d 项，共 %.2f GB" % (len(pending), sum(p[0] for p in pending) / 1e9))
    t0 = time.time()
    CAP_MIN = 30.0        # 硬上限：超时不再接新任务，先交付已完成部分
    results = []

    def work(j):
        size, grp, sub, name, dest, urls = j
        if (time.time() - t0) / 60 > CAP_MIN:
            return (grp, name, False, 0.0, "超时跳过")
        t = time.time()
        ok, src = D.fetch_multi(urls, dest, size)
        return (grp, name, ok, time.time() - t, src)

    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(work, j) for j in pending]
        for f in as_completed(futs):
            grp, name, ok, dt, src = f.result()
            results.append((grp, name, ok, dt, src))
            log("%s [%-10s] %-22s %-58s %6.2f 分"
                % ("OK  " if ok else "FAIL", src, grp, name, dt / 60))

    log("=" * 70)
    bad = [r for r in results if not r[2]]
    log("补充下载结束：成功 %d / %d，用时 %.1f 分"
        % (len(results) - len(bad), len(results), (time.time() - t0) / 60))
    for grp, name, ok, dt, src in bad:
        log("  失败: [%s] %s" % (grp, name))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
