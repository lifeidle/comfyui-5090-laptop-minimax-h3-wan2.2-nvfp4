# Round 3 — closing every remaining gap, then the final verdict

All timings read from ComfyUI's `/history/<prompt_id>` `execution_start` → `execution_success`
(server-authoritative). Hardware: RTX 5090 Laptop 24 GB (sm_120), ComfyUI 0.37.0,
PyTorch 2.11.0+cu128. GPU serialized, `POST /free` before every submit.

## 1. Newly run lines

| Domain | Model | Configuration | Exec (s) | Output |
|---|---|---|---|---|
| Video | **Wan 2.2 14B MoE (4-step LoRA)** | 832×480, 81 frames, **4 steps** | **93.8** | h264 832×480, 5.06 s @16fps |
| Video | Wan 2.2 14B MoE (**20 steps, no LoRA**) | 832×480, 81 frames, 20 steps | **739.0** | h264 832×480, 5.06 s |
| Video | **MiniMax H3 (4-step LoRA)** | 1344×768, 124 frames, **4 steps** | **286.2** | h264 1344×768, 5.17 s **+ aac 32 kHz stereo** |
| Image | **FLUX.2 Klein 9B fp8 (2-pass edit)** | 1024², 4 steps | **18.9** | PNG 1024² |
| Image | **Lens turbo** | 1024², 4 steps | **13.6** | PNG 1024² |
| Image | **ERNIE-Image turbo** | 1024², 8 steps + LLM prompt enhancer | **37.3** | PNG 1024² |
| Music | **Stable Audio 3 Medium** | 60 s, 8 steps | **13.8** | mp3 48 kHz stereo 60.0 s |

## 2. Two misjudgements corrected this round

### 2.1 FLUX.2 Klein 9B was never actually blocked

The original "blocked" verdict came from BFL's official repo, which ships the Qwen3-VL encoder as
**diffusers shards**. But `Comfy-Org/flux2-klein-9B` publishes a **single-file** encoder:

| File | Repo | Size |
|---|---|---|
| `qwen_3_8b_fp8mixed.safetensors` | `Comfy-Org/flux2-klein-9B` | 8.66 GB |
| `flux-2-klein-9b-fp8.safetensors` | `black-forest-labs/FLUX.2-klein-9b-fp8` | 9.43 GB |
| `full_encoder_small_decoder.safetensors` | `black-forest-labs/FLUX.2-small-decoder` | 0.25 GB |

Total **18.3 GB — fits in 24 GB with room to spare**, and it runs in 18.9 s.

**Lesson: "the official repo ships shards" is not the same as "no single file exists anywhere."
Check the Comfy-Org repackage before declaring a model unrunnable.**

### 2.2 The 4-step LoRA trade-off is now quantified, not assumed

| Model | 4-step | 20/8-step | Speed-up |
|---|---|---|---|
| Wan 2.2 14B MoE | **93.8 s** | **739.0 s** (20 steps) | **7.9×** |
| MiniMax H3 | **286.2 s** | **519.1 s** (8 steps) | **1.81×** |

Same resolution, same frame count. The LoRA trades quality for speed, and now the size of that
trade is measured rather than guessed.

## 3. LTX-2.3 GGUF — attempted, blocked at three concrete steps

The correction in Appendix E stands (GGUF tiers do exist — `unsloth/LTX-2.3-GGUF` shows
311,007 downloads). But finishing it required three things this session could not close:

1. **`hf-mirror.com` API returns 403** for `unsloth/LTX-2.3-GGUF` (`?blobs=true` and `/tree/main`),
   so the actual file names and sizes could not be confirmed; direct filename guesses all 404'd.
2. It needs the **`ComfyUI-GGUF` custom node** — installable (github.com is blocked but
   `codeload.github.com` tarballs return 200), yet that also means a ComfyUI restart mid-run.
3. **LTX-2.3's text encoder and VAE** are separate, unidentified downloads on top of the DiT.

Verdict: feasible, but a multi-hour thread. Recorded as *attempted* rather than *skipped*.

## 4. Complete benchmark — all 21 measured configurations

### Image (1024² unless noted)

| Model | Steps | Exec (s) |
|---|---|---|
| **Lens turbo** | 4 | **13.6** |
| **Qwen-Image 2512 + Lightning** | 4 (1328²) | **12.2** |
| **Z-Image-Turbo nvfp4** | 8 | **13.8** |
| SDXL base 1.0 | 20 | 14.1 |
| **FLUX.2 Klein 9B fp8** | 4 (edit) | **18.9** |
| Z-Image-Turbo int8 | 8 | 17.7 |
| FLUX.1-dev fp8 | 20 | 32.1 |
| **ERNIE-Image turbo** | 8 | 37.3 |
| FLUX.2 Klein 4B fp8 | edit | 42.3 |
| Qwen-Image 2512 (no LoRA) | 50 (1328²) | 206.7 |

### Video

| Model | Configuration | Exec (s) |
|---|---|---|
| **LTX-Video 2B distilled** | 1216×704, 121 frames | **19.2** |
| **Wan 2.2 14B MoE** | 832×480, 81 frames, 4 steps | **93.8** |
| Wan 2.2 5B TI2V (smoke) | 704×384, 49 frames | 34.6 |
| HunyuanVideo 1.5 480p | 848×480, 121 frames, 4 steps | 117.0 |
| **MiniMax H3** | 1344×768, 124 frames, **4 steps, with audio** | **286.2** |
| Wan 2.2 5B TI2V | 1280×704, 121 frames, 20 steps | 355.1 |
| Wan 2.2 14B MoE | 832×480, 81 frames, 20 steps | 739.0 |
| MiniMax H3 | 1344×768, 124 frames, 8 steps, with audio | 519.1 |
| ~~HunyuanVideo 1.5 720p→1080p~~ | DNF — 70 min, terminated | — |

### Music (60 s song)

| Model | Exec (s) |
|---|---|
| **Stable Audio 3 Medium** | **13.8** |
| ACE-Step 1.5 turbo | 22.9 |
| ACE-Step 1.5 XL turbo | 28.6 |
| YuE2-3B | 93.7 |
| MiniMax Music 3 | 458.2 |

### 3D

| Model | Exec (s) |
|---|---|
| Hunyuan3D 2.1 | 54.7 |
