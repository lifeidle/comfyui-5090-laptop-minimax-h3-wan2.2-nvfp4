# Round 4 — ComfyUI 0.38.0 re-verification + Qwen-Image 2.1

Hardware: RTX 5090 Laptop 24 GB (sm_120), ComfyUI **0.38.0**, PyTorch 2.11.0+cu128. GPU serialized.

## 1. ComfyUI 0.37.0 → 0.38.0 — did the timings go stale?

The 0.38.0 release notes list optimizations that touch three of our measured models. Re-ran them:

| Model | 0.37.0 | **0.38.0** | Change | 0.38.0 change responsible |
|---|---|---|---|---|
| ACE-Step 1.5 XL turbo | 28.6 s | **20.8 s** | **−27.3%** | CUDA graphs + memory compiler on the autoregressive model |
| YuE2-3B | 93.7 s | **87.5 s** | −6.6% | "Speedup Yue2 AR" |
| FLUX.1-dev fp8 | 32.1 s | **30.1 s** | −6.2% | "Port some optimizations to flux model family" |

**All three were stale; ACE-Step materially so.** Unchanged and still applicable:
`hunyuanvideo1.5_480p` 117.0 s, `wan22_14b_t2v_4step` 93.8 s, `minimax_h3_t2va_4step` 286.2 s.

**What did NOT change**: the `comfy_kitchen` CUDA backend is still `disabled: True`
(`WARNING: You need pytorch with cu130 or higher`; torch is cu128).
So §5's "NVFP4 is 22% faster" **remains a lower bound**.

New in 0.38.0: `w6a8` quantization format, `ModelAttentionBackend` node, `TextEncodeQwenImage21`.
Node count 960 → **965**.

## 2. Qwen-Image 2.1 — the successor to our image pick

`Comfy-Org/Qwen-Image-2.1` ships single-file int8 builds — **17.3 GB total, fits**:

| File | Size |
|---|---|
| `qwen_image_2.1_int8_convrot.safetensors` | 7.26 GB (650 tensors) |
| `qwen3vl_8b_int8_convrot.safetensors` | 9.35 GB (1259 tensors) |
| `qwen_image_2.1_vae_bf16.safetensors` | 0.68 GB |

**Controlled comparison** — identical prompt, identical 1328×1328 resolution:

| Model | Quant | Steps | Exec | 30 Chinese characters |
|---|---|---|---|---|
| Qwen-Image 2512 | fp8 | 50 | 206.7 s | ✅ 30/30 character-exact |
| Qwen-Image 2512 + Lightning | fp8 | 4 | **12.2 s** | ✅ 30/30 |
| **Qwen-Image 2.1** | **int8 convrot** | **25** | **72.7 s** | ✅ **30/30 character-exact** |

1. **Chinese rendering ties** — both title lines (7 chars each: 春风得意马蹄疾 / 一日看尽长安花)
   and all four subtitle phrases (茶香四溢 / 静心品茗 / 八方来客 / 岁月悠长) are exact.
2. **2.8× faster at comparable quality** — 25 steps / 72.7 s vs 50 steps / 206.7 s.
3. **Smaller footprint** — 17.3 GB vs roughly 30 GB.

**Caveat**: 2.1 has **no Lightning / lightx2v LoRA**, so the fastest configuration is still
2512 + Lightning at 12.2 s. Pick by need: absolute speed → 2512 + Lightning; full quality at
moderate speed and smaller footprint → 2.1.

Style differs: 2512 gives bolder brushwork and stronger contrast; 2.1 is more refined with more
whitespace and subtler ink-wash gradation.

## 3. Downloader bugs found (both would have silently corrupted weights)

1. **No final size check** — a downloader that only prints progress reported "OK" on two files
   truncated at exactly 4.36 GB (modelscope appears to cap a single connection near that point).
2. **Stale offset across source failover** — the resume loop computed `have` once per outer
   attempt, so when it switched source mid-file the second source appended from a stale offset and
   produced a file **larger** than the expected size (7.46 GB for a 7.26 GB target).

The corrected downloader (`scripts/dl_fixed.py`) recomputes the offset before every source attempt,
verifies the response `Content-Range` starts at the requested offset, and validates byte count plus
the safetensors header before accepting a file.

## 4. Model cleanup (same day)

42 files / 167.4 GB removed, 515.6 GB → 348.2 GB. See §6.6.
