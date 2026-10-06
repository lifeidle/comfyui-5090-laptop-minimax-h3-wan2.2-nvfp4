# -*- coding: utf-8 -*-
"""dl_round6.py — PixelDiT + Kandinsky 5 T2V + Chroma1-HD（远端路径 / 本地路径分开）。"""
import json
import os
import struct
import threading
import time
import urllib.request

OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
ROOT = r"D:\models\comfyui-models"
ITEMS = [
    ("Comfy-Org/PixelDiT", "diffusion_models/pid_flux2_1024_to_4096_4step_bf16.safetensors",
     "diffusion_models/pid_flux2_1024_to_4096_4step_bf16.safetensors"),
    ("Comfy-Org/PixelDiT", "diffusion_models/pid_flux2_512_to_2048_4step_bf16.safetensors",
     "diffusion_models/pid_flux2_512_to_2048_4step_bf16.safetensors"),
    ("Comfy-Org/PixelDiT", "text_encoders/gemma_2_2b_it_elm_fp8_scaled.safetensors",
     "text_encoders/gemma_2_2b_it_elm_fp8_scaled.safetensors"),
    ("kandinskylab/Kandinsky-5.0-T2V-Lite-sft-5s", "model/kandinsky5lite_t2v_sft_5s.safetensors",
     "diffusion_models/kandinsky5lite_t2v_sft_5s.safetensors"),
    ("Comfy-Org/Chroma1-HD_repackaged", "split_files/diffusion_models/Chroma1-HD-fp8mixed.safetensors",
     "diffusion_models/Chroma1-HD-fp8mixed.safetensors"),
]
BASES = ["https://www.modelscope.cn/models/{}/resolve/master/",
         "https://hf-mirror.com/{}/resolve/main/"]


def total(repo, p):
    for bf in BASES:
        try:
            r = OP.open(urllib.request.Request(bf.format(repo) + p,
                                               headers={"Range": "bytes=0-0", "User-Agent": "dl"}), timeout=25)
            cr = r.headers.get("Content-Range") or ""
            if "/" in cr:
                return int(cr.split("/")[-1])
        except Exception:
            pass
    return -1


def fetch(repo, remote, local, tries=60):
    dst = os.path.join(ROOT, local.replace("/", os.sep))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    part = dst + ".part"
    exp = total(repo, remote)
    if exp <= 0:
        print(f"  取不到大小 {remote}", flush=True)
        return
    for _ in range(tries):
        if os.path.exists(dst) and os.path.getsize(dst) == exp:
            break
        have = os.path.getsize(part) if os.path.exists(part) else 0
        if have > exp:
            os.remove(part); have = 0
        if have == exp:
            os.replace(part, dst); break
        for bf in BASES:                      # ★ 换源前重算偏移
            have = os.path.getsize(part) if os.path.exists(part) else 0
            if have >= exp:
                break
            try:
                h = {"User-Agent": "dl"}
                if have:
                    h["Range"] = f"bytes={have}-"
                r = OP.open(urllib.request.Request(bf.format(repo) + remote, headers=h), timeout=60)
                cr = r.headers.get("Content-Range") or ""
                if have and not cr.startswith(f"bytes {have}-"):
                    print(f"    源未按偏移返回（{cr[:30]}），跳过", flush=True); r.close(); continue
                t0 = time.time(); got = have; last = have; lastT = time.time()
                with r, open(part, "ab" if have else "wb") as f:
                    while True:
                        c = r.read(1 << 22)
                        if not c:
                            break
                        f.write(c); got += len(c)
                        if got - last > (1 << 28):
                            last = got
                            print(f"    {os.path.basename(dst)} {got/1e9:.2f}/{exp/1e9:.2f} GB "
                                  f"{got/max(time.time()-t0,1)/1e6:.1f} MB/s", flush=True)
                        if time.time() - lastT > 90:
                            break
            except Exception as e:
                print(f"    断开 {os.path.basename(dst)}: {str(e)[:46]}", flush=True); time.sleep(2)
    final = os.path.getsize(dst) if os.path.exists(dst) else 0
    if final == exp:
        with open(dst, "rb") as f:
            hl = struct.unpack("<Q", f.read(8))[0]
            hdr = json.loads(f.read(min(hl, 4_000_000)))
        mx = max((v.get("data_offsets", [0, 0])[1] for v in hdr.values() if isinstance(v, dict)), default=0)
        print(f"  OK {os.path.basename(dst)} {final/1e9:.2f} GB  张量 {len(hdr)}  最大偏移 {mx/1e9:.2f} GB", flush=True)
    else:
        print(f"  FAIL {os.path.basename(dst)} {final/1e9:.2f}/{exp/1e9:.2f} GB", flush=True)


if __name__ == "__main__":
    ts = [threading.Thread(target=fetch, args=it, daemon=True) for it in ITEMS]
    [t.start() for t in ts]
    [t.join() for t in ts]
    print("下载结束")
