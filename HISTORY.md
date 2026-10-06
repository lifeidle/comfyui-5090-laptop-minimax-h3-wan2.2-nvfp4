# 项目全史 · 从部署到定稿

> **这份文档是给"下一个接手的 AI"看的交接文档。**
> 目标：读完这一篇，就能明白这个项目从头到尾做了什么、为什么这么做、现在处于什么状态、下一步该干什么。
> 配套阅读：`README.md`（技术手册本体）、`data/*.md`（7 份原始数据）、`附录 A–F`。
>
> 最后更新：2026-10-06 · 仓库 106 文件 · 与远端完全一致

---

## 0. 项目一句话

**在 24 GB 显存的笔记本 GPU（RTX 5090 Laptop）上，把当前能拿到权重的一切主流开源生成模型跑通、测透、
写成一份中英双语、带受控实验和授权矩阵的实战手册，发布在 GitHub Pages。**

- 仓库：https://github.com/lifeidle/comfyui-5090-laptop-minimax-h3-wan2.2-nvfp4
- 在线：https://lifeidle.github.io/comfyui-5090-laptop-minimax-h3-wan2.2-nvfp4/
- 本地：`C:\Users\chenhua\Desktop\3\comfyui-5090-laptop-playbook\`
- 模型库：`D:\models\comfyui-models\`（`D:\ComfyUI\models` 是指向它的 junction）
- ComfyUI：`D:\ComfyUI`，venv 在 `D:\aigc\venv`，端口 8188

---

## 1. 时间线总览

| 阶段 | 日期 | 主题 | 结果 |
|---|---|---|---|
| **P0–P2 部署** | 9 月中 | ComfyUI 0.37.0 + 模型落位 | ✅（另一台工作区做的） |
| **P3 三图跑通** | 09-22 上午 | SDXL / FLUX.1-dev / Qwen-Image 2512 | ✅ 14.1 / 32.1 / 206.7 s |
| **LoRA 加速** | 09-22 | Qwen-Image 2512 + Lightning | ✅ 206.7 → **12.2 s**（16.9×） |
| **覆盖度审计** | 09-22 下午 | 用户问"最先进的都试了吗" | ❌ 没试完：视频"下了没跑"、音乐**完全空白** |
| **第二轮补齐** | 09-22 | Wan 2.2 14B/5B、LTX、4 条音乐线、Hunyuan3D | ✅ 音乐从 0 → 4 条 |
| **第三轮补完** | 09-22 | FLUX.2 Klein 9B、Lens、ERNIE、Stable Audio 3 | ✅ 覆盖度终态 21 组 |
| **手册上线** | 09-22 | 双语手册 + GitHub Pages | ✅ 40 → 76 文件 |
| **法律附录** | 09-22 | 附录 F 授权核实 + 隐私清理 | ✅ 18 模型逐一核实 |
| **同提示词对比** | 09-22 | 三条视频线同提示词 | ⚠️ 发现 LTX 不跟随提示词 |
| **顶部图选区** | 09-22 | 三套方案 + 授权矩阵 4 张图 | ✅ |
| **SEO + 改名** | 09-22 | 仓库名、title、topics | ✅ 改为现名 |
| **0.38.0 升级** | 10-05 | ComfyUI 0.37 → 0.38 + 清库 167 GB | ✅ 965 节点 |
| **六轮扩展** | 10-05 | Qwen-Image 2.1、Kandinsky 5 双线、Chroma、PixelDiT、SeedVR2 | ✅ 覆盖度 27 组 |
| **翻案** | 10-05 | PixelDiT 潜空间超分 | ★ **推翻唯一一条"不可行"** |
| **图集** | 10-05 | 14 张实拍产物图进仓库 | ✅ 定稿 |

---

## 2. 当前环境（接手前先核对）

| 项 | 值 | 备注 |
|---|---|---|
| ComfyUI | **0.38.0**，965 节点 | 0.37.0 时是 960 |
| PyTorch | 2.11.0+**cu128** | ⚠️ cu130 内核被禁用（见 §6） |
| Python | 3.11.9（`D:\aigc\venv`） | |
| comfy-kitchen | 0.2.36 | 0.2.35 会导致 SeedVR2 崩溃 |
| GPU | RTX 5090 Laptop，24,435 MiB，sm_120 | 支持 NVFP4 |
| 模型库 | **~402 GB / 85 个物理文件** | D 盘可用 ~273 GB |
| 启动 | `cd /d/ComfyUI && /d/aigc/venv/Scripts/python.exe main.py --listen 127.0.0.1 --port 8188` | **必须用 Bash 工具的 `run_in_background: true`**，`nohup &` 活不过调用结束 |

---

## 3. 各阶段详解

### 3.1 部署与核验（9 月中–09-22 上午）

接手时 P0–P2 已完成，但 **P3 三条工作流一个都没跑过**（`output/` 为空）。

做的第一件事不是跑，而是**用 safetensors header 核验每个文件的真实身份** —— 因为发现：
- `models\clip\clip_l.safetensors` 内容其实是 **CLIP-G**（32 层 / hidden 1280 / 有 `text_projection`），
  而 `text_encoders\clip_l.safetensors` 才是真 CLIP-L（12 层 / 768）
- LTX-Video 的 text_encoder 是 **fp32 diffusers 分片**（18 GB），ComfyUI 只吃单文件
- SDXL diffusers 目录缺 `model_index.json`，还有 4 个 `.incomplete` 占 19.5 GB

**方法论确立**：验模型身份**只认 safetensors header**（前 8 字节小端 uint64 = header 长度 → JSON），
**不信文件名**。这条贯穿了整个项目。

随后 13/13 模型下载校验通过（90.9 GB），P3 三图跑通。

### 3.2 两个可选项全做（09-22）

1. **LoRA 加速**：`Qwen-Image-2512-Lightning-4steps-V1.0-fp32`（1.58 GB）→
   官方参数 4 步 / cfg 1.0 / strength 1.0，从 `definitions.subgraphs[0].links` 还原出确切拓扑
   （三个 `ComfySwitchNode` 由同一 `PrimitiveBoolean` 驱动）→ **206.7 → 12.2 s**
2. **冗余 VAE 回收**：先证明等价再删 —— 两边各 194 张量，`(dtype, shape, sha1)` 多重集完全相同，
   只是 key 命名不同（diffusers `quant_conv` vs Comfy `conv1/conv2`）→ 242 MB 回收

### 3.3 覆盖度审计（用户追问"最先进的都试过了吗"）

**结论：没有。** 图像覆盖最好，视频"下了没跑"居多，**音乐完全空白**。
而且发现手册**漏掉了 P3 那批 90.9 GB** 和"下了没跑"的那批 —— 手册只写了最后一批 125.6 GB。

还发现一处**事实错误**：§6.1 把"中文文字渲染准确"归给 Z-Image-Turbo，但证据
（30/30 逐字全对）实为 **Qwen-Image 2512** 的成绩 —— Z-Image 的中文渲染从未单独验证。已修。

### 3.4 第二轮：音乐从 0 到 4 条线 + Wan 2.2

发现 ComfyUI 0.37 **原生支持** ACE-Step 1.5 / YuE2 / MiniMax Music 3 / Stable Audio 3，
**不需要任何 custom node**。音乐从 0 补到 4 条。

同时写了 **`ui2api.py` —— 官方模板 → API 工作流转换器**，踩了 8 个坑（详见 §7）。

### 3.5 第三轮：第二次误判纠正

旧结论"FLUX.2 Klein 9B 编码器只有 diffusers 分片无法加载"**只对 BFL 官方仓库成立** ——
**`Comfy-Org/flux2-klein-9B` 有单文件编码器**（`qwen_3_8b_fp8mixed` 8.66 GB），18.3 GB 装得下，18.9 s 出图。

> **教训（与 LTX-2.3 同源）：下结论前先查 Comfy-Org 的 repackage 仓库 —— 那是事实上的标准发布渠道。**

### 3.6 手册上线 + 法律附录 + 同提示词对比

手册发布后做了三轮深化：
- **附录 F 授权核实**：18 个模型逐个查。两个关键法律事实：
  - **FLUX.2 Klein 的 4B 与 9B 授权相反**（4B=Apache 2.0 / 9B=禁商用）
  - **MiniMax H3 排除 US/EU/UK/KR 四地，中国大陆在授权范围内**；商用 < $2000 万 + 界面标注即可
- **同提示词视频对比**：三条线同一句蜂鸟提示词 → Wan ✅ / MiniMax H3 ✅（构图更好）/ **LTX ❌ 完全无关**
  - 三步诊断排除中文问题、排除偶然 → **LTX 蒸馏版在 CFG=1/8 步下提示词遵循极弱**
  - → LTX 从"视频速度首选"**降级**
- **顶部"三套方案"图选区** + 商用过滤（禁商用模型从推荐位移除）
- **SEO**：title/description/topics 补模型名；**仓库改名**（见 §5）

### 3.7 10-05：0.38.0 升级 + 清库 167 GB

- **升级路径**：github.com 被墙 → **codeload.github.com tarball** 可用；
  覆盖安装时 `tar --exclude` 掉 models/custom_nodes/user/input/output/.git
- **清库**：删 42 文件 / 167.4 GB（515.6 → 348.2 GB），三类：
  从未运行过的 diffusers 重复件 95.1 GB / 被取代的旧模型 42.1 GB / 失败路径 39.1 GB
- **0.38.0 让三个数字变旧**：ACE-Step **28.6 → 20.8 s（−27%）**、YuE2 93.7 → 87.5、FLUX.1-dev 32.1 → 30.1
- **cu130 内核问题没被解决** → §5「NVFP4 快 22%」**仍是下界**

### 3.8 10-05 六轮扩展（覆盖度 21 → 27 组）

| 轮 | 内容 | 关键数字 |
|---|---|---|
| 四 | **Qwen-Image 2.1** | 72.7 s @1328²/25步，中文同样 30/30；同质量档比 2512 快 2.8×，17.3 GB |
| 五 | Kandinsky 5 T2I Lite + SeedVR2 3B | 68.1 s / 23.6 s（768²→3072²） |
| 六 | PixelDiT 1.3B + Chroma1-HD + Kandinsky 5 T2V | **10.1 s**（全表最快 1024²）/ 42.6 s / 884.5 s |
| 七 | **★ PixelDiT 潜空间超分** | **1024²→2048² 仅 5.4 秒** |

---

## 4. 当前最终结论（§11 摘要）

| 领域 | 选择 | 耗时 | 备注 |
|---|---|---|---|
| **图像（最快）** | PixelDiT 1.3B | **10.1 s** @1024² | 潜空间 DiT 架构 |
| **图像（最快+中文）** | Qwen-Image 2512 + Lightning | **12.2 s** @1328² | 中文 30/30 逐字全对 |
| **图像（满质量+中文）** | Qwen-Image 2.1 int8 | **72.7 s** @1328² | 中文 30/30；比 2512 快 2.8×；17.3 GB |
| 图像（常驻显存） | Z-Image-Turbo nvfp4 | 13.8 s @1024² | 8.33 GB 全常驻零 offload |
| **2K 级超分 ★** | PixelDiT `pid_flux2` | **5.4 s** 1024²→2048² | 替代了 HV1.5 跑不动的路径 |
| 任意图 4× 放大 | SeedVR2 3B int8 | 23.6 s 768²→3072² | 1 步扩散修复 |
| **视频（旗舰画质）** | Wan 2.2 14B MoE + 4步 LoRA | **93.8 s** | 20 步要 739 s → 7.9× |
| 视频（最轻） | Kandinsky 5 T2V Lite | 884.5 s | 仅 4.57 GB，最轻但慢 |
| **视频 + 音频** | MiniMax H3 + 4步 LoRA | **286.2 s** | 原生立体声；⚠ 排除 US/EU/UK/KR |
| **音乐** | ACE-Step 1.5 XL turbo | **20.8 s** | Apache 2.0 可商用 |
| 图像编辑 | FLUX.2 Klein 4B fp8 | 42.3 s | **9B 是禁商用，4B 是 Apache 2.0** |
| **图生 3D** | Hunyuan3D 2.1 | **54.7 s** | ⚠ ≤100万月活、排除 EU/UK/KR、须标注 |
| **量化** | **NVFP4** | 快 22%、小 27% | 画质差异在噪声地板下；**22% 是下界**（cu130 内核被禁） |

**明确的反面教材**：LTX-Video 2B 蒸馏最快（19.2 s）但在 CFG=1/8 步下**完全不跟随提示词**。

---

## 5. 关键技术决策与理由

| 决策 | 理由 |
|---|---|
| **单一仓库**而非每模型一仓 | 四条线复用同一套方法论（受控 A/B / 下载器 / 校验器 / 权威计时）；拆仓会让方法论复制 N 份、改一处不同步 → 结论不可比（附录 D） |
| **仓库名含 `minimax-h3-wan2.2-nvfp4`** | GitHub 搜索实测：`wan2.2` in:name 1084 个仓库、`minimax-h3` 778、`qwen-image` 701 —— 模型名是硬权重 |
| **`wan2.2` 带点不写 `wan22`** | 实测 `wan2.2` 1084 个 vs `wan22` 213 个，差 5 倍；搜「wan 2.2」命中的全是带点写法 |
| **模型库用 junction 单一副本** | 多个 ComfyUI 目录类别指向同一物理文件，零额外占用 |
| **手册中英各一份 MD（非翻译）** | `index.html` 由 `tools/build_site.py` 渲染，按 `navigator.language` 自动切换 |
| **图表按语言拆 SVG 文件** | `<img>` 无法按语言切换内容 |

---

## 6. 踩坑清单（全项目累计，按主题归组）

### 6.1 Windows 平台
1. **判同一物理文件必须用 `GetFileInformationByHandle` 的 `nFileIndex`**，`os.stat().st_ino` 不可靠
   —— 踩了**两次**：19.6 GB 误算 58.7 GB；515.6 GB 误算 852 GB（超过整盘容量）
2. **`os.path.realpath` 不解析 junction** → 统计磁盘占用会重复计数，必须用文件身份
3. `SHFileOperationW` 送回收站：`pFrom` 要**双 `\0` 结尾的 wchar 缓冲**、字段声明 `c_void_p`；
   且 **rc 不可信**（成功也返回 2）→ 判定只能看文件是否还在
4. **回收站是同盘移动，不释放空间**
5. **删完模型必须停掉 ComfyUI 才真正释放空间**（句柄持有 → delete-pending）

### 6.2 网络 / 下载
6. **下载器必须有最终大小校验** —— 只打印进度会接受 4.36 GB 截断的"OK"
7. **换源前必须重算偏移**，且校验响应 `Content-Range` 起点 == 请求偏移（否则追加写出超长坏文件）
8. **modelscope 不支持 HEAD 但支持 Range**；**单连接约 4.36 GB 会断**，必须续传
9. **源速度实测**：modelscope 11–30 MB/s ≫ hf-mirror 2–4（会静默降速到 0）≈ huggingface 1.6–2.2
10. **判源可用性要避开下载高峰**（带宽饱和时并发探测全超时 → 误判"两源均不可用"，导致 LTX-2.3/Klein 9B 两次误判）
11. **github.com 被墙**，但 `codeload.github.com` 和 `api.github.com` 可达 → 升级走 tarball

### 6.3 ComfyUI
12. **升级 Python 包后必须重启 ComfyUI**（旧模块在内存里 → SeedVR2 崩溃）
13. **删模型必须先停 ComfyUI**（见 §6.1.5）
14. **ComfyUI 会缓存模型不释放**：跑完图像 vram_free 只剩 3.7 GB → 串跑视频前重启
15. **`CLIPLoader` 的 type 列表不全**：HunyuanVideo 1.5 要用 `DualCLIPLoader(type=hunyuan_video_15)`
16. **官方模板是 subgraph 格式**，不能直接当 API prompt 提交；写了 `ui2api.py` 转换器（**8 个坑**：
    `control_after_generate` 伪 widget / widget-link 两条规则 / v3 点号命名空间 / 子图边界按 linkIds 接回 /
    required 在前 optional 在后 / `ComfyMathExpression` 的 `values.*` / 未知节点穿透 / `PrimitiveNode` 内联）
17. **判 Manager 装没装**：打 `/api/manager/version`（Manager V3 不注册成图节点）
18. **模型没下完时 `POST /prompt` 返回 400 + node_errors** → 可当免费 dry-run
19. ComfyUI **会动态重扫模型目录**，新增文件不必重启

### 6.4 工作流改造
20. **模板里两个 `CLIPTextEncode` 分正/负向**，别按"空的就是要填的"判断（Kandinsky 教训）
21. **连线要解析两层**：KSampler 的 positive/negative 可能指向中间节点（如 `Kandinsky5ImageToVideo`），
    真正的 CLIPTextEncode 在下一层
22. **转换器可能接错 SaveImage**（Kandinsky 的 SaveImage 被接到 CLIPTextEncode 而非 VAEDecode）
23. **模板里的文件名与实际不一致是常态**（`t5xxl_fp8_e4m3fn_scaled` vs 实际无 `_scaled`）
24. **预览节点（ImageCompare / JoinImageWithAlpha）单图流程用不到**，要删
25. **Wan 2.2 的 5B 与 14B 线用的不是同一个 VAE**（48 vs 16 通道）

### 6.5 PixelDiT（通道数是核心约束）
26. `pid_flux2_*` 期望 **128 通道**（FLUX.2 潜空间）→ 源图用 **`flux2-vae`** 编码
27. `pid_flux1_*` / `pid_sd3_*` 期望 **16 通道** → 与 flux2 版**不可混用**
28. 采样**输出**是 128 通道，解码**必须用内置 `pixel_space` VAE**
29. 手写图容易漏掉 `VAELoader(pixel_space)` 节点

### 6.6 工具链 / 仓库
30. **`hash-object` 必须喂绝对路径**（相对路径按 CWD 解析会找不到文件）
31. **跨行字符串替换必须写成脚本文件再执行**（bash heredoc 里 `\\` 会被转义，匹配串变形 → 静默失败）
32. **改 Python 数据块别用 `s.find(']},\n')` 做边界** —— 两次切错位置把脚本写坏
33. **`__pycache__/*.pyc` 曾被推上远端** → push_site.py 的 SKIP 已补
34. **fine-grained PAT 建不了仓库** → 用 gh CLI keyring 的经典 OAuth token
35. **Node 无法 spawn 子进程**（EBUSY -4082）而 Python 可以 → `push-site.mjs` 已移植为 `push_site.py`
36. **ComfyUI 后台启动必须用 Bash 工具的 `run_in_background: true`**，`nohup &` 活不过调用结束
37. **照片/渲染图进仓库先转 JPEG**（PNG 11.64 MB → JPEG 1.50 MB，8×）

### 6.7 方法论
38. **扩散模型量化对比不能用 PSNR 直接下结论** —— 必须固定编码器/提示词/种子，
    并同时测「同量化换种子」作噪声基线；只有 cross-quant 差异 < seed 差异才能证明量化可忽略
39. **「跑得快」≠「能用」**（LTX 案例：快 18× 但提示词不跟随）
40. **下结论前先查 Comfy-Org 的 repackage 仓库**（两次误判同源）
41. **测量要读工具自己的计时**（服务端 `execution_start→execution_success`），不要用 API 往返推算
42. **改完图表必须截图看**（`header()` 多个首参导致标题被吞，grep 文本查不出渲染级 bug）

---

## 7. 当前覆盖度（27 组实测，全部出片）

| 领域 | 数量 | 明细 |
|---|---|---|
| **图像** | 13 | PixelDiT 1.3B / Qwen-Image 2512(+Lightning) / Qwen-Image 2.1 / Z-Image-Turbo(nvfp4+int8) / FLUX.2 Klein 4B / FLUX.2 Klein 9B / Lens turbo / ERNIE-Image turbo / Chroma1-HD / Kandinsky 5 Lite / SDXL / FLUX.1-dev |
| **视频** | 6 | Wan 2.2 14B MoE(4步/20步) / Wan 2.2 5B / LTX-Video 2B / HunyuanVideo 1.5 480p / MiniMax H3(4步/8步) / Kandinsky 5 T2V Lite |
| **音乐** | 5 | ACE-Step 1.5(XL/turbo) / YuE2-3B / MiniMax Music 3 / Stable Audio 3 Medium |
| **3D** | 1 | Hunyuan3D 2.1 |
| **放大修复** | 2 | PixelDiT pid_flux2 / SeedVR2 3B int8 |

### 明确不做 / 做不了的（每个都有确切理由）

| 项 | 理由 |
|---|---|
| FLUX.3 / MiniMax H3 Max | **API-only，无本地权重** |
| LTX-2.5 | **gated（403）**，两次核实都是 |
| MiniMax Music 3（权重源） | 原仓库 gated；**授权信源冲突**（CC BY-NC vs Community） |
| Bernini-R / SCAIL-2 / HiDream E1.1 | **31.1 / 32.8 / 34.2 GB**，24 GB 装不下 |
| FLUX.2 Klein 9B / FLUX.1-dev / YuE2 | **禁商用**（权重在，但不进商用推荐位） |
| HunyuanVideo 1.5 720p→1080p | 两步串行路径 70 分钟未完成（**已被 PixelDiT 替代**） |
| LTX-2.3 GGUF | attempted：hf-mirror API 403 + 需 custom node + 编码器未知 |
| MiniMax H3 Max / FLUX.3 | API-only |

---

## 8. 文件地图（接手时去哪找什么）

```
comfyui-5090-laptop-playbook/
├── README.md / README_EN.md     ← 手册本体（中英，单一内容真相源）
├── index.html                   ← build_site.py 生成，勿手改
├── HISTORY.md                   ← 本文档
├── assets/{zh,en}/              ← 10 张图表 × 2 语言（SVG）
├── assets/shots/                ← 14 张实拍产物图（JPEG）
├── data/                        ← 7 份原始实测数据（round1–4 + 授权 + 对比）
├── docs/                        ← 受控 A/B 方法论深挖（双语）
├── scripts/                     ← dl_fixed.py（下载器）/ verify_new.py / run_batch.py …
├── tools/                       ← build_site.py / make_charts.py / make_recommend_charts.py
└── workflows/                   ← 39 个 API 格式工作流（含 _meta 说明）
```

**ComfyUI 侧**：`D:\aigc\` 有全套工具（`run_batch.py` / `verify_new.py` / `probe_speed.py` 等），
`D:\aigc\workflows\` 是工作流的另一份副本。

---

## 9. 下一步候选（按价值排序）

1. **解决 cu130**：装 PyTorch cu130 → comfy_kitchen CUDA 后端启用 → NVFP4 的 22% 从下界变成真实值
   （这是当前**唯一**卡住所有性能数字天花板的事）
2. **PixelDiT 潜空间超分的系统性测试**：4 个变体（flux1/sd3）× 2 个目标分辨率，做成标准化放大管线
3. **Qwen-Image 2.1 等 Lightning LoRA**（出了就把 72.7 s 压到 ~12 s）
4. **MiniMax Music 3 授权定案**（读原始仓库 LICENSE，当前信源冲突）
5. **Lens 授权核实**（Comfy-Org repackage，原始厂商不明）
6. 视频侧：**LTX-2.5 若解除 gated**（带音频 VAE + latent upscaler，是唯一原生同步音视频的开源线）

---

## 10. 给接手 AI 的三条最重要的提醒

1. **验身份看 header，不看文件名**；**统计磁盘用 Windows 文件身份**，不用 `realpath`
2. **所有数字必须来自服务端权威计时**，且要注明测量时的 ComfyUI 版本（0.37 和 0.38 数字不同）
3. **结论要可推翻**：本项目两次推翻自己的结论（LTX-2.3"不可行"、HV1.5 1080p"不可行"），
   两次都是因为**先查 Comfy-Org repackage / 换个实现路径**。写负面结论时注明"以当前实现为准"。
