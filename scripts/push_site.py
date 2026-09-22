#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""push_site.py — push-site.mjs 的 Python 移植版。

为什么需要它：本环境**Node 无法 spawn 任何外部进程**（连 cmd.exe 都报 EBUSY -4082），
而 push-site.mjs 依赖 `execFileSync` 调 git 做 CRLF 规范化，因此完全不可用。
**Python 的 subprocess 不受此限制**，所以这里用 Python 复刻同一套逻辑。

逻辑与 push-site.mjs 完全一致：
  1. 绝不直接上传磁盘原始字节 —— 本机 core.autocrlf=true，磁盘是 CRLF、git 存 LF。
     必须经 `git hash-object -w --stdin-paths` 落盘，再 `git cat-file blob` 取回真实字节。
  2. 树构建用「祖先闭包」：只含子目录的中间目录也必须登记，否则整棵子树会从提交里消失。
  3. 动 ref 之前先自检：GET trees/<root>?recursive=1 核对 blob 数 == 本地文件数。

用法:
    python push_site.py <localDir> <owner/repo> <branch> <message>
环境变量: SITE_TOKEN / GH_TOKEN 提供 token；GH_COMMIT_NAME / GH_COMMIT_EMAIL 覆盖署名。
"""
import base64
import json
import os
import subprocess
import sys
import time

GH = r"C:\Users\chenhua\Desktop\1\gh_cli\bin\gh.exe"
GIT = r"C:\Program Files\Git\cmd\git.exe"
SCRATCH = os.path.join(os.environ.get("TEMP", r"C:\Users\chenhua\AppData\Local\Temp"),
                       "keelpush", "py_scratch")
SKIP = {".git", "node_modules", ".DS_Store"}
TRANSIENT = ("Bad Gateway", "502", "503", "504", "timeout", "timed out",
             "ECONNRESET", "ETIMEDOUT", "TLS", "EOF", "Empty reply")


def token():
    t = os.environ.get("SITE_TOKEN") or os.environ.get("GH_TOKEN")
    if t:
        return t.strip()
    try:
        r = subprocess.run([GH, "auth", "token"], capture_output=True, timeout=30)
        if r.returncode == 0:
            return r.stdout.decode().strip()
    except Exception:
        pass
    raise SystemExit("ABORT: no token")


def api(tok, method, path, body=None, attempts=5):
    args = [GH, "api", "-X", method, path]
    data = None
    if body is not None:
        args += ["--input", "-"]
        data = json.dumps(body).encode("utf-8")
    env = dict(os.environ, GH_TOKEN=tok)
    last = None
    for i in range(attempts):
        try:
            r = subprocess.run(args, input=data, capture_output=True, env=env, timeout=300)
            if r.returncode != 0:
                err = r.stderr.decode("utf-8", "replace")
                raise RuntimeError(err)
            out = r.stdout.decode("utf-8", "replace").strip()
            return json.loads(out) if out else {}
        except Exception as e:
            last = e
            msg = str(e)
            if i == attempts - 1 or not any(t in msg for t in TRANSIENT):
                raise
            print(f"    retry {i+1}/{attempts-1}: {msg.splitlines()[0][:90]}", flush=True)
            time.sleep(1.2 * (i + 1))
    raise last


def walk(root):
    out = []
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP]
        for fn in fns:
            if fn in SKIP:
                continue
            ap = os.path.join(dp, fn)
            out.append((os.path.relpath(ap, root).replace("\\", "/"), ap))
    return sorted(out)


def git(args, cwd=None, data=None):
    return subprocess.run([GIT] + args, cwd=cwd, input=data,
                          capture_output=True, timeout=900)


def main():
    if len(sys.argv) < 5:
        raise SystemExit("usage: push_site.py <localDir> <owner/repo> <branch> <message>")
    local_dir, owner_repo, branch, message = sys.argv[1:5]
    owner, repo = owner_repo.split("/")
    tok = token()
    name = os.environ.get("GH_COMMIT_NAME", "speculcom")
    email = os.environ.get("GH_COMMIT_EMAIL", "speculcom@users.noreply.github.com")

    # ---- scratch 对象库（用 rename 挪走旧目录，避免 safe-delete 拦截大目录删除）
    parent = os.path.dirname(SCRATCH)
    os.makedirs(parent, exist_ok=True)
    if os.path.isdir(SCRATCH):
        old = SCRATCH + f"_old_{int(time.time())}"
        try:
            os.rename(SCRATCH, old)
        except OSError:
            pass
    os.makedirs(SCRATCH, exist_ok=True)
    r = git(["init", "-q"], cwd=SCRATCH)
    if r.returncode != 0:
        raise SystemExit("git init failed: " + r.stderr.decode("utf-8", "replace")[:300])

    files = walk(local_dir)
    print(f"local files: {len(files)}")
    if not files:
        raise SystemExit("ABORT: nothing to upload")

    # ---- hash-object -w --stdin-paths：拿到 git 自己会用的 SHA（含 autocrlf 规范化）
    payload = "".join(p.replace("\\", "/") + "\n" for _, p in files).encode("utf-8")
    r = git(["--git-dir", os.path.join(SCRATCH, ".git"), "-c", "core.autocrlf=true",
             "hash-object", "-w", "--stdin-paths"], data=payload)
    if r.returncode != 0:
        raise SystemExit("hash-object failed: " + r.stderr.decode("utf-8", "replace")[:400])
    shas = r.stdout.decode("utf-8", "replace").strip().split("\n")
    if len(shas) != len(files):
        raise SystemExit(f"ABORT: expected {len(files)} hashes, got {len(shas)}")
    sha_by_rel = {rel: shas[i] for i, (rel, _) in enumerate(files)}

    # ---- 远端状态
    head = api(tok, "GET", f"/repos/{owner}/{repo}/git/ref/heads/{branch}")["object"]["sha"]
    tree = api(tok, "GET", f"/repos/{owner}/{repo}/git/trees/{head}?recursive=1")
    if tree.get("truncated"):
        raise SystemExit("ABORT: remote tree listing truncated")
    remote_blobs = {e["path"]: e["sha"] for e in tree["tree"] if e["type"] == "blob"}
    print(f"remote head {head[:8]} — {len(remote_blobs)} blobs at {owner}/{repo}@{branch}")

    known = set(remote_blobs.values())
    cursor = head
    for _ in range(4):
        if not cursor:
            break
        c = api(tok, "GET", f"/repos/{owner}/{repo}/git/commits/{cursor}")
        parents = c.get("parents") or []
        if not parents:
            break
        cursor = parents[0]["sha"]
        t2 = api(tok, "GET", f"/repos/{owner}/{repo}/git/trees/{cursor}?recursive=1")
        if t2.get("truncated"):
            continue
        known |= {e["sha"] for e in t2["tree"] if e["type"] == "blob"}
    print(f"known blobs (history): {len(known)}")

    # ---- 上传缺失 blob（内容取自 git 存储的规范化字节）
    uploaded = reused = 0
    for rel, ap in files:
        sha = sha_by_rel[rel]
        if remote_blobs.get(rel) == sha or sha in known:
            reused += 1
            continue
        rr = git(["--git-dir", os.path.join(SCRATCH, ".git"), "cat-file", "blob", sha])
        if rr.returncode != 0:
            raise SystemExit("cat-file failed for " + rel)
        api(tok, "POST", f"/repos/{owner}/{repo}/git/blobs",
            {"content": base64.b64encode(rr.stdout).decode(), "encoding": "base64"})
        uploaded += 1
        if uploaded % 25 == 0:
            print(f"    ... {uploaded} uploaded", flush=True)
    print(f"blobs: {uploaded} uploaded, {reused} reused")

    # ---- 祖先闭包 + 自底向上建树
    all_dirs = {""}
    for rel, _ in files:
        parts = rel.split("/")[:-1]
        acc = ""
        for seg in parts:
            acc = f"{acc}/{seg}" if acc else seg
            all_dirs.add(acc)
    children = {d: [] for d in all_dirs}
    for rel, _ in files:
        parts = rel.split("/")
        fn = parts.pop()
        children["/".join(parts)].append({"path": fn, "mode": "100644",
                                          "type": "blob", "sha": sha_by_rel[rel]})
    for d in all_dirs:
        if not d:
            continue
        parts = d.split("/")
        fn = parts.pop()
        children["/".join(parts)].append({"path": fn, "mode": "040000", "type": "tree",
                                          "_dir": d})

    depth = lambda d: len([x for x in d.split("/") if x])
    dir_sha = {}
    for d in sorted(all_dirs, key=depth, reverse=True):
        entries = []
        for e in children[d]:
            if e["type"] == "blob":
                entries.append(e)
            else:
                sub = dir_sha.get(e["_dir"])
                if not sub:
                    raise SystemExit(f"internal: tree sha missing for {e['_dir']}")
                entries.append({"path": e["path"], "mode": "040000", "type": "tree", "sha": sub})
        entries.sort(key=lambda x: x["path"])
        if not entries:
            raise SystemExit(f"internal: empty tree for {d or '<root>'}")
        dir_sha[d] = api(tok, "POST", f"/repos/{owner}/{repo}/git/trees", {"tree": entries})["sha"]
    root_sha = dir_sha.get("")
    if not root_sha:
        raise SystemExit("internal: no root tree built")

    check = api(tok, "GET", f"/repos/{owner}/{repo}/git/trees/{root_sha}?recursive=1")
    n = len([e for e in check["tree"] if e["type"] == "blob"])
    if check.get("truncated") or n != len(files):
        raise SystemExit(f"ABORT: built tree holds {n} blobs, expected {len(files)}")
    print(f"tree self-check: {n} blobs OK")

    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    ident = {"name": name, "email": email, "date": now}
    commit = api(tok, "POST", f"/repos/{owner}/{repo}/git/commits",
                 {"message": message, "tree": root_sha, "parents": [head],
                  "author": ident, "committer": ident})
    api(tok, "PATCH", f"/repos/{owner}/{repo}/git/refs/heads/{branch}", {"sha": commit["sha"], "force": False})
    print(f"{owner}/{repo}@{branch} -> {commit['sha']}")


if __name__ == "__main__":
    main()
