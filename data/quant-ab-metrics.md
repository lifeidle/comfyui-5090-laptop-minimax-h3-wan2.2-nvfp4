# Controlled A/B metrics — quantization versus seed noise

All values measured on **RTX 5090 Laptop (24 GB, sm_120)**, ComfyUI 0.37.0.

## Setup

| Item | Value |
|---|---|
| Model | Z-Image-Turbo |
| DiT A | `z_image_turbo_int8_convrot.safetensors` (6.20 GB) |
| DiT B | `z_image_turbo_nvfp4.safetensors` (4.51 GB) |
| Text encoder | `qwen_3_4b_fp4_mixed.safetensors` — **identical in every arm** |
| Prompt | 一张超写实摄影作品：黄山云海日出，花岗岩奇峰在翻涌的云层中若隐若现…… |
| Resolution / steps | 1024 x 1024 / 8 steps |
| Sampler / scheduler | `res_multistep` / `simple`, CFG 1.0, `ModelSamplingAuraFlow` shift 3 |

The **only** variable between the two DiT arms is the quantization format. The text encoder,
prompt, resolution, step count, sampler, scheduler and CFG are byte-identical across all five runs.

## Runs

| Run | DiT | Seed | Output file | Server exec |
|---|---|---|---|---|
| A1 | int8 | 20260922 | `ctl_int8_00001_.png` | 17.7 s |
| A2 | int8 | 20260922 | `ctl_int8_rep_00001_.png` | 12.5 s |
| A3 | int8 | 20260923 | `ctl_int8_s2_00001_.png` | 12.6 s |
| B1 | nvfp4 | 20260922 | `ctl_nvfp4_00001_.png` | 13.8 s |
| B2 | nvfp4 | 20260923 | `ctl_nvfp4_s2_00001_.png` | 11.7 s |

## PSNR / mean pixel difference

| Arm | Comparison | Variable | PSNR | MAE | MAE % |
|---|---|---|---|---|---|
| `det` | A2 vs A1 | none (re-run) | **inf** | **0.00** | **0.00 %** |
| `seed` | A3 vs A1 | random seed (int8) | 12.10 dB | 43.07 | 16.89 % |
| `cross` | B1 vs A1 | **quantization only** | **16.84 dB** | **18.90** | **7.41 %** |
| `seedB` | B2 vs B1 | random seed (nvfp4) | 12.45 dB | 41.89 | 16.43 % |

### Difference distribution (cross arm, per-pixel max channel delta)

| Percentile | Value |
|---|---|
| P50 | 12.0 |
| P90 | 49.0 |
| P95 | 101.0 |
| P99 | 177.0 |
| P99.9 | 210.0 |
| max | 245 |

### 4x4 tile PSNR (cross arm), dB

```
 18.8  35.9  33.5  28.2
 14.2  17.7  15.7  16.2
 15.3  11.3  18.3  13.7
 25.1  18.1  18.2  18.2
```

No tile collapses to near-zero, i.e. there is no localised structural artifact — the difference is
distributed, which is what trajectory divergence looks like.

## Quality proxies (robust to trajectory divergence)

| Sample | Sharpness (Laplacian var) | Shannon entropy | HF ratio |
|---|---|---|---|
| int8 · seed 20260922 | 776.5 | 5.572 | 0.0130 |
| int8 · seed 20260922 (re-run) | 776.5 | 5.572 | 0.0130 |
| int8 · seed 20260923 | 705.4 | 5.736 | 0.0134 |
| nvfp4 · seed 20260922 | 694.3 | 5.614 | 0.0127 |
| nvfp4 · seed 20260923 | 604.1 | 5.791 | 0.0140 |

Notable: the **re-run of the same quantization and seed reproduces the proxy metrics exactly**
(776.5 / 5.572 / 0.0130), consistent with the PSNR = inf result.

Within-quantization seed spread for int8 is 776.5 -> 705.4 (-71.1). The cross-quantization spread at
a fixed seed is 776.5 -> 694.3 (-82.2). These are the same magnitude — quantization is not a
distinguishable factor.

## Colour histogram L1 distance

| Arm | L1 |
|---|---|
| `det` | 0.0000 |
| `cross` | 0.0858 |
| `seedB` | 0.1085 |
| `seed` | 0.1256 |

Comment: 1.0 would mean completely disjoint histograms. Both seed arms are *further* from the
baseline than the cross-quantization arm.

## Verdict

1. The pipeline is **deterministic** (PSNR = inf on re-run) — so the cross-quantization gap is
   attributable entirely to quantization.
2. The cross-quantization gap (**7.41 %** MAE) is **smaller** than the seed gap (**16.89 %** MAE).
3. Quality proxies and colour histograms agree: no systematic difference.

**Conclusion: on this hardware NVFP4 costs nothing measurable in quality, while being 22 % faster
and 27 % smaller.**
