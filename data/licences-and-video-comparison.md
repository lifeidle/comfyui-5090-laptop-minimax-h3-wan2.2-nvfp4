# Round 4 — licence verification and a same-prompt video comparison

## 1. Licence verification results

Every licence marked ⚠️ in Appendix F.2 was re-checked against public sources on 2026-09-22.

| Model | Verdict | Source basis |
|---|---|---|
| Z-Image-Turbo | **Apache 2.0** — commercial OK | multiple independent sources |
| Qwen-Image 2512 | **Apache 2.0** — commercial OK | multiple independent sources |
| Wan 2.2 (5B/14B) | **Apache 2.0** — commercial OK | registry-verified. **"Wan 2.7 is open source" is false** — the open line ends at 2.2; 2.5/2.6/2.7 are API-only |
| ERNIE-Image (+Turbo) | **Apache 2.0** — commercial OK | 8B DiT; GenEval 0.8856, LongTextBench 0.9733 |
| FLUX.2 Klein 4B | **Apache 2.0** — commercial OK | BFL's first fully Apache-2.0 FLUX model |
| FLUX.2 Klein 9B | **FLUX Non-Commercial Licence** — no commercial use | opposite of the 4B |
| FLUX.1-dev | FLUX.1-dev Non-Commercial — no commercial use | baseline only |
| MiniMax H3 | **MiniMax Community Licence** — conditional | **Excluded territories: EU, UK, South Korea and the United States** (local deployment unlicensed there); commercial use allowed under **$20M annual revenue** with prominent "MiniMax H3" attribution. MiniMax states the carve-out stems from its **ongoing generative-video copyright litigation with major Hollywood studios** |
| MiniMax Music 3 | **⚠️ sources conflict** | one reports **CC BY-NC 4.0** (no commercial use); others report the **MiniMax-Music3 Community Licence** (commercial + on-screen attribution + $20M threshold). **Read the repo's LICENSE file directly** |
| Stable Audio 3 Medium | **Stability AI Community Licence** — commercial OK **under $1M annual revenue** | trained on fully licensed audio (806k AudioSparx + 473k Freesound; UMG/Warner partnerships); **instrumental only — no vocals or lyrics**; outputs are owned by the user |
| Hunyuan3D 2.1 | Tencent Community Licence — conditional | commercial ≤ **1M MAU**; **territory excludes EU/UK/South Korea**; must ship a Notice file and mark products **"Powered by Tencent Hunyuan"**; **may not be used to train other AI models** |
| LTX-Video / LTX-2.3 | LTX Community Licence — free commercial use **under $10M annual revenue** | frequently mis-described as Apache 2.0 |
| YuE2 | **CC BY-NC 4.0** — no commercial use | |
| ACE-Step 1.5 | Apache 2.0 (one source says MIT) — no revenue threshold either way | |
| Lens | **still unverified** — Comfy-Org/Lens is a repackage; the original vendor is not identified in the template | |

## 2. Same-prompt video comparison

One identical Chinese prompt for all three lines:
*"特写镜头，一只蜂鸟悬停在红色花丛前采蜜，翅膀高速振动，阳光透过花瓣，背景虚化，镜头缓慢横移"*

| Model | Resolution / frames | Steps | Exec (s) | Followed the prompt? |
|---|---|---|---|---|
| Wan 2.2 5B TI2V | 1280×704 / 121 | 20 | 355.1 | ✅ fully |
| MiniMax H3 | 1344×768 / 124 | 8 | 539.5 | ✅ fully (better composition/detail) |
| LTX-Video 2B distilled | 1216×704 / 121 | 8 (CFG 1) | 23.2 | ❌ unrelated Mediterranean coastline |

### LTX diagnosis (three controlled steps)

| Step | Change | Result |
|---|---|---|
| 1 | same prompt in **English** | still the coastline |
| 2 | **different seed** (20260922 → 777) | still the coastline |
| 3 | **different common prompt** ("red sports car on a desert highway at sunset") | a parking lot / road — broad scene type matches, **no car** |

**Conclusion:** LTX-Video 2B distilled at **CFG=1 / 8 steps** captures broad scene type but not
specific subjects. The speed is paid for with prompt adherence. This is a property of the
*distilled + CFG-free* configuration we chose, not necessarily of the architecture.
