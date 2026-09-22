#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_workflow.py — submit a ComfyUI workflow over the HTTP API and time it properly

Two things this script exists to get right:

1. AUTHORITATIVE TIMING
   The only honest execution time comes from the server's own history entry: the
   `execution_start` and `execution_success` timestamps inside /history/<id>.
   Wall-clock and API round-trip deltas fold queueing and model loading into the number.
   On a 21 GB model that has to be offloaded, that difference is minutes.

2. THE FREE DRY RUN
   POSTing a graph whose models are not downloaded yet returns HTTP 400 with per-node
   `node_errors`. If every error is `value_not_in_list`, the graph's structure and types
   are correct and only the weights are missing. That turns validation into a free step
   you can run before spending hours on downloads.

Usage
-----
    python scripts/run_workflow.py workflows/z_image_turbo_nvfp4.json
    python scripts/run_workflow.py wf.json --free --timeout 900
    python scripts/run_workflow.py wf.json --seed 12345 --free
    python scripts/run_workflow.py wf.json --dry          # validate, never execute
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

DEFAULT_HOST = os.environ.get("COMFY_HOST", "http://127.0.0.1:8188")


def post(host: str, path: str, payload):
    """POST JSON. Returns {} for an empty body — /free replies 200 with no content."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(host + path, data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read().decode("utf-8", "replace").strip()
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace").strip()
        try:
            return {"__http_error__": e.code, **json.loads(body)}
        except Exception:
            return {"__http_error__": e.code, "raw": body[:2000]}


def get(host: str, path: str):
    with urllib.request.urlopen(host + path, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def free_vram(host: str) -> None:
    post(host, "/free", {"unload_models": True, "free_memory": True})


def vram_free_gb(host: str) -> str:
    try:
        s = get(host, "/system_stats")
        for dev in s.get("devices", []):
            return "%.2f / %.2f GB" % (dev.get("vram_free", 0) / 1e9,
                                       dev.get("vram_total", 0) / 1e9)
    except Exception:
        pass
    return "?"


def explain_node_errors(err: dict) -> bool:
    """Print node errors. Returns True if the graph is structurally fine (only missing models)."""
    node_errors = err.get("node_errors") or {}
    if not node_errors:
        print("   error: %s" % err.get("error"))
        return False
    only_missing = True
    for node_id, info in node_errors.items():
        for e in info.get("errors", []):
            kind = e.get("type", "?")
            if kind != "value_not_in_list":
                only_missing = False
            detail = e.get("extra_info", {})
            msg = e.get("message", "")
            if kind == "value_not_in_list":
                recv = detail.get("input_name", "?")
                val = detail.get("received_value", "?")
                print("   node %-5s %s: %s = %r not available" % (node_id, kind, recv, val))
            else:
                print("   node %-5s %s: %s" % (node_id, kind, msg))
    if only_missing:
        print("   => every error is 'value_not_in_list': the GRAPH IS VALID, only models are missing")
    return only_missing


def main() -> int:
    ap = argparse.ArgumentParser(description="Submit a ComfyUI workflow and time it server-side")
    ap.add_argument("workflow", help="path to an API-format workflow JSON")
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--timeout", type=float, default=1800, help="seconds to wait for completion")
    ap.add_argument("--free", action="store_true", help="POST /free before submitting")
    ap.add_argument("--seed", type=int, default=None, help="override the seed in KSampler nodes")
    ap.add_argument("--dry", action="store_true", help="validate only, do not execute")
    args = ap.parse_args()

    with open(args.workflow, encoding="utf-8") as f:
        wf = json.load(f)

    if args.seed is not None:
        n = 0
        for node in wf.values():
            if isinstance(node, dict) and "seed" in (node.get("inputs") or {}):
                node["inputs"]["seed"] = args.seed
                n += 1
        print("seed override applied to %d node(s)" % n)

    if args.free:
        free_vram(args.host)
        print("freed VRAM, now: %s" % vram_free_gb(args.host))
    print("VRAM free before submit: %s" % vram_free_gb(args.host))

    res = post(args.host, "/prompt", {"prompt": wf})
    if "__http_error__" in res:
        print("!! HTTP %s from /prompt" % res["__http_error__"])
        explain_node_errors(res)
        return 2
    if res.get("node_errors"):
        print("!! graph rejected")
        explain_node_errors(res)
        return 2

    pid = res.get("prompt_id")
    print("submitted prompt_id=%s" % pid)
    if args.dry:
        print("dry run: graph accepted, nothing executed")
        return 0

    t_wall = time.time()
    t_prev = t_wall
    while True:
        time.sleep(2)
        hist = get(args.host, "/history/%s" % pid)
        entry = hist.get(pid)
        if entry:
            status = (entry.get("status") or {}).get("status_str", "?")
            messages = (entry.get("status") or {}).get("messages") or []
            ts = {}
            for name, payload in messages:
                if name in ("execution_start", "execution_success", "execution_error"):
                    ts[name] = (payload or {}).get("timestamp")
            if status in ("success", "error"):
                files = []
                for out in (entry.get("outputs") or {}).values():
                    for key in ("images", "video", "gifs", "audio"):
                        files.extend(out.get(key) or [])
                exec_s = None
                if "execution_start" in ts and "execution_success" in ts:
                    exec_s = (ts["execution_success"] - ts["execution_start"]) / 1000.0
                print()
                print("=== %s ===" % os.path.basename(args.workflow))
                print("status        : %s" % status)
                if exec_s is not None:
                    print("server exec   : %.1f s" % exec_s)
                else:
                    print("server exec   : n/a")
                print("wall clock    : %.1f s" % (time.time() - t_wall))
                for f in files:
                    fn = f.get("filename")
                    if not fn:
                        continue
                    sub = f.get("subfolder") or ""
                    kind = f.get("type", "output")
                    print("output        : %s" % os.path.join(kind, sub, fn))
                if status == "error":
                    for name, payload in messages:
                        if name == "execution_error":
                            print("ERROR: %s" % (payload or {}).get("exception_message"))
                    return 1
                return 0
        else:
            if time.time() - t_wall > args.timeout:
                print("!! timeout after %.0f s waiting for %s" % (args.timeout, pid))
                return 3
            if time.time() - t_prev > 30:
                print("   ... %.0f s, VRAM free %s" % (time.time() - t_wall, vram_free_gb(args.host)))
                t_prev = time.time()
            continue
        if time.time() - t_wall > args.timeout:
            print("!! timeout after %.0f s" % args.timeout)
            return 3


if __name__ == "__main__":
    sys.exit(main())
