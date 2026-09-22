# -*- coding: utf-8 -*-
"""mk_music.py — 生成音乐生成工作流（ACE-Step 1.5 家族）。

用法: python mk_music.py ace_turbo | ace_xl | yue2 | mm3
"""
import json, os, sys, subprocess

OUT = r"D:\aigc\workflows"
PY = r"D:\aigc\venv\Scripts\python.exe"
UI2API = r"D:\aigc\ui2api.py"

# 可逐字核对的中文歌词 —— 便于听感/字幕复核
LYRICS = """[verse]
春风吹过山岗
桃花开满了村庄
溪水绕过青石旁
谁在轻轻把歌唱
[chorus]
一路向前走啊
把歌儿唱到天亮
不管山高水又长
心里有光就不慌"""

TAGS = ("Chinese folk pop, guzheng and bamboo flute, warm female vocal, "
        "mid tempo, gentle and lyrical, clean mix, studio quality")


def convert(template):
    tmp = os.path.join(os.environ.get("TEMP", r"C:\Users\chenhua\AppData\Local\Temp"), "_m.json")
    r = subprocess.run([PY, UI2API, template, "-o", tmp],
                       capture_output=True, text=True, encoding="utf-8")
    if not os.path.exists(tmp):
        raise RuntimeError((r.stdout or "")[:600] + (r.stderr or "")[:600])
    p = json.load(open(tmp, encoding="utf-8"))
    os.remove(tmp)
    return p


def by_type(p, t):
    return [k for k, v in p.items() if v["class_type"] == t]


def write(name, p):
    os.makedirs(OUT, exist_ok=True)
    fp = os.path.join(OUT, name)
    json.dump(p, open(fp, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    print("wrote", fp, f"({len(p)} nodes)")


def ace(name, template, duration, seed, bpm=90, steps=8, tags=TAGS, lyrics=LYRICS):
    p = convert(template)
    for k in by_type(p, "TextEncodeAceStepAudio1.5"):
        p[k]["inputs"]["tags"] = tags
        p[k]["inputs"]["lyrics"] = lyrics
        p[k]["inputs"]["language"] = "zh"
        p[k]["inputs"]["bpm"] = bpm
        p[k]["inputs"]["duration"] = float(duration)
        p[k]["inputs"]["seed"] = seed
    for k in by_type(p, "EmptyAceStep1.5LatentAudio"):
        p[k]["inputs"]["seconds"] = float(duration)
    for k in by_type(p, "PrimitiveInt"):
        p[k]["inputs"]["value"] = seed
    for k in by_type(p, "KSampler"):
        if not isinstance(p[k]["inputs"].get("seed"), list):
            p[k]["inputs"]["seed"] = seed
        p[k]["inputs"]["steps"] = steps
    for k in by_type(p, "SaveAudioAdvanced") + by_type(p, "SaveAudioMP3"):
        p[k]["inputs"]["filename_prefix"] = name.replace(".json", "")
    return p


if __name__ == "__main__":
    for v in sys.argv[1:]:
        if v == "ace_xl":
            write("ace15_xl_turbo_song.json",
                  ace("ace15_xl_turbo_song.json", "audio_ace_step1_5_xl_turbo.json", 60, 20260922))
        elif v == "ace_turbo":
            write("ace15_turbo_song.json",
                  ace("ace15_turbo_song.json", "audio_ace_step_1_5_split.json", 60, 20260922))
        else:
            print("unknown:", v)
