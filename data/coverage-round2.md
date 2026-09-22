# Round 2 — coverage expansion: raw measurements

All timings read from ComfyUI's `/history/<prompt_id>` `execution_start` →
`execution_success` timestamps (server-authoritative; excludes queueing, model loading
and API round-trip).

Hardware: **RTX 5090 Laptop, 24435 MiB (24 GB), sm_120** · ComfyUI 0.37.0 · PyTorch 2.11.0+cu128
Run date: 2026-09-22 · GPU serialized (one workflow at a time, `POST /free` before each submit)

## 1. Newly run model lines

| Domain | Model | Configuration | Exec (s) | Output |
|---|---|---|---|---|
| Image | Z-Image-Turbo nvfp4 (3D input image) | 1024², 8 steps | 15.0 | 1024×1024 PNG |
| Video | Wan 2.2 5B TI2V (smoke) | 704×384, 49 frames, 20 steps | 34.6 | h264 704×384, 2.04 s |
| Video | **Wan 2.2 5B TI2V (full)** | 1280×704, 121 frames, 20 steps | **355.1** | h264 1280×704, 5.04 s |
| Video | **Wan 2.2 14B MoE** | 832×480, 81 frames, **4 steps** (LightX2V) | **93.8** | h264 832×480, 5.06 s @16fps |
| Video | LTX-Video 2B distilled (smoke) | 768×512, 97 frames, 8 steps | 11.7 | h264 768×512, 4.04 s |
| Video | **LTX-Video 2B distilled (full)** | 1216×704, 121 frames, 8 steps | **19.2** | h264 1216×704, 5.04 s |
| Video | HunyuanVideo 1.5 720p→1080p | 1280×720 base 20 steps + 1080p SR 8 steps | **DNF — 70 min, terminated** | — |
| Music | ACE-Step 1.5 turbo | 60 s song, 8 steps, CFG 1 | 22.9 | mp3 48 kHz stereo 60.00 s |
| Music | ACE-Step 1.5 XL turbo | 60 s song, 8 steps, CFG 1 | 28.6 | mp3 48 kHz stereo 60.00 s |
| Music | YuE2-3B | 60 s song, 32 steps (ABC plan + AR) | 93.7 | flac 48 kHz stereo 60.00 s |
| Music | MiniMax Music 3 | 60 s song, 30 steps, CFG 1.7 | 458.2 | mp3 44.1 kHz stereo 59.99 s |
| 3D | **Hunyuan3D 2.1** | 30 steps, latent 4096, octree 256 | **54.7** | GLB, 202,768 verts / 522,140 tris |

## 2. Hunyuan3D 2.1 output structure (parsed from the GLB binary)

```
magic = "glTF"   version = 2   file length = 8,701,344
meshes = 1
  primitive: vertices = 202,768   triangles = 522,140
materials = 1    nodes = 1
```

## 3. Wan 2.2 — the VAE trap

`wan2.2_t2v_14B` substituted with `wan2.2_vae` fails at `VAEDecode`:

```
Given groups=1, weight of size [48, 48, 1, 1, 1],
expected input[1, 16, 21, 60, 104] to have 48 channels, but got 16 channels instead
```

Root cause: **the 5B line and the 14B line use different VAEs.**

| Template family | VAE referenced |
|---|---|
| `video_wan2_2_5B_ti2v.json`, `video_wan2_2_5B_fun_*.json` | `wan2.2_vae.safetensors` |
| every `video_wan2_2_14B_*.json` | `wan_2.1_vae.safetensors` |

## 4. Environment finding — optimized CUDA kernels disabled

```
WARNING: You need pytorch with cu130 or higher to use optimized CUDA operations.
[INFO] Found comfy_kitchen backend cuda: {'available': True, 'disabled': True, ...}
```

PyTorch is `2.11.0+cu128`, so the `comfy_kitchen` CUDA backend is disabled. The capability
list it *would* provide includes `scaled_mm_nvfp4`, `scaled_mm_svdquant_w4a4`,
`convrot_w4a4_linear`, `quantize_nvfp4`, `dequantize_nvfp4`, …

**Consequence:** the controlled A/B in `data/quant-ab-metrics.md` (NVFP4 22% faster than INT8)
was measured **without** these kernels. That figure is therefore a **lower bound**.

## 5. Coverage summary

| Domain | Ran | Downloaded, not run | Deliberately skipped |
|---|---|---|---|
| Image | 7 lines | 1 (Qwen bf16 shards) | 2 (FLUX.2-dev, Nunchaku Qwen NVFP4) |
| Video | 5 lines | 2 (HV1.0, HV1.5 720p) | 2 (LTX-2.3, LTX-2.5) |
| Music | 4 lines | 1 (Stable Audio 3) | 0 |
| 3D | 1 line | 0 | 0 |

See Appendix E of `README.md` / `README_EN.md` for the reason behind every skip.
