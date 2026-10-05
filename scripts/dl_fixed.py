# 正确的大文件下载器：
#  ① 每次尝试前重算偏移（内层换源必须重算，否则会重复追加写坏文件）
#  ② 校验响应 Content-Range 的起点 == 请求偏移，不符就换源
#  ③ 最终校验：字节数 + safetensors header
import os, sys, time, json, struct, threading, urllib.request
OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
ROOT = r"D:/models/comfyui-models"; REPO = "Comfy-Org/Qwen-Image-2.1"
ITEMS = ["diffusion_models/qwen_image_2.1_int8_convrot.safetensors",
         "text_encoders/qwen3vl_8b_int8_convrot.safetensors"]
BASES = [f"https://www.modelscope.cn/models/{REPO}/resolve/master/",
         f"https://hf-mirror.com/{REPO}/resolve/main/"]
def total(p):
    for b in BASES:
        try:
            r = OP.open(urllib.request.Request(b+p, headers={"Range":"bytes=0-0","User-Agent":"dl"}), timeout=25)
            cr = r.headers.get("Content-Range") or ""
            if "/" in cr: return int(cr.split("/")[-1])
        except Exception: pass
    return -1
def fetch(p, tries=60):
    dst = os.path.join(ROOT, p.replace("/", os.sep)); os.makedirs(os.path.dirname(dst), exist_ok=True)
    exp = total(p)
    if exp <= 0: return print(f"  取不到大小 {p}")
    part = dst + ".part"
    for _ in range(tries):
        if os.path.exists(dst) and os.path.getsize(dst) == exp: break
        have = os.path.getsize(part) if os.path.exists(part) else 0
        if have > exp: os.remove(part); have = 0          # 已写坏，重来
        if have == exp: os.replace(part, dst); break
        for b in BASES:
            have = os.path.getsize(part) if os.path.exists(part) else 0   # ★ 换源前重算
            if have >= exp: break
            try:
                h = {"User-Agent": "dl"}
                if have: h["Range"] = f"bytes={have}-"
                r = OP.open(urllib.request.Request(b+p, headers=h), timeout=60)
                cr = r.headers.get("Content-Range") or ""
                if have and not cr.startswith(f"bytes {have}-"):
                    print(f"    源未按偏移返回（{cr[:34]}），跳过", flush=True); r.close(); continue
                t0=time.time(); got=have; last=have; lastT=time.time()
                with r, open(part, "ab" if have else "wb") as f:
                    while True:
                        c = r.read(1<<22)
                        if not c: break
                        f.write(c); got += len(c)
                        if got-last > (1<<28):
                            last=got
                            print(f"    {os.path.basename(dst)} {got/1e9:.2f}/{exp/1e9:.2f} GB "
                                  f"{got/max(time.time()-t0,1)/1e6:.1f} MB/s", flush=True)
                        if time.time()-lastT > 90: break
            except Exception as e:
                print(f"    断开 {os.path.basename(dst)}: {str(e)[:46]}", flush=True); time.sleep(2)
    final = os.path.getsize(dst) if os.path.exists(dst) else 0
    ok = (final == exp)
    if ok:  # safetensors header 校验
        with open(dst,"rb") as f:
            hl = struct.unpack("<Q", f.read(8))[0]
            hdr = json.loads(f.read(min(hl, 4_000_000)))
        nt = len(hdr); mx = max((v.get("data_offsets",[0,0])[1] for v in hdr.values() if isinstance(v,dict)), default=0)
        print(f"  OK {os.path.basename(dst)} {final/1e9:.2f} GB  header {hl/1e6:.1f}MB  张量 {nt}  最大偏移 {mx/1e9:.2f}GB", flush=True)
    else:
        print(f"  FAIL {os.path.basename(dst)} {final/1e9:.2f}/{exp/1e9:.2f} GB", flush=True)
ts=[threading.Thread(target=fetch,args=(p,),daemon=True) for p in ITEMS]
[t.start() for t in ts]; [t.join() for t in ts]
