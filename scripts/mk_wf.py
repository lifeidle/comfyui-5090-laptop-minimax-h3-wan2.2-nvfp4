# -*- coding: utf-8 -*-
"""mk_wf.py — 用 ui2api 转换官方模板，并派生本项目要跑的变体工作流。

用法: python mk_wf.py <variant...>
    variant: wan_smoke | wan_full | ltx_smoke | ltx_full | hv15_720 | hy3d
"""
import json, os, sys, subprocess

OUT = r"D:\aigc\workflows"
PY = r"D:\aigc\venv\Scripts\python.exe"
UI2API = r"D:\aigc\ui2api.py"

WAN_POS = "特写镜头，一只蜂鸟悬停在红色花丛前采蜜，翅膀高速振动，阳光透过花瓣，背景虚化，镜头缓慢横移"

LTX_POS = "A steaming cup of jasmine tea on a bamboo tray by a rain-streaked window, soft morning light, slow push-in, cinematic"
LTX_NEG = "worst quality, inconsistent motion, blurry, jittery, distorted"

HV_POS = "陶艺工作室里，双手在旋转的陶轮上把陶土拉坯成花瓶，左侧暖黄色轮廓光，背景虚化木架上摆满素坯，镜头缓慢推近"
HV_NEG = "低质量，模糊，抖动，畸变，静止不动，字幕，水印"


def convert(template):
    """注意：ui2api 无 -o 时会把输出截断到 4000 字符，大图会解析失败 —— 必须走临时文件。"""
    tmp = os.path.join(os.environ.get("TEMP", r"C:\Users\chenhua\AppData\Local\Temp"),
                       "_mk_wf_conv.json")
    r = subprocess.run([PY, UI2API, template, "-o", tmp],
                       capture_output=True, text=True, encoding="utf-8")
    if not os.path.exists(tmp):
        raise RuntimeError("convert failed: " + (r.stdout or "")[:800] + (r.stderr or "")[:800])
    with open(tmp, encoding="utf-8") as f:
        return json.load(f)


def write(name, prompt):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(prompt, f, ensure_ascii=False, indent=1)
    print("wrote", p, f"({len(prompt)} nodes)")


def by_type(p, t):
    return [k for k, v in p.items() if v["class_type"] == t]


# ---------------------------------------------------------------- Wan 2.2 5B
def wan_variant(w, h, length, steps, seed, name, prompt_text=WAN_POS, drop_image=True):
    p = convert("video_wan2_2_5B_ti2v.json")
    # 纯文生视频：去掉 start_image（optional）与其来源 LoadImage
    for k in by_type(p, "Wan22ImageToVideoLatent"):
        p[k]["inputs"]["width"] = w
        p[k]["inputs"]["height"] = h
        p[k]["inputs"]["length"] = length
        if drop_image:
            p[k]["inputs"].pop("start_image", None)
    if drop_image:
        for k in by_type(p, "LoadImage"):
            p.pop(k)
    for k in by_type(p, "KSampler"):
        p[k]["inputs"]["steps"] = steps
        p[k]["inputs"]["seed"] = seed
    # 正向提示词 = 最长的那条中文/英文文本
    texts = [k for k in by_type(p, "CLIPTextEncode")]
    # 模板里 node 6 = 正向，node 7 = 负向；按 text 长度区分不可靠，改用固定 id 优先
    if "6" in p and p["6"]["class_type"] == "CLIPTextEncode":
        p["6"]["inputs"]["text"] = prompt_text
    else:
        texts.sort(key=lambda k: len(str(p[k]["inputs"].get("text", ""))))
        p[texts[-1]]["inputs"]["text"] = prompt_text
    for k in by_type(p, "SaveVideo"):
        p[k]["inputs"]["filename_prefix"] = name.replace(".json", "")
    return p


# ---------------------------------------------------------------- LTX-Video 2B
def ltx_variant(w, h, length, steps, cfg, seed, name, pos=LTX_POS, neg=LTX_NEG):
    p = convert("ltxv_text_to_video.json")
    # 指向本机实际的权重要（模板给的是 t5xxl_fp16 / ltx-video-2b-v0.9，我们都没有）
    for k in by_type(p, "CLIPLoader"):
        p[k]["inputs"]["clip_name"] = "t5xxl_fp8_e4m3fn.safetensors"
        p[k]["inputs"]["type"] = "ltxv"
    for k in by_type(p, "CheckpointLoaderSimple"):
        p[k]["inputs"]["ckpt_name"] = "ltxv-2b-0.9.8-distilled-fp8.safetensors"
    for k in by_type(p, "EmptyLTXVLatentVideo"):
        p[k]["inputs"].update({"width": w, "height": h, "length": length, "batch_size": 1})
    for k in by_type(p, "LTXVScheduler"):
        p[k]["inputs"]["steps"] = steps
    for k in by_type(p, "SamplerCustom"):
        p[k]["inputs"]["noise_seed"] = seed
        p[k]["inputs"]["cfg"] = cfg          # 蒸馏版走 CFG-free，cfg=1
    for k in by_type(p, "RandomNoise"):
        p[k]["inputs"]["noise_seed"] = seed
    # 模板里 node 6 = 正向，7 = 负向
    if "6" in p and p["6"]["class_type"] == "CLIPTextEncode":
        p["6"]["inputs"]["text"] = pos
    if "7" in p and p["7"]["class_type"] == "CLIPTextEncode":
        p["7"]["inputs"]["text"] = neg
    for k in by_type(p, "SaveVideo"):
        p[k]["inputs"]["filename_prefix"] = name.replace(".json", "")
    return p


# ---------------------------------------------------------------- HV1.5 720p→1080p
def hv15_720(seed, name, pos=HV_POS, neg=HV_NEG, base_steps=20):
    p = convert("video_hunyuan_video_1.5_720p_t2v.json")
    for k in by_type(p, "RandomNoise"):
        p[k]["inputs"]["noise_seed"] = seed
    for k in by_type(p, "BasicScheduler"):
        if p[k]["inputs"].get("steps") == 20:      # 只改基座那一档，SR 保持 8 步
            p[k]["inputs"]["steps"] = base_steps
    # 44 = 正向，93 = 负向（模板负向是空串）
    if "44" in p and p["44"]["class_type"] == "CLIPTextEncode":
        p["44"]["inputs"]["text"] = pos
    if "93" in p and p["93"]["class_type"] == "CLIPTextEncode":
        p["93"]["inputs"]["text"] = neg
    # 两个 SaveVideo：按 codec 区分（h264 = 720p 基座，auto = 1080p SR 分支）
    svs = by_type(p, "SaveVideo")
    for k in svs:
        p[k]["inputs"]["filename_prefix"] = name.replace(".json", "")
    for k in svs:
        if p[k]["inputs"].get("codec") == "h264":
            p[k]["inputs"]["filename_prefix"] = name.replace(".json", "") + "_720p"
        else:
            p[k]["inputs"]["filename_prefix"] = name.replace(".json", "") + "_1080p_sr"
    return p


# ---------------------------------------------------------------- Hunyuan3D 2.1
def hy3d(image_name, seed, name, steps=30):
    p = convert("3d_hunyuan3d-v2.1.json")
    for k in by_type(p, "ImageOnlyCheckpointLoader"):
        p[k]["inputs"]["ckpt_name"] = "hunyuan_3d_v2.1.safetensors"
    for k in by_type(p, "LoadImage"):
        p[k]["inputs"]["image"] = image_name
    for k in by_type(p, "KSampler"):
        p[k]["inputs"]["seed"] = seed
        p[k]["inputs"]["steps"] = steps
    for k in by_type(p, "SaveGLB"):
        p[k]["inputs"]["filename_prefix"] = name.replace(".json", "")
    return p


# ---------------------------------------------------------------- Wan 2.2 14B MoE
def wan14b(w, h, seconds, name, seed=20260922, pos=WAN_POS, use_lora=True, fps=16):
    p = convert("video_wan2_2_14B_t2v.json")
    # ⚠️ Wan 2.2 的 14B 线用的是 wan_2.1_vae（16 通道），
    # 与 5B 线用的 wan2.2_vae 不是同一个 VAE —— 混用会在 VAEDecode 报
    # "expected input to have 48 channels, but got 16 channels"。
    for k in by_type(p, "VAELoader"):
        p[k]["inputs"]["vae_name"] = "wan_2.1_vae.safetensors"
    # ComfySwitchNode 由同一个 PrimitiveBoolean 驱动：true = 走 LightX2V 4step LoRA + 4步 + cfg1
    for k in by_type(p, "PrimitiveBoolean"):
        p[k]["inputs"]["value"] = bool(use_lora)
    # 总帧数 = floor(seconds * fps) + 1（模板用 ComfyMathExpression 算 length）
    for k in by_type(p, "PrimitiveFloat"):
        v = p[k]["inputs"].get("value")
        if v == 16:
            p[k]["inputs"]["value"] = float(fps)
    nf = int(seconds * fps) + 1
    for k in by_type(p, "ComfyMathExpression"):
        # 不要把 values.a / values.b 删掉 —— ComfyMathExpression 的 values.* 是必填输入，
        # 删了会在提交时被判 required_input_missing: values.a。
        # 正解：把表达式简化成单个变量，并把帧数喂给它。
        p[k]["inputs"]["expression"] = "a"
        p[k]["inputs"]["values.a"] = nf
        p[k]["inputs"].pop("values.b", None)
    for k in by_type(p, "EmptyHunyuanLatentVideo"):
        p[k]["inputs"]["width"] = w
        p[k]["inputs"]["height"] = h
    for k in by_type(p, "KSamplerAdvanced"):
        if p[k]["inputs"].get("add_noise") == "enable":
            p[k]["inputs"]["noise_seed"] = seed
    for k in by_type(p, "CreateVideo"):
        p[k]["inputs"]["fps"] = float(fps)
    for k in by_type(p, "PrimitiveInt"):
        if p[k]["inputs"].get("value") == 20:
            p[k]["inputs"]["value"] = 20           # 非 LoRA 分支的步数，保留
    ce = by_type(p, "CLIPTextEncode")
    if "1136" in p:
        p["1136"]["inputs"]["text"] = pos
    for k in by_type(p, "SaveVideo"):
        p[k]["inputs"]["filename_prefix"] = name.replace(".json", "")
    return p


if __name__ == "__main__":
    for v in sys.argv[1:]:
        if v == "wan_smoke":
            write("wan22_5b_t2v_smoke.json", wan_variant(704, 384, 49, 20, 20260922, "wan22_5b_t2v_smoke"))
        elif v == "wan_full":
            write("wan22_5b_t2v_full.json", wan_variant(1280, 704, 121, 20, 20260922, "wan22_5b_t2v_full"))
        elif v == "ltx_smoke":
            write("ltx2b_t2v_smoke.json", ltx_variant(768, 512, 97, 8, 1, 20260922, "ltx2b_t2v_smoke"))
        elif v == "ltx_full":
            write("ltx2b_t2v_full.json", ltx_variant(1216, 704, 121, 8, 1, 20260922, "ltx2b_t2v_full"))
        elif v == "hv15_720":
            write("hv15_t2v_720p.json", hv15_720(20260922, "hv15_t2v_720p"))
        elif v == "hy3d":
            write("hunyuan3d_v21_teapot.json",
                  hy3d("h3d_teapot_input.png", 20260922, "hunyuan3d_v21_teapot"))
        elif v == "wan14b_4step":
            write("wan22_14b_t2v_4step.json",
                  wan14b(832, 480, 5, "wan22_14b_t2v_4step", use_lora=True))
        elif v == "wan14b_20step":
            write("wan22_14b_t2v_20step.json",
                  wan14b(832, 480, 5, "wan22_14b_t2v_20step", use_lora=False))
        else:
            print("unknown variant:", v)
