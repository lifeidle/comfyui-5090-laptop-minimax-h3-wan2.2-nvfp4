# Running the Newest Image, Video and Audio Models on an RTX 5090 Laptop with ComfyUI

**A complete field manual: model selection, downloads, graph construction, measurement, and the verdict.**

[中文](README.md) · **English** · [📖 Read online (language auto-detected)](https://lifeidle.github.io/comfyui-5090-laptop-playbook/)

---

> **The one-line verdict**: On a 24 GB laptop GPU we got four of the newest open-weight generative
> model lines running (six workflows in total) — and proved with a **controlled experiment** that
> **NVFP4 is the best quantization format for this machine**: **22% faster** and **27% smaller** than
> INT8, with a quality difference that sits **below the random seed noise floor**.

This is not a "copy-paste the commands" tutorial. The hard part is never getting one model to run —
it is **deciding which of dozens of quantization variants to pick**. This document lays the whole
decision chain bare: how we reasoned, how we downloaded, how we built the graphs, how we measured,
how we chose. Every number is measured on the machine, and every conclusion ships with a
reproducible method.

---

## Contents

| Section | Topic | What you get |
|---|---|---|
| [0](#0-hardware-and-starting-point) | Hardware and starting point | Where the real constraint is |
| [1](#1-tldr-the-verdict) | **The verdict first** | Every choice in one table |
| [2](#2-how-we-reasoned-framing-the-constraint) | How we reasoned | A complete mental model of quantization |
| [3](#3-how-we-downloaded-moving-1256-gb) | How we downloaded | The engineering behind 125.6 GB |
| [4](#4-how-we-built-comfyui-node-constraints) | How we built | Node constraints bought with pain |
| [5](#5-how-we-measured-the-controlled-ab-the-core-of-this-document) | **How we measured** | The methodology (the core) |
| [6](#6-how-we-chose-four-model-lines-in-practice) | How we chose | Each model, measured |
| [7](#7-optimization-checklist-configs-you-can-copy) | Optimization checklist | Copy-paste configs |
| [8](#8-troubleshooting-table) | Troubleshooting | Symptom → cause → fix |
| [9](#9-toolchain) | Toolchain | Six reusable scripts |
| [10](#10-conclusion-and-what-is-next) | Conclusion | What is still open |

---

## 0. Hardware and starting point

| Item | Measured value |
|---|---|
| GPU | **RTX 5090 Laptop** — 24435 MiB (**24 GB**), compute capability **sm_120** (Blackwell) |
| CUDA | 12.8 |
| System RAM | 64 GB |
| Engine | ComfyUI **0.37.0** / PyTorch 2.11.0+cu128 / Python 3.11.9 |
| Goal | Use the **newest** open-weight models, covering **image / video / audio** generation |

**Why start at 24 GB?** Because it is the only genuinely hard constraint in this document.

Raw compute on a modern laptop GPU is never the problem — an 8-step distilled model renders a
1024² image in about ten seconds on a 5090. What decides which models you can and cannot run is
**whether the weights fit in VRAM**. And the newest generation of open-weight generative models
shares a trend: **the base model keeps getting bigger, and it now demands a separate text encoder
that is just as big.**

Look at the chart below. Note the 24 GB red line.

![Single-file weight size against 24 GB of VRAM](assets/chart2-model-footprint.svg)

Three of these files — MiniMax H3's DiT at 21 GB, HunyuanVideo 1.5 at 16.7 GB, and MiniMax H3's text
encoder at 15.7 GB — **each individually exceeds 24 GB**. Which means:

> **They can never be resident. On every single step, weights must be shuttled between VRAM and
> system RAM.** That is why "picking the right quantization format" on this machine is not an
> optimization. It is the difference between running and not running.

---

## 1. TL;DR: the verdict

### 1.1 Selection table

| Use case | Model chosen | Quantization | Measured time | Notes |
|---|---|---|---|---|
| **Image generation** | Z-Image-Turbo | **NVFP4** (4.51 GB) | **13.8 s** (1024²/8 steps) | Accurate Chinese text rendering |
| **Image editing** | FLUX.2 Klein **4B** | fp8 (4.07 GB) | 42.3 s | 9B is blocked by its encoder, see §6.5 |
| **Video + audio** | MiniMax H3 | int8 + ConvRot | **519.1 s** (1344×768/124 frames) | **Native audio track**, 5.17 s of video with stereo |
| **Video only** | HunyuanVideo 1.5 480p | fp16 + LightX2V 4-step LoRA | **117.0 s** (848×480/121 frames) | 4 steps — fast enough to iterate |

### 1.2 Three rules you can apply immediately

1. **Quantization: if the GPU is Blackwell (sm_120/121), always pick NVFP4.** Proof in §5.
2. **Offload or not: sum the base model and the encoder, and compare against VRAM.** If the sum
   exceeds it, offloading is mandatory — and then every gigabyte quantization saves converts
   directly into speed.
3. **Speed comes from fewer steps, not from smaller weights.** An 8-step → 4-step LoRA buys far
   more than any weight quantization. Quantization makes the model **fit**; a distilled LoRA makes
   it **fast**. These are different problems.

---

## 2. How we reasoned: framing the constraint

### 2.1 The only hard constraint is VRAM, not compute

This deserves emphasis, because it determines every subsequent trade-off.

The common intuition — "if VRAM is short, use a smaller model" — does not apply here. The models we
want are the newest and strongest, and **they have no small variant**. The only free variable is
**how many bits each weight occupies**.

So the problem compresses into one sentence: **what is the fewest bits per weight that costs nothing
visible to the eye?**

### 2.2 The four families of quantization (this is the foundation)

The phrase "4-bit quantization" lumps together three completely different things. Separate them first.

| Family | Examples | What is compressed | Saves VRAM | Faster |
|---|---|---|---|---|
| **W4A16** | GGUF / NF4 / bitsandbytes / torchao | **weights only** | ✅ | ❌ **no, often slower** |
| **W4A4** | Nunchaku SVDQuant | **weights + activations** | ✅ | ✅ |
| **INT8 + ConvRot** | Comfy-Org's default for new models | 8-bit weights + rotation compensation | ✅ | ➖ no (runs the BF16 path) |
| **NVFP4** | Blackwell-native 4-bit float | weights + activations | ✅ | ✅ **fastest** |

**The most important row in that table is the first one.**

`W4A16` shrinks the weights but must expand them back to 16-bit to compute, so **you save memory but
save zero compute — and you pay extra dequantization overhead on top**. This is exactly why people
report "I switched to a 4-bit model and it got slower."

> **Remember it this way**: W4A16 saves **memory**. W4A4 / NVFP4 save **memory and bandwidth**.
> Only the latter actually goes faster.

NVFP4 wins on this machine because it is **Blackwell's native 4-bit floating-point format**: it feeds
tensor cores directly for 4-bit matrix multiplication, with no "expand first, then compute" round trip.

### 2.3 How to tell real NVFP4 apart (never trust the filename)

This is a trap we walked into. A great many community files named `fp4` or `nvfp4` are actually a
different format, or only partially 4-bit.

**The only reliable test is the tensor keys inside the safetensors file.** Open the header (first 8
bytes, little-endian uint64 = header length → JSON) and look for this set:

```
weight_scale
weight_scale_2
input_scale
pre_quant_scale
TensorCoreNVFP4Layout   (group_size = 16)
```

A verified real NVFP4 file on this machine shows both `F8_E4M3` (for block scales) and `U8` in its
dtype list. For example:

```
z_image_turbo_nvfp4.safetensors    4.51 GB   993 tensors   BF16, F32, F8_E4M3, U8   ✅ real NVFP4
qwen_3_4b_fp4_mixed.safetensors    3.48 GB  1081 tensors   BF16, F32, F8_E4M3, U8   ✅ real NVFP4
```

**The decision tree below is the complete selection logic:**

![Quantization selection decision tree](assets/chart4-quant-decision-tree.svg)

---

## 3. How we downloaded: moving 125.6 GB

Downloading looks trivial until you multiply **125.6 GB** by **unstable mirrors**. A naive
implementation can spend a whole day on it. The outcome: **34 files, 125.6 GB, zero corruption** —
built on three mechanisms.

### 3.1 Throughput, measured

![Download source throughput](assets/chart1-download-sources.svg)

The gap is **an order of magnitude**: modelscope is 7× faster than hf-mirror and 12× faster than
huggingface. Multi-source fallback is therefore not a nicety — it is mandatory.

### 3.2 Mechanism one: three-tier fallback

```
Each file tries:  www.modelscope.cn  →  hf-mirror.com  →  huggingface.co
```

If a source fails, fall through to the next. The `.part` resume file is **reusable across sources**
(both ends serve byte-identical content — verified).

### 3.3 Mechanism two: a silent watchdog (this one is essential)

This was our deepest trap.

We originally set a 45-second socket timeout. Then a file sat at **4.6%, 0.0 MB/s, for 19 minutes**
without raising a single error. The cause is nasty: **the server dribbled a few KB every 30 seconds**,
which was just enough to keep the socket alive while making no real progress.

> **Lesson**: a socket timeout cannot catch a "slow drip" stall. You need a second, **application-level
> watchdog**: if the byte count makes no real progress for **150 seconds**, actively disconnect and
> retry; after **3 consecutive silent stalls**, abandon that source and let the caller switch.
>
> With this layer in place, the same network conditions never produced another infinite hang.

### 3.4 Mechanism three: Range probing and concurrency

`modelscope` **does not support HEAD requests**, so you cannot get a file size the normal way — and
without a size you cannot verify anything. The fix is to range-request a single byte and read the
total from the response header:

```http
Range: bytes=0-0
→  HTTP/1.1 206 Partial Content
   Content-Range: bytes 0-0/16748116224        # ← the true byte count
```

Once you have the expected size, three things become possible:
1. **Probe sizes concurrently** (probe only, no download) → know the total and prioritise early
2. **Compare byte counts after download** → detect truncation and corruption precisely
3. **Cross-validate two sources** → the same file should report the same size on both

### 3.5 A meta-lesson: never probe source health during a download peak

**We got this wrong once.** While four parallel downloads were saturating the link, we probed the
other sources — every probe timed out, and we concluded, incorrectly, that "both mirrors are
unavailable, so the user must download manually."

They were perfectly healthy. The bandwidth was simply **fully consumed**.

> **Lesson**: probe requests (speed tests, availability checks) and download requests compete for the
> same bandwidth. Either probe while idle, or **rate-limit the probes separately**.

---

## 4. How we built: ComfyUI node constraints

With the models on disk, the next job is turning them into a runnable graph. ComfyUI's official
workflows live in two places:

- `ComfyUI/blueprints/*.json` — **116 official blueprints**
- `site-packages/comfyui_workflow_templates_json/templates/` — the same set

But they **cannot be submitted as an API prompt directly**, because they are in **subgraph format**:
node types are UUIDs, and the real topology is buried inside `definitions.subgraphs`. We wrote
`bp_dump.py` to flatten a subgraph into a node-and-wire listing — far more reliable than guessing the
topology by hand.

### 4.1 Four node constraints you must know

| # | Constraint | Detail |
|---|---|---|
| 1 | **`CLIPLoader` has 29 types and `hunyuan_video_15` is not one of them** | HunyuanVideo 1.5 requires `DualCLIPLoader` (type=`hunyuan_video_15`) with `qwen_2.5_vl_7b_fp8_scaled` + `byt5_small_glyphxl_fp16` |
| 2 | **Z-Image's type is `lumina2`; FLUX.2's is `flux2`** | The same `qwen_3_4b` encoder is loaded with **different** types in the two models. Mixing them up is an error |
| 3 | **`MiniMaxH3ImageToVideo` has `first_frame` as optional** | Leave it unconnected → **pure text-to-video, with audio**. A node named "ImageToVideo" is not necessarily image-only |
| 4 | **`HunyuanVideo15ImageToVideo` has `start_image` as optional** | Same story: unconnected = text-to-video |

Points 3 and 4 were our biggest **correction of an assumption**: when you see `ImageToVideo`, first
check whether the image input is optional. If it is, the node also works as text-to-video.

### 4.2 What to do when there is no official blueprint

**HunyuanVideo 1.5 has no official blueprint.** You have to build the graph by hand from node
signatures. Order matters:

1. Check `DualCLIPLoader`'s type list to confirm `hunyuan_video_15` exists
2. Confirm the latent channel count (**1.5 uses 32 channels and spatial downsampling of 16** — unlike 1.0)
3. After building, run the **free validation** trick below

### 4.3 A free graph-validation trick (highly recommended)

While models are still downloading, a direct `POST /prompt` returns **HTTP 400 with per-node
`node_errors`**. The key insight:

> **If the only errors are `value_not_in_list` — meaning "that model file is not in the list" — then
> the graph's structure and types are entirely correct.**

That gives you a **zero-cost dry run**: you can validate a workflow before its weights finish
downloading. All seven workflows in this project were validated this way before the downloads completed.

---

## 5. How we measured: the controlled A/B (the core of this document)

This is the most valuable section here, because **we got it wrong the first time**.

### 5.1 A plausible conclusion that was wrong

In the first comparison we ran two Z-Image-Turbo variants (int8 and nvfp4) and got:

```
PSNR = 13.82 dB
```

What does 13.82 dB mean? Conventionally, anything below 20 dB means "two visibly different images."
Our conclusion at the time: **"4-bit quantization really does degrade quality. NVFP4 is not good
enough."**

**That conclusion was wrong**, because we made a methodological error:

> ❌ **The two variants used different text encoders.**
> The int8 build was paired with `qwen_3_4b.safetensors` (bf16); the nvfp4 build with
> `qwen_3_4b_fp4_mixed.safetensors` (fp4).
>
> So encoder differences were baked into that 13.82 dB. Quantization was never the culprit.

### 5.2 Why PSNR cannot be used naively on generative models

Before fixing the method, you have to internalise a counter-intuitive fact:

> **Diffusion sampling is chaotic.**

Two models whose values agree to four decimal places will produce **two completely different
compositions** after 8 sampling steps. This is not a bug — it is the nature of the process; sampling
keeps amplifying tiny differences.

**So "these two images have low PSNR" does not prove "one of them is worse." It only proves "these
are two different samples."**

To judge whether quantization damages quality, you need something else entirely: **a noise baseline**.

### 5.3 Designing the four-way control

We isolated the variable completely — identical encoder, identical prompt, identical 1024²/8-step
configuration, **with only the DiT quantization differing** — and then added two "only the random
seed changed" controls:

| Arm | Variable | Purpose |
|---|---|---|
| **det** | none (same quant, same seed, re-run) | **Determinism check**: is the pipeline reproducible? |
| **seed** | random seed only (within int8) | **Noise floor** |
| **cross** | **quantization only** (same seed) | **The thing being measured** |
| **seedB** | random seed only (within nvfp4) | Noise floor (second copy) |

**The test**: if `cross` similarity is **higher** than `seed` similarity, then **the perturbation
caused by quantization is smaller than the randomness of sampling** — meaning quantization error is
negligible.

### 5.4 Results

![Controlled A/B: is the quantization loss real?](assets/chart3-quant-ab-psnr.svg)

| Arm | Variable | PSNR | Mean pixel difference |
|---|---|---|---|
| **det** same quant, same seed, re-run | none | **∞ dB** | **0.00%** |
| **seed** int8, different seed | seed only | 12.10 dB | 16.89% |
| **cross** nvfp4 vs int8, same seed | **quantization only** | **16.84 dB** | **7.41%** |
| **seedB** nvfp4, different seed | seed only | 12.45 dB | 16.43% |

### 5.5 Three hard conclusions

**Conclusion one: the pipeline is deterministic.**

The `det` arm measured PSNR = **∞** — the two images are **byte-for-byte identical**. This single fact
is what makes the whole experiment **attributable**: since identical inputs necessarily produce
identical outputs, the difference in the `cross` arm is **100% attributable to the quantization
format itself**, with zero runtime noise mixed in.

> Had this failed — had a re-run produced a different image — then no cross-quantization difference
> could be attributed to anything, and the experiment would have been worthless.

**Conclusion two: quantization perturbation < sampling noise.**

```
cross difference (7.41%)  <  seed difference (16.89%)
```

**Changing the quantization format alters the image less than picking a different random seed.**
That is the hard evidence that quantization is not costing quality.

**Conclusion three: quality proxy metrics show no systematic difference.**

PSNR is sensitive to trajectory divergence, so we measured five **robust** proxies as well:

| Sample | Sharpness (Laplacian variance) | Shannon entropy | High-frequency ratio |
|---|---|---|---|
| int8 · seed A | 776.5 | 5.572 | 0.0130 |
| int8 · seed B | 705.4 | 5.736 | 0.0134 |
| nvfp4 · seed A | 694.3 | 5.614 | 0.0127 |
| nvfp4 · seed B | 604.1 | 5.791 | 0.0140 |

**The spread caused by changing only the seed within one quantization (int8: 776.5 → 705.4) already
covers the entire cross-quantization difference (776.5 → 694.3).** In other words: **the quantization
factor is drowned inside the seed factor's variance.**

Color histogram L1 distance agrees:

```
det = 0.0000   |   cross = 0.0858   |   seedB = 0.1085   |   seed = 0.1256
                    ↑ cross-quant          ↑ within-seed      ↑ within-seed
```

**The color-distribution difference across quantizations is smaller than the difference caused by
changing the seed.**

### 5.6 Final review: do they look the same?

Numbers aside, we did a human eye check. Four images laid out **2×2**, deliberately arranged so that
**reading down a column = same seed, different quantization** and **reading across a row = same
quantization, different seed**:

```
┌──────────────────────┬──────────────────────┐
│  INT8  · seed 20260922│  INT8  · seed 20260923│
├──────────────────────┼──────────────────────┤
│ NVFP4  · seed 20260922│ NVFP4  · seed 20260923│
└──────────────────────┴──────────────────────┘
       ↑ column: same seed, cross-quant   ↑ row: same quant, cross-seed
```

**The result matches the numbers exactly:**
- **Down a column** (same seed, cross-quantization) → **highly similar compositions** (both expose
  the same distant rock spires on the left)
- **Across a row** (same quantization, different seed) → **entirely different compositions**

**All four are competent, high-quality Huangshan sunrise renderings** — semantically correct, richly
detailed, free of artifacts. Quantization is not the variable. The seed is.

### 5.7 The methodology, distilled (reusable for any model)

> **Any "does quantization hurt quality?" comparison must satisfy three conditions:**
>
> 1. **Controlled**: encoder, prompt, resolution, steps, sampler, and CFG **all fixed** — change one variable at a time
> 2. **Has a noise baseline**: you must also measure "same quantization, different seed", or you cannot
>    separate quantization perturbation from sampling randomness
> 3. **Has a determinism check**: "same quantization + same seed" must reproduce byte-identically,
>    or the conclusion is not attributable
>
> Miss any one of these and the PSNR number will be misread.

---

## 6. How we chose: four model lines in practice

### 6.1 Image generation — Z-Image-Turbo

| Item | Value |
|---|---|
| DiT | `z_image_turbo_nvfp4.safetensors` — **4.51 GB** (int8 build is 6.20 GB) |
| Text encoder | `qwen_3_4b_fp4_mixed.safetensors` — 3.48 GB |
| VAE | `ae.safetensors` — 0.34 GB |
| Key parameters | `CLIPLoader` type = **`lumina2`**; `ModelSamplingAuraFlow` shift=3; KSampler **8 steps, CFG=1**, `res_multistep` / `simple` |
| Measured | int8 **17.7 s** / nvfp4 **13.8 s** (1024², 8 steps) |

**Why this is our default image model** — three reasons:
1. **8 steps to an image**, roughly ten seconds, which makes it fast enough to use as a sketchpad
2. **Accurate Chinese text rendering** (Chinese signage in the prompt is drawn correctly)
3. It ships an nvfp4 build at **4.51 GB** — on a 24 GB machine the model *and* its encoder fit fully
   in VRAM, with no offload at all

### 6.2 Image editing — FLUX.2 Klein 4B

| Item | Value |
|---|---|
| DiT | `flux-2-klein-4b-fp8.safetensors` — 4.07 GB |
| Encoder | `qwen_3_4b_fp4_flux2.safetensors` — 3.85 GB |
| Key parameters | `CLIPLoader` type = **`flux2`**; `ReferenceLatent` ×2; `Flux2Scheduler` **20 steps**; CFGGuider **CFG=5** |
| Measured | **42.3 s** |

**A counter-intuitive finding**: BFL's official fp8 single file is only **4.07 GB**, whereas the bf16
build is 7.75 GB — **fp8 costs essentially nothing in quality and halves the size**. When a vendor
ships the good stuff directly, take it.

An even more counter-intuitive point: **the 9B NVFP4 build is only 5.76 GB — smaller than the 4B
bf16 build (7.75 GB).** A bigger model in a smaller file. That is the value of 4 bits.

### 6.3 Video + audio — MiniMax H3

This is the heaviest line here, because it **generates picture and sound together**.

| Item | Value |
|---|---|
| DiT | `minimax_h3_fl2va_pruned_int8_convrot.safetensors` — **20.97 GB** |
| Text encoder | `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` — **15.69 GB** |
| Video VAE | `minimax_h3_video_vae_fp16.safetensors` — 5.21 GB |
| Audio VAE | `minimax_h3_audio_vae_fp32.safetensors` — 0.61 GB |
| Accelerator LoRA | 4-step / 8-step turbo, 1.96 GB each (**the official blueprint uses 8-step**) |
| Key parameters | `BasicScheduler(simple, 8 steps)` + `KSamplerSelect(res_multistep)` + `SamplerCustomAdvanced`; **do not use `MiniMaxH3SigmaShift`** |
| Measured | smoke 768×448/56 frames = **76.3 s**; full 1344×768/124 frames = **519.1 s** |

**Offloading is mandatory.** The DiT (21 GB) plus the encoder (15.7 GB) is 36.7 GB — far beyond 24 GB.
So every generation shuttles weights between VRAM and RAM. That, not raw compute, is why it takes
519 seconds.

**Output verification** (a step you must not skip): `ffprobe` confirms
**h264 / 1344×768 / 24fps / 5.17 s + aac 32 kHz stereo**. Extracting four frames into a contact sheet
shows the imagery matching the prompt's timeline (an RGB-split "COMFYUI" title → chrome palm trees →
sunset). **This is not noise. It is usable video with usable audio.**

### 6.4 Video only — HunyuanVideo 1.5

| Item | Value |
|---|---|
| DiT | `hunyuanvideo1.5_480p_t2v_fp16.safetensors` — 16.65 GB |
| Text encoder | **`DualCLIPLoader`** (type=`hunyuan_video_15`) = `qwen_2.5_vl_7b_fp8_scaled` + `byt5_small_glyphxl_fp16` |
| VAE | `hunyuanvideo15_vae_fp16.safetensors` — 2.52 GB |
| Accelerator LoRA | `hunyuanvideo1.5_t2v_480p_lightx2v_4step_lora_rank_32_bf16.safetensors` — 0.34 GB |
| Measured | 848×480 / 121 frames (5.04 s) = **117.0 s** |

**⚠️ A crucial conceptual distinction: `480p` / `720p` / `i2v` / `SR` are four different base
models**, not one model at different resolutions. The resolution in the filename is **part of the
model's identity**.

**Four-step generation is its main value** — 117 seconds for 5 seconds of video means real iteration
speed. The 720p 50-step path is higher quality but far slower. **Prototype prompts at 480p, then
commit to 720p** — that is the recommended workflow.

**Output verification**: `ffprobe` confirms h264 / 848×480 / 24fps / 121 frames / 5.04 s. A frame
contact sheet shows a temporally stable, subject-consistent result — *"a pottery studio: the wheel
slowly turns, wet clay is pulled taller into a vase between two hands, warm rim light from the left,
blurred wooden shelves of bisque ware behind"* — **every element of the prompt is present.**

### 6.5 The one that does not run — FLUX.2 Klein 9B

**This is the only line we could not get running, and the reason is instructive.**

The error:

```
mat1 and mat2 shapes cannot be multiplied (1024x7680 and 12288x4096)
```

**Root cause**: the 9B model needs a Qwen3-VL text encoder of roughly **16.4 GB**, and BFL ships it
**only in diffusers sharded format** — which ComfyUI cannot load.

**This is not a VRAM problem, and not a quantization problem. It is a weight-packaging problem.**
Three ways out:
1. Wait for ComfyUI's official single-file packaging of the encoder
2. Merge the diffusers shards into a ComfyUI-loadable single file yourself (16.4 GB download plus a conversion script)
3. **Use the 4B** — 42.3 seconds per image, and it is enough

> **Lesson**: when picking a model, check not only "does it fit in VRAM" but also **"is its weight
> format loadable by my tooling?"** Many people overlook this precondition.

### 6.6 Benchmark summary

![Measured generation time per workflow](assets/chart5-model-benchmark.svg)

> All times are read from ComfyUI's server-side `execution_start` / `execution_success` timestamps —
> **never wall-clock time or API round-trip time**, which would fold queueing and model-loading into
> the number and inflate it.

**An honest note**: we timed Z-Image twice and got `20.9 / 15.8 s` and `17.7 / 13.8 s`.
**Run-to-run variance in absolute terms is about ±15%** (a laptop GPU throttles against thermal and
power limits), but **the relative result — nvfp4 is 22–25% faster than int8 — held in both runs.**

> **When reporting performance, relative percentages are far more trustworthy than absolute values.**

---

## 7. Optimization checklist (configs you can copy)

![What NVFP4 actually buys you](assets/chart6-nvfp4-gain.svg)

### 7.1 Ordered by payoff

| Priority | Optimization | Payoff | Cost |
|---|---|---|---|
| **P0** | Use **NVFP4** for every 4-bit model | 22% faster, 27% smaller, no measurable quality change | none |
| **P0** | Use a **distilled LoRA to cut steps** (8 → 4) | up to 2× faster | tune the LoRA strength |
| **P1** | **Tiled VAE decode** (`VAEDecodeTiled`) | avoids transient OOM at high resolution | slightly slower |
| **P1** | **Free VRAM before each run** (`POST /free`) | avoids leftovers breaking sequential runs | none |
| **P2** | Restart or force-unload when switching model families | avoids fragmentation | extra waiting |
| **P2** | Prototype long video prompts at 480p, commit at 720p | saves a lot of trial time | none |

### 7.2 Two VRAM traps you must know

**Trap one: ComfyUI does not release models on its own.**
After generating one image, the model is still resident. Chaining a second generation — especially a
video — very easily OOMs. Fix: call
`POST /free {"unload_models": true, "free_memory": true}` before each submission.

> ⚠️ Note that `/free` returns an **empty body**. Do not try to parse it as JSON, or you will get a
> `JSONDecodeError`.

**Trap two: the transient peak in VAE decoding.**
VAE decoding of high-resolution images or video creates a transient VRAM spike on the **final step**
(several GB), producing the classic "the transformer finished and then it died at the last step."
Fix: use `VAEDecodeTiled`.

---

## 8. Troubleshooting table

| Symptom | Actual cause | Fix |
|---|---|---|
| Download stalls at some percentage, 0.0 MB/s, **no error** | "Slow drip" defeats the socket timeout | Add an **application-level silent watchdog**: 150 s without real progress → disconnect and retry |
| Every source probe times out | Bandwidth already saturated by concurrent downloads | Probe while idle, or rate-limit probes separately |
| Downloader starts with a huge slow file and the queue dies | An hf-only file holds the worker | Sort pending work **by whether a fast source exists** |
| `POST /prompt` returns 400 | Missing model **or** a bad graph | Read `node_errors`: only `value_not_in_list` → the graph is fine |
| HunyuanVideo 1.5 reports an encoder type error | `CLIPLoader` has no `hunyuan_video_15` | Use `DualCLIPLoader` |
| Z-Image reports a CLIP type error | It needs `lumina2`, not `qwen` | Change the type |
| FLUX.2 reports a CLIP type error | It needs `flux2` | Change the type |
| You want text-to-video but the node says `ImageToVideo` | The image input is **optional** | Leave the image input **unconnected** |
| `mat1 and mat2 shapes cannot be multiplied` | Encoder packaging mismatch (diffusers shards) | Use a single-file packaging, or a smaller model |
| `/free` throws a JSON parse error | It returns an empty body | Check for empty before parsing |
| Video renders but the frames look like noise | Output verification was skipped | Run `ffprobe` plus a frame contact sheet |
| A low PSNR after switching quantization "proves" quality loss | **Method error: the encoder was not fixed** | See §5 — you need a control plus a seed baseline |

---

## 9. Toolchain

### 9.1 Six scripts

| Script | Purpose |
|---|---|
| `scripts/dl_models.py` | Multi-source downloader: three-tier fallback + silent watchdog + Range sizing + resume |
| `scripts/verify_models.py` | Three-layer validation: byte size + safetensors structure + dtype detection |
| `scripts/run_workflow.py` | API submission + **server-authoritative timing** (reads `execution_start`/`success`) |
| `tools/compare_ab.py` | Controlled A/B: PSNR + per-tile PSNR + difference heatmap + side-by-side |
| `tools/ab_metrics.py` | Four-arm paired PSNR + quality proxies (sharpness/entropy/high-frequency/histogram) |
| `tools/make_charts.py` | Regenerates every SVG chart in this document |

### 9.2 Quick start

```bash
# 1) Assumes ComfyUI is already serving on http://127.0.0.1:8188

# 2) Download the models (three-tier fallback)
python scripts/dl_models.py

# 3) Three-layer validation (bytes + structure + dtype)
python scripts/verify_models.py --refresh

# 4) Run one workflow and get the server-authoritative time
python scripts/run_workflow.py workflows/z_image_turbo_nvfp4.json --free

# 5) Run a controlled A/B (same encoder, quantization is the only variable)
python tools/compare_ab.py
python tools/ab_metrics.py
```

### 9.3 Repository layout

```
.
├── README.md              # Chinese
├── README_EN.md           # English (this file)
├── index.html             # Online edition (adapts to your browser language)
├── assets/                # All SVG charts, generated by tools/make_charts.py
├── data/                  # Raw measurements
├── docs/                  # Deep dives
├── scripts/               # Reproducible scripts
└── tools/                 # Analysis and charting tools
```

---

## 10. Conclusion and what is next

### 10.1 Conclusions

1. **24 GB of VRAM is enough for the newest and strongest open-weight generative models** — provided
   you accept offloading and **choose the right quantization format**
2. **NVFP4 is the best choice on Blackwell** — backed by a controlled experiment, not by a feeling
3. **Quantization makes a model fit; a distilled LoRA makes it fast** — neither substitutes for the other
4. **Quantization comparisons on generative models require a noise baseline** — otherwise PSNR is
   badly misread

### 10.2 Open items

| Item | Status |
|---|---|
| HunyuanVideo 1.5 **720p, 50 steps** | Base model (16.65 GB) ready, workflow built, not yet run |
| CLIP semantic similarity | Use CLIP scoring instead of PSNR to quantify semantic agreement |
| Larger-sample A/B | Currently 2 seeds per quantization; expand to 8 to shrink variance |
| FLUX.2 Klein 9B | Blocked on encoder packaging |
| MiniMax H3 with the 4-step LoRA | Expect roughly half the time; quality needs re-evaluation |

---

## Appendix A: Complete model manifest (34 files / 125.6 GB)

<details>
<summary>Expand to see every file</summary>

**MiniMax H3 (video + audio)**

| File | Size |
|---|---|
| `minimax_h3_fl2va_pruned_int8_convrot.safetensors` | 20.97 GB |
| `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | 15.69 GB |
| `minimax_h3_video_vae_fp16.safetensors` | 5.21 GB |
| `minimax_h3_video_vae_int8_convrot.safetensors` | 2.81 GB |
| `minimax_h3_fun_controlnet_union_pruned_int8_convrot.safetensors` | 2.30 GB |
| `minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors` | 1.96 GB |
| `minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors` | 1.96 GB |
| `minimax_h3_audio_vae_fp32.safetensors` | 0.61 GB |
| `minimaxh3_*` effect LoRAs × 10 (art explosion / blooming flowers / bullet time / dark magic / fire breath / four seasons / kiss camera / spiral ascent / storm magic / truman show) | < 0.01 GB each |

**Z-Image-Turbo (image)**

| File | Size |
|---|---|
| `z_image_turbo_int8_convrot.safetensors` | 6.20 GB |
| `z_image_turbo_nvfp4.safetensors` | 4.51 GB |
| `qwen_3_4b.safetensors` (bf16) | 8.04 GB |
| `qwen_3_4b_fp4_mixed.safetensors` | 3.48 GB |
| `ae.safetensors` | 0.34 GB |

**FLUX.2 Klein (image editing)**

| File | Size |
|---|---|
| `flux-2-klein-9b-nvfp4.safetensors` | 5.76 GB |
| `flux-2-klein-4b-fp8.safetensors` | 4.07 GB |
| `qwen_3_4b_fp4_flux2.safetensors` | 3.85 GB |
| `flux2-vae.safetensors` | 0.34 GB |

**HunyuanVideo 1.5 (video)**

| File | Size |
|---|---|
| `hunyuanvideo1.5_720p_t2v_fp16.safetensors` | 16.65 GB |
| `hunyuanvideo1.5_480p_t2v_fp16.safetensors` | 16.65 GB |
| `hunyuanvideo15_vae_fp16.safetensors` | 2.52 GB |
| `sigclip_vision_patch14_384.safetensors` | 0.86 GB |
| `byt5_small_glyphxl_fp16.safetensors` | 0.44 GB |
| `hunyuanvideo1.5_t2v_480p_lightx2v_4step_lora_rank_32_bf16.safetensors` | 0.34 GB |
| `hunyuanvideo15_latent_upsampler_720p.safetensors` | 0.09 GB |

**Validation result: 34 / 34 complete, 125.6 GB, 0 corrupt.**

</details>

## Appendix B: Raw measurements

See the [`data/`](data/) directory:

- [`data/quant-ab-metrics.md`](data/quant-ab-metrics.md) — full controlled A/B metrics
- [`data/benchmark-results.md`](data/benchmark-results.md) — server-side time per workflow
- [`data/download-manifest.md`](data/download-manifest.md) — size and dtype of all 34 files

## Appendix C: Glossary

| Term | Meaning |
|---|---|
| **offload** | Shuttle weights between VRAM and system RAM so a model larger than VRAM can still run |
| **W4A16** | 4-bit weights, 16-bit activations; saves VRAM but gives no speedup |
| **W4A4** | Both weights and activations 4-bit; saves VRAM and goes faster |
| **NVFP4** | Blackwell's native 4-bit float format; tensor cores consume it directly |
| **ConvRot** | Rotation compensation that lets INT8 quantization run on the BF16 compute path |
| **Distilled LoRA** | A distilled "fewer-steps" adapter, e.g. 4 steps instead of 20+ |
| **PSNR** | Peak signal-to-noise ratio; **not valid as a standalone quality judge for generative models** |
| **subgraph** | ComfyUI's newer blueprint packaging, where node types are UUIDs |
| **VAE tiling** | Chunked decoding, to avoid the transient VRAM spike at high resolution |

## Appendix D: Why a single repository, not one per model

We settled this before writing any code: **should each model (say MiniMax H3) get its own repository?**

### The two options

| Dimension | Single repo (this one) | One repo per model |
|---|---|---|
| Reuse of the core methodology | ✅ Controlled A/B, downloader, verifier written **once** | ❌ Copied N times; a single fix must be applied N times |
| Comparability of results | ✅ All four model lines measured with **one yardstick** | ❌ Each does its own thing; cross-model numbers aren't comparable |
| Readability of "why we chose it" | ✅ One page shows the whole picture and the trade-offs | ❌ The reader must hop across four repos to assemble it |
| Per-model depth | ➖ Handled by focused long-form docs under `docs/` | ✅ Naturally isolated |
| Maintenance cost | ✅ Update once, everything benefits | ❌ N× |
| Sharing cost | ✅ One link = the complete framework | ❌ Must first explain "which repo to read" |

### Our call

**A single repo, with per-topic deep dives under `docs/`.**

One reason, but a hard one: **what makes this guide valuable is the methodology, not any single model's parameters.**

- Across all four model lines the reusable parts are **the same**: the four-arm controlled A/B design, the multi-source downloader with a silent watchdog, three-layer model verification, server-authoritative timing.
- The **non-reusable parts — each model's own node constraints and parameters — are small**: one chapter (§6) covers them.
- Split into four repos, that methodology gets copied four times. Improve the A/B method in one repo and the other three never catch up — which is exactly how results **stop being comparable**.

> **Rule of thumb**: the larger the shared *method* and the smaller the model-specific *parameters*, the more you should merge into a single repo.
> Conversely, splitting pays off only when each model genuinely needs its own toolchain and dataset.

### When splitting would become right

Any one of these would justify it:

1. A model's toolchain becomes truly independent (e.g. it needs a dedicated training / fine-tuning pipeline)
2. The repo bloats until cloning is painful (bulk data or weights committed — note this repo ships **scripts and charts only, no weights**)
3. The team splits so that each model is maintained by a different person

Until then, the **benefits of the single repo — reusable, comparable, explained in one pass — far outweigh the cost.**

---

## License

[MIT](LICENSE). Every measurement here comes from a real run on this machine — corrections and
reproduction attempts are welcome.
