# -*- coding: utf-8 -*-
"""dl_k5_svr2.py — 下载 Kandinsky 5 Lite + SeedVR2 3B（多仓库、可续传、强校验）。

要点（都是踩过的坑）：
  ① 每次换源前重算偏移，否则第二个源会按旧偏移追加，写出超长坏文件
  ② 校验响应 Content-Range 起点 == 请求偏移
  ③ 最终校验字节数 + safetensors header
"""
import json
import os
import struct
import threading
import time
import urllib.request

OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
ROOT = r"D:\models\comfyui-models"
ITEMS = [
    ("kandinskylab/Kandinsky-5.0-T2I-Lite", "model/kandinsky5lite_t2i.safetensors", "diffusion_models/kandinsky5lite_t2i.safetensors"),
    ("Comfy-Org/SeedVR2", "diffusion_models/seedvr2_3b_int8_convrot.safetensors", "diffusion_models/seedvr2_3b_int8_convrot.safetensors"),
    ("Comfy-Org/SeedVR2", "vae/seedvr2_ema_vae_fp16.safetensors", "vae/seedvr2_ema_vae_fp16.safetensors"),
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
    p = remote
    dst = os.path.join(ROOT, local.replace("/", os.sep))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    part = dst + ".part"
    exp = total(repo, p)
    if exp <= 0:
        print(f"  取不到大小 {p}", flush=True)
        return
    for _ in range(tries):
        if os.path.exists(dst) and os.path.getsize(dst) == exp:
            break
        have = os.path.getsize(part) if os.path.exists(part) else 0
        if have > exp:                      # 已写坏 → 丢弃重来
            os.remove(part)
            have = 0
        if have == exp:
            os.replace(part, dst)
            break
        for bf in BASES:                    # ★ 换源前重算偏移
            have = os.path.getsize(part) if os.path.exists(part) else 0
            if have >= exp:
                break
            url = bf.format(repo) + p
            try:
                h = {"User-Agent": "dl"}
                if have:
                    h["Range"] = f"bytes={have}-"
                r = OP.open(urllib.request.Request(url, headers=h), timeout=60)
                cr = r.headers.get("Content-Range") or ""
                if have and not cr.startswith(f"bytes {have}-"):
                    print(f"    源未按偏移返回（{cr[:30]}），跳过", flush=True)
                    r.close()
                    continue
                t0 = time.time()
                got = have
                last = have
                lastT = time.time()
                with r, open(part, "ab" if have else "wb") as f:
                    while True:
                        c = r.read(1 << 22)
                        if not c:
                            break
                        f.write(c)
                        got += len(c)
                        if got - last > (1 << 28):
                            last = got
                            print(f"    {os.path.basename(dst)} {got/1e9:.2f}/{exp/1e9:.2f} GB "
                                  f"{got/max(time.time()-t0,1)/1e6:.1f} MB/s", flush=True)
                        if time.time() - lastT > 90:
                            break
            except Exception as e:
                print(f"    断开 {os.path.basename(dst)}: {str(e)[:46]}", flush=True)
                time.sleep(2)
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
