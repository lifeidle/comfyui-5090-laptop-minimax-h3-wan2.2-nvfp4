# Benchmark results — server-side execution time

All timings are read from ComfyUI's `/history/<prompt_id>` entry, from the
`execution_start` and `execution_success` timestamps. This is **pure execution time**: it excludes
queueing, model loading and API round-trip. Wall-clock and API-delta timings were deliberately not
used, because they inflate the number and are not comparable between runs.

Hardware: **RTX 5090 Laptop, 24435 MiB (24 GB), sm_120** · ComfyUI 0.37.0 · PyTorch 2.11.0+cu128

## Round 1 — full sweep

| # | Workflow | Configuration | Exec | Result |
|---|---|---|---|---|
| 1 | MiniMax H3 t2va (smoke) | 768 x 448, 56 frames | **76.31 s** | ok |
| 2 | Z-Image-Turbo int8 | 1024 x 1024, 8 steps | **20.91 s** | ok |
| 3 | Z-Image-Turbo nvfp4 | 1024 x 1024, 8 steps | **15.76 s** | ok |
| 4 | FLUX.2 Klein 9B nvfp4 edit | — | — | **failed** (encoder packaging, see below) |
| 5 | FLUX.2 Klein 4B fp8 edit | single 1024 x 1024 image | **42.32 s** | ok |
| 6 | HunyuanVideo 1.5 480p 4-step | 848 x 480, 121 frames | — | not run in this round |
| 7 | MiniMax H3 t2va (full) | 1344 x 768, 124 frames | **519.06 s** | ok |

Z-Image round 1: int8 20.91 s vs nvfp4 15.76 s -> nvfp4 is **24.6 % faster**.

## Round 2 — controlled A/B, back-to-back

Run immediately after round 1, with a `POST /free` before each submission.

| Workflow | DiT | Seed | Exec |
|---|---|---|---|
| `ab_ctl_int8` | int8 | 20260922 | **17.7 s** |
| `ab_ctl_int8_rep` | int8 | 20260922 | 12.5 s |
| `ab_ctl_int8_s2` | int8 | 20260923 | 12.6 s |
| `ab_ctl_nvfp4` | nvfp4 | 20260922 | **13.8 s** |
| `ab_ctl_nvfp4_s2` | nvfp4 | 20260923 | 11.7 s |

Z-Image round 2, first-run pair: int8 17.7 s vs nvfp4 13.8 s -> nvfp4 is **22.0 % faster**.

## HunyuanVideo 1.5, measured separately

| Workflow | Configuration | Exec | Result |
|---|---|---|---|
| `hv15_t2v_480p_4step` | 848 x 480, 121 frames, LightX2V 4-step LoRA | **117.0 s** | ok |

## On run-to-run variance

The two Z-Image rounds disagree in absolute terms:

```
int8 :  20.91 s  vs  17.7 s     (-15.4 %)
nvfp4:  15.76 s  vs  13.8 s     (-12.4 %)
```

A laptop GPU throttles against thermal and power limits, so ±15 % run-to-run drift in absolute
numbers is normal. However, the **relative** result is stable across both rounds:

```
nvfp4 vs int8:  24.6 % faster (round 1)   22.0 % faster (round 2)
```

> When reporting performance, trust the relative percentage, not the absolute seconds.

## Failed run detail

`flux2_klein_9b_nvfp4_edit` failed with:

```
mat1 and mat2 shapes cannot be multiplied (1024x7680 and 12288x4096)
```

Root cause: the 9B model requires a Qwen3-VL text encoder of roughly 16.4 GB, which BFL publishes
only in **diffusers sharded format**. ComfyUI cannot load a sharded directory. This is a weight
packaging incompatibility, not a VRAM or quantization problem.

## Output verification

Both videos were verified with `ffprobe` and by extracting frames into a contact sheet:

| Workflow | ffprobe result | Visual check |
|---|---|---|
| MiniMax H3 t2va full | h264, 1344x768, 24 fps, 5.17 s, nb_frames=124, **+ aac 32 kHz stereo** | frames match the prompt timeline (RGB-split title -> chrome palm trees -> sunset) |
| HunyuanVideo 1.5 480p | h264, 848x480, 24 fps, 5.04 s, nb_frames=121 | temporally stable pottery-wheel shot; wheel turning, hands shaping, warm left rim light, blurred shelves of bisque ware |
