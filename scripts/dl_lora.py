# -*- coding: utf-8 -*-
"""补下 Qwen-Image-2512 Lightning 4steps LoRA（多源测速后择优）。

官方来源（取自 image_qwen_Image_2512.json 的 MarkdownNote）：
    https://huggingface.co/lightx2v/Qwen-Image-2512-Lightning/resolve/main/Qwen-Image-2512-Lightning-4steps-V1.0-fp32.safetensors

实测速度（2026-09-22，单连接）：
    www.modelscope.cn  32.5 MB/s   ← 采用
    modelscope.cn      21.0 MB/s
    huggingface.co      4.9 MB/s
    hf-mirror.com       1.0 MB/s   ← 被限速，弃用

目录（单一真相源）：`D:\\ComfyUI\\models` 本身就是指回 `D:\\models\\comfyui-models` 的 junction，
所以只要在 `D:\\models\\comfyui-models\\loras` 落文件，ComfyUI 立刻可见，无需再建链接。
"""
import os
import sys

sys.path.insert(0, r"D:\aigc")
from dl_models import fetch, log                      # noqa: E402

NAME = "Qwen-Image-2512-Lightning-4steps-V1.0-fp32.safetensors"
EXPECTED = 1698951104
STORE = r"D:\models\comfyui-models\loras"

SOURCES = [
    ("www.modelscope.cn", "https://www.modelscope.cn/models/lightx2v/Qwen-Image-2512-Lightning/resolve/master/" + NAME),
    ("modelscope.cn", "https://modelscope.cn/models/lightx2v/Qwen-Image-2512-Lightning/resolve/master/" + NAME),
    ("huggingface.co", "https://huggingface.co/lightx2v/Qwen-Image-2512-Lightning/resolve/main/" + NAME),
    ("hf-mirror.com", "https://hf-mirror.com/lightx2v/Qwen-Image-2512-Lightning/resolve/main/" + NAME),
]


def main():
    os.makedirs(STORE, exist_ok=True)
    dest = os.path.join(STORE, NAME)

    if os.path.exists(dest) and os.path.getsize(dest) == EXPECTED:
        log("[skip] 已存在且大小正确: %s" % dest)
        return 0

    part = dest + ".part"
    if os.path.exists(part):
        log("[resume] 已有断点 %.2f GB，将续传" % (os.path.getsize(part) / 1e9))

    for tag, url in SOURCES:
        log("尝试源 %s" % tag)
        if fetch(url, dest, EXPECTED):
            log("完成（源 %s），%.2f GB" % (tag, os.path.getsize(dest) / 1e9))
            return 0
        log("  源 %s 失败，换下一个" % tag)

    log("所有源均失败")
    return 1


if __name__ == "__main__":
    sys.exit(main())
