# A controlled experiment for comparing quantization formats

> See also: [中文](controlled-ab-methodology.md) · Data in [`../data/quant-ab-metrics.md`](../data/quant-ab-metrics.md) · Tool in [`../tools/ab_metrics.py`](../tools/ab_metrics.py)

This document explains how to determine whether a quantization format costs image quality. It is
not a theoretical argument — it is the record of **getting it wrong with a plausible method, and
then fixing it**.

---

## 1. Why intuition misleads you here

Our first comparison ran two Z-Image-Turbo variants and measured PSNR = 13.82 dB. We concluded:
"4-bit quantization degrades quality."

**The error: the two variants used different text encoders.**

- the int8 build was paired with `qwen_3_4b.safetensors` (bf16)
- the nvfp4 build with `qwen_3_4b_fp4_mixed.safetensors` (fp4)

Encoder differences were folded into that 13.82 dB. We measured the combined effect of *encoder plus
quantization* and attributed all of it to quantization.

> **Lesson 1: change one variable at a time. Encoder, prompt, resolution, steps, sampler, CFG and
> seed must all be pinned — everything except the one thing you are measuring.**

---

## 2. Why PSNR alone still is not enough

Even with the variables cleanly controlled, a deeper problem remains:

> **Diffusion sampling is chaotic.**

Two models whose weights agree to four decimal places will produce **entirely different
compositions** after 8 sampling steps, because the process continuously amplifies tiny differences.
This is the nature of generative sampling, not a defect.

The consequence is severe:

| What you observe | What you may conclude |
|---|---|
| two images with PSNR = 16 dB | they are two different samples |
| two images with PSNR = 16 dB | ❌ **not** "one of them is worse" |

So PSNR by itself **cannot answer** whether quantization damaged quality. It lacks a frame of
reference.

> **Lesson 2: you need a noise baseline — the difference caused by "same quantization, different
> random seed". Only by comparing quantization drift against seed drift does PSNR become
> interpretable.**

---

## 3. Designing the four-arm control

The goal: separate *quantization perturbation* and *sampling randomness* into two comparable
quantities.

| Arm | Held fixed | Varied | Purpose |
|---|---|---|---|
| **det** | everything | **nothing** (re-run) | determinism check |
| **seed** | everything + quantization A | random seed only | noise floor |
| **cross** | everything + a fixed seed | **quantization only** | the measurement |
| **seedB** | everything + quantization B | random seed only | noise floor, second copy |

**Decision rule:**

```
cross similarity >= seed similarity   ->  quantization drift <= sampling noise  ->  negligible
cross similarity << seed similarity   ->  quantization introduces real distortion
```

### Why the `det` arm is not optional

If `det` does not equal infinity (byte-identical), the pipeline itself is not reproducible. Then the
`cross` arm's difference could come from quantization *or* from run-to-run noise — **it cannot be
attributed, and the whole experiment is worthless.**

We measured `det` first, got infinity, and only then proceeded.

---

## 4. Results

| Arm | Variable | PSNR | Mean pixel difference |
|---|---|---|---|
| **det** same quant, same seed, re-run | none | **∞ dB** | **0.00%** |
| **seed** int8, different seed | seed only | 12.10 dB | 16.89% |
| **cross** nvfp4 vs int8, same seed | **quantization only** | **16.84 dB** | **7.41%** |
| **seedB** nvfp4, different seed | seed only | 12.45 dB | 16.43% |

**7.41% < 16.89%** — changing the quantization format alters the image **less than changing the
random seed does.**

---

## 5. Why PSNR alone is not enough: five robust proxies

PSNR is sensitive to trajectory divergence, so we also measured quality proxies that are **not**.

| Metric | Definition | What it answers |
|---|---|---|
| Sharpness | variance of a Laplacian response | was detail lost (did it get soft)? |
| Shannon entropy | information entropy of the grey histogram | did information content drop? |
| High-frequency ratio | `mean(‖img − blur‖) / std(img)` | how much fine detail survived |
| Colour histogram L1 | three-channel distribution distance | any systematic colour shift? |
| Per-tile PSNR | PSNR computed on a 4×4 grid | is the difference **distributed** or **localised**? |

Measured:

| Sample | Sharpness | Entropy | HF ratio |
|---|---|---|---|
| int8 · seed A | 776.5 | 5.572 | 0.0130 |
| int8 · seed A (re-run) | 776.5 | 5.572 | 0.0130 |
| int8 · seed B | 705.4 | 5.736 | 0.0134 |
| nvfp4 · seed A | 694.3 | 5.614 | 0.0127 |
| nvfp4 · seed B | 604.1 | 5.791 | 0.0140 |

Two things to read out of this:

1. **The re-run row matches the baseline exactly** (776.5 / 5.572 / 0.0130) — corroborating the
   `det` arm's PSNR = ∞. The pipeline really is deterministic.
2. **The seed spread within one quantization (776.5 → 705.4, −71.1) already covers the entire
   cross-quantization difference (776.5 → 694.3, −82.2).** Same magnitude — so quantization is not a
   distinguishable factor.

The per-tile PSNR grid agrees — no tile collapses toward zero:

```
 18.8  35.9  33.5  28.2
 14.2  17.7  15.7  16.2
 15.3  11.3  18.3  13.7
 25.1  18.1  18.2  18.2
```

> A **structural artifact** (say a block effect from some quantizer) concentrates its difference in
> specific regions and produces isolated very low tiles. A distributed difference is what sampling
> divergence looks like.

---

## 6. The last gate: human review

Lay the four images out **2×2**, deliberately arranged so that **reading down a column = same seed,
different quantization** and **reading across a row = same quantization, different seed**:

```
┌──────────────────────┬──────────────────────┐
│  INT8  · seed 20260922│  INT8  · seed 20260923│
├──────────────────────┼──────────────────────┤
│ NVFP4  · seed 20260922│ NVFP4  · seed 20260923│
└──────────────────────┴──────────────────────┘
   column → same seed, cross-quant   row → same quant, cross-seed
```

Result: **columns are highly similar; rows are entirely different.** The visual verdict matches every
number.

> The layout is itself part of the method — one image conveys both controls at once, more legibly
> than two pairwise comparisons.

---

## 7. A checklist you can reuse directly

Before running any "does quantization hurt quality?" comparison, confirm each line:

- [ ] encoder, prompt, resolution, steps, sampler and CFG are **all pinned**
- [ ] only the quantization format varies
- [ ] the `det` arm was run and re-runs are byte-identical (otherwise fix determinism first)
- [ ] the `seed` / `seedB` arms were run to obtain the noise floor
- [ ] `cross` PSNR is at or above the `seed` arms
- [ ] quality proxies (sharpness / entropy / HF / colour) show no systematic difference
- [ ] per-tile PSNR shows no localised collapse (rules out structural artifacts)
- [ ] the 2×2 contact sheet passes human review

Only when all eight hold may you claim "quantization costs no quality".

---

## 8. Where this method applies

**Applies to**: quantization of diffusion and autoregressive generative models of any modality
(image / video / audio), choosing between quantization builds, evaluating the fidelity of a
distilled LoRA, and attributing differences before and after fine-tuning.

**Does not apply to**: discriminative models, classifiers, super-resolution and other tasks where
the output is a **continuous, deterministic function of the input**. There, PSNR is directly usable
and no noise floor is needed.

**In one sentence**: **PSNR is the instrument; the noise baseline is the ruler. Without the ruler,
the reading means nothing.**
