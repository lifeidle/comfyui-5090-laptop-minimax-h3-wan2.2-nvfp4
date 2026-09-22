# -*- coding: utf-8 -*-
"""run_batch.py — 顺序跑多个工作流（GPU 必须串行），每个带独立超时上限。

用法:
    python run_batch.py wf1.json@600 wf2.json@900 ...
注意：分隔符用 @ 而不是 :，因为 Windows 盘符 (D:\...) 里本身就有冒号，用冒号会被切歪。
"""
import subprocess, sys, os, time, json

PY = r"D:\aigc\venv\Scripts\python.exe"
RUNNER = r"D:\aigc\run_wf.py"
RESULTS = r"D:\aigc\output\batch_results.json"
SEP = "@"


def main():
    specs = sys.argv[1:]
    out = {}
    if os.path.exists(RESULTS):
        try:
            out = json.load(open(RESULTS, encoding="utf-8"))
        except Exception:
            out = {}
    for sp in specs:
        wf, _, to = sp.partition(SEP)
        to = to or "900"
        name = os.path.basename(wf.replace("\\", "/"))
        print(f"\n########## {name}  (timeout {to}s) ##########", flush=True)
        t0 = time.time()
        r = subprocess.run([PY, "-u", RUNNER, wf, "--free", "--timeout", to],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        elapsed = time.time() - t0
        print(r.stdout[-2500:], flush=True)
        if r.stderr.strip():
            print("STDERR:", r.stderr[-800:], flush=True)
        # 抓服务端权威耗时
        exec_s = None
        status = "?"
        for line in (r.stdout or "").splitlines():
            if "服务端执行耗时" in line:
                try:
                    exec_s = float(line.split(":")[1].strip().split()[0])
                except Exception:
                    pass
            if line.strip().startswith("状态:"):
                status = line.split(":", 1)[1].strip()
        out[name] = {"exec_s": exec_s, "status": status, "wall_s": round(elapsed, 1)}
        print(f"--> {name}: status={status} exec={exec_s}s wall={elapsed:.1f}s", flush=True)
        json.dump(out, open(RESULTS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n===== 汇总 =====")
    for k, v in out.items():
        print(f"  {k:44s} {v['status']:8s} exec={v['exec_s']}")


if __name__ == "__main__":
    main()
