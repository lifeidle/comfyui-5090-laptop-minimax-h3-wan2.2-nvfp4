# Download manifest — 34 files, 125.6 GB

Validation method: three layers, all passing.

1. **Byte size** — expected size probed from the remote with `Range: bytes=0-0` and read off
   `Content-Range`, then compared against the file on disk.
2. **Structure** — the safetensors header (first 8 bytes, little-endian uint64 = header length,
   then JSON) is parsed and every tensor's `data_offsets` is checked against the file length.
3. **dtype** — the distinct dtypes actually present in the tensor table.

Result: **34 / 34 complete, 125.6 GB, 0 corrupt, 0 in progress.**

Source column: `ms` = www.modelscope.cn, `hfm` = hf-mirror.com, `hf` = huggingface.co.
Every file was fetched from the **first** source that served it; fallbacks were only used when a
source failed outright.

## MiniMax H3 — video + audio (8 weights + 10 effect LoRAs)

| File | Size | Tensors | dtypes | Source |
|---|---|---|---|---|
| `minimax_h3_fl2va_pruned_int8_convrot.safetensors` | 20.97 GB | 932 | BF16, F16, F32, I8, U8 | ms |
| `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | 15.69 GB | 2054 | BF16, F32, F8_E4M3, I8, U8 | ms |
| `minimax_h3_video_vae_fp16.safetensors` | 5.21 GB | 562 | F16 | ms |
| `minimax_h3_video_vae_int8_convrot.safetensors` | 2.81 GB | 850 | F16, F32, I8, U8 | ms |
| `minimax_h3_fun_controlnet_union_pruned_int8_convrot.safetensors` | 2.30 GB | 104 | BF16, F32, I8, U8 | ms |
| `minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors` | 1.96 GB | 624 | BF16, F32 | ms |
| `minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors` | 1.96 GB | 624 | BF16, F32 | ms |
| `minimax_h3_audio_vae_fp32.safetensors` | 0.61 GB | 917 | F32 | ms |
| `minimaxh3_art_is_explosion.safetensors` | < 0.01 GB | 1 | BF16 | ms |
| `minimaxh3_blooming_flowers.safetensors` | < 0.01 GB | 1 | BF16 | ms |
| `minimaxh3_bullet_time.safetensors` | < 0.01 GB | 1 | BF16 | ms |
| `minimaxh3_dark_magic.safetensors` | < 0.01 GB | 1 | BF16 | ms |
| `minimaxh3_fire_breath.safetensors` | < 0.01 GB | 1 | BF16 | ms |
| `minimaxh3_four_seasons.safetensors` | < 0.01 GB | 1 | BF16 | ms |
| `minimaxh3_kiss_camera.safetensors` | < 0.01 GB | 1 | BF16 | ms |
| `minimaxh3_spiral_ascent.safetensors` | < 0.01 GB | 1 | BF16 | ms |
| `minimaxh3_storm_magic.safetensors` | < 0.01 GB | 1 | BF16 | ms |
| `minimaxh3_truman_show.safetensors` | < 0.01 GB | 1 | BF16 | ms |

## Z-Image-Turbo — image (5 files)

| File | Size | Tensors | dtypes | Source | Note |
|---|---|---|---|---|---|
| `z_image_turbo_int8_convrot.safetensors` | 6.20 GB | 857 | F32, I8, U8 | ms | A/B baseline |
| `z_image_turbo_nvfp4.safetensors` | 4.51 GB | 993 | BF16, F32, **F8_E4M3**, U8 | ms | **real NVFP4** |
| `qwen_3_4b.safetensors` | 8.04 GB | 398 | BF16 | ms | text encoder, bf16 |
| `qwen_3_4b_fp4_mixed.safetensors` | 3.48 GB | 1081 | BF16, F32, **F8_E4M3**, U8 | ms | **real NVFP4** encoder |
| `ae.safetensors` | 0.34 GB | 244 | F32 | ms | VAE |

## FLUX.2 Klein — image editing (4 files)

| File | Size | Tensors | dtypes | Source | Note |
|---|---|---|---|---|---|
| `flux-2-klein-9b-nvfp4.safetensors` | 5.76 GB | 531 | BF16, F32, F8_E4M3, U8 | ms | DiT only; **not runnable** without its encoder |
| `flux-2-klein-4b-fp8.safetensors` | 4.07 GB | 309 | BF16, F32, F8_E4M3 | ms | official BFL fp8 single file |
| `qwen_3_4b_fp4_flux2.safetensors` | 3.85 GB | 1028 | BF16, F32, F8_E4M3, U8 | ms | encoder (type `flux2`) |
| `flux2-vae.safetensors` | 0.34 GB | 251 | F32, I64 | ms | VAE |

## HunyuanVideo 1.5 — video (7 files)

| File | Size | Tensors | dtypes | Source | Note |
|---|---|---|---|---|---|
| `hunyuanvideo1.5_720p_t2v_fp16.safetensors` | 16.65 GB | 1361 | F16 | ms | 720p is a **separate base model** |
| `hunyuanvideo1.5_480p_t2v_fp16.safetensors` | 16.65 GB | 1361 | F16 | ms | 480p is a **separate base model** |
| `hunyuanvideo15_vae_fp16.safetensors` | 2.52 GB | 218 | F16 | ms | VAE |
| `sigclip_vision_patch14_384.safetensors` | 0.86 GB | 448 | F16 | ms | CLIP vision |
| `byt5_small_glyphxl_fp16.safetensors` | 0.44 GB | 111 | F16 | ms | second text encoder |
| `hunyuanvideo1.5_t2v_480p_lightx2v_4step_lora_rank_32_bf16.safetensors` | 0.34 GB | 1709 | BF16 | ms | 4-step accelerator |
| `hunyuanvideo15_latent_upsampler_720p.safetensors` | 0.09 GB | 100 | F32 | ms | latent upsampler |

Note: `qwen_2.5_vl_7b_fp8_scaled.safetensors` (8.74 GB) is reused as HunyuanVideo 1.5's first text
encoder. It was already on disk from an earlier project, so it is not counted in the 125.6 GB.

## Identifying real NVFP4

Do **not** trust the filename. A real NVFP4 file declares these tensor keys:

```
weight_scale
weight_scale_2
input_scale
pre_quant_scale
TensorCoreNVFP4Layout   (group_size = 16)
```

and its dtype set includes `F8_E4M3` (block scales) alongside `U8`. In the table above, the three
files marked **real NVFP4** were confirmed this way.

By contrast `flux-2-klein-4b-fp8.safetensors` has no `U8` and no NVFP4 keys — it is genuine fp8, as
its name says. Trusting the name happened to be correct there, but only the tensor keys prove it.

## Transfer performance

| Source | Observed single-connection throughput | Time for a 16.65 GB file |
|---|---|---|
| www.modelscope.cn | 11 – 27 MB/s | 12.6 min (measured) |
| hf-mirror.com | 2 – 4 MB/s | ~80 min (projected) |
| huggingface.co | 1.6 – 2.2 MB/s | ~2.4 h (projected) |
