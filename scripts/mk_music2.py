# -*- coding: utf-8 -*-
"""mk_music2.py — YuE2 与 MiniMax Music 3 工作流。

用法: python mk_music2.py yue2 | mm3
"""
import json, os, sys, subprocess

OUT = r"D:\aigc\workflows"
PY = r"D:\aigc\venv\Scripts\python.exe"
UI2API = r"D:\aigc\ui2api.py"

STYLE = ("Chinese folk pop, guzheng and bamboo flute, warm female vocal, "
         "mid tempo, gentle and lyrical, clean studio mix")
LYRICS = """[Verse]
春风吹过山岗
桃花开满了村庄
溪水绕过青石旁
谁在轻轻把歌唱
[Chorus]
一路向前走啊
把歌儿唱到天亮
不管山高水又长
心里有光就不慌"""

CAPTION = ("Chinese folk pop song, warm female vocal, guzheng and bamboo flute, "
           "mid tempo, gentle and lyrical")


def convert(t):
    tmp = os.path.join(os.environ.get("TEMP", r"C:\Users\chenhua\AppData\Local\Temp"), "_m2.json")
    r = subprocess.run([PY, UI2API, t, "-o", tmp], capture_output=True, text=True, encoding="utf-8")
    if not os.path.exists(tmp):
        raise RuntimeError((r.stdout or "")[:600] + (r.stderr or "")[:600])
    p = json.load(open(tmp, encoding="utf-8")); os.remove(tmp)
    return p


def by_type(p, t):
    return [k for k, v in p.items() if v["class_type"] == t]


def write(name, p):
    os.makedirs(OUT, exist_ok=True)
    fp = os.path.join(OUT, name)
    json.dump(p, open(fp, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    print("wrote", fp, f"({len(p)} nodes)")


def yue2(name, seconds=60, seed=20260922, steps=32):
    p = convert("audio_yue2_text2music.json")
    for k in by_type(p, "CheckpointLoaderSimple"):
        p[k]["inputs"]["ckpt_name"] = "yue2_3b_int8_convrot.safetensors"
    # PrimitiveStringMultiline / PrimitiveString 承载 style 与 lyrics —— 直接覆盖字面量
    for k in by_type(p, "YuE2GenerateABC"):
        p[k]["inputs"]["style"] = STYLE
        p[k]["inputs"]["lyrics"] = LYRICS
        p[k]["inputs"]["mode"] = "full"
        p[k]["inputs"]["seed"] = seed
    for k in by_type(p, "YuE2GenerateMusic"):
        p[k]["inputs"]["style"] = STYLE
        p[k]["inputs"]["lyrics"] = LYRICS
        p[k]["inputs"]["mode"] = "full"
        p[k]["inputs"]["seed"] = seed
        p[k]["inputs"]["max_duration"] = int(seconds)
    for k in by_type(p, "EmptyYuE2LatentAudio"):
        p[k]["inputs"]["seconds"] = float(seconds)
    for k in by_type(p, "KSampler"):
        p[k]["inputs"]["steps"] = steps
        p[k]["inputs"]["seed"] = seed
    for k in by_type(p, "SeedNode"):
        p[k]["inputs"]["seed"] = seed
    for k in by_type(p, "SaveAudioAdvanced"):
        p[k]["inputs"]["filename_prefix"] = name.replace(".json", "")
    return p


def mm3(name, seconds=60, seed=20260922, steps=30):
    p = convert("audio_minimax_music_3.json")
    for k in by_type(p, "UNETLoader"):
        p[k]["inputs"]["unet_name"] = "minimax_music3_dit_int8_convrot.safetensors"
    for k in by_type(p, "CLIPLoader"):
        p[k]["inputs"]["clip_name"] = "minimax_music3_text_encoder_pruned_int8_convrot.safetensors"
        p[k]["inputs"]["type"] = "minimax"
    for k in by_type(p, "VAELoader"):
        p[k]["inputs"]["vae_name"] = "minimax_music3_dav.safetensors"
    for k in by_type(p, "MiniMaxMusic3TextEncode"):
        p[k]["inputs"]["caption"] = CAPTION
        p[k]["inputs"]["lyrics"] = LYRICS
        p[k]["inputs"]["seed"] = seed
        p[k]["inputs"]["max_duration"] = float(seconds)
    for k in by_type(p, "EmptyMiniMaxMusic3LatentAudio"):
        p[k]["inputs"]["seconds"] = float(seconds)
    for k in by_type(p, "KSampler"):
        p[k]["inputs"]["steps"] = steps
        p[k]["inputs"]["seed"] = seed
    for k in by_type(p, "SeedNode"):
        p[k]["inputs"]["seed"] = seed
    for k in by_type(p, "SaveAudioAdvanced"):
        p[k]["inputs"]["filename_prefix"] = name.replace(".json", "")
    return p


if __name__ == "__main__":
    for v in sys.argv[1:]:
        if v == "yue2":
            write("yue2_text2music.json", yue2("yue2_text2music", 60))
        elif v == "mm3":
            write("minimax_music3_song.json", mm3("minimax_music3_song", 60))
        else:
            print("unknown:", v)
