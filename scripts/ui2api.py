# -*- coding: utf-8 -*-
"""ui2api.py — 把 ComfyUI 官方模板（UI / workflow 格式）转成可直接 POST /prompt 的 API 格式。

背景：`comfyui_workflow_templates_json/templates/*.json` 里大部分是**扁平 UI 格式**
（节点 type 是真实类名），可以直接转换；少数是**子图格式**（type 为 UUID + definitions），
本脚本会先把子图展开再转换。

转换要点
--------
1. widget 与 link 的判定：`INPUT_TYPES` 里类型是 list（combo）或 INT/FLOAT/STRING/BOOLEAN
   的算 widget；其余（MODEL/CLIP/VAE/CONDITIONING/LATENT/IMAGE/AUDIO/…）算 link 输入。
2. `widgets_values` 按上述 widget 顺序**位置对齐**赋给 inputs。
3. 有 link 的输入覆盖位置对齐的值。
4. `PrimitiveNode` 在 API 格式里不存在 → 内联成字面量常数。
5. `Reroute` 一路回溯到真实来源。
6. `Note` / `MarkdownNote` / `Group` 直接丢弃。

用法:
    python ui2api.py --list                      # 列出可用模板
    python ui2api.py <模板名或绝对路径>           # 转成 API 格式并打印
    python ui2api.py <模板> -o <输出.json>        # 写文件
    python ui2api.py <模板> --validate            # POST /prompt 做结构与类型校验
"""
import argparse
import json
import os
import sys
import urllib.request

TPL_DIRS = [
    r"D:\aigc\venv\Lib\site-packages\comfyui_workflow_templates_json\templates",
    r"D:\ComfyUI\blueprints",
]
API_ROOT = "http://127.0.0.1:8188"
WIDGET_SCALAR = {"INT", "FLOAT", "STRING", "BOOLEAN"}
DROP_TYPES = {"Note", "MarkdownNote", "Group"}
PASSTHRU_TYPES = {"Reroute"}
CONST_TYPES = {"PrimitiveNode"}


def opener():
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def load_object_info():
    with opener().open(API_ROOT + "/object_info", timeout=120) as r:
        oi = json.load(r)
    # 可连线类型 = 所有节点的输出类型之并集。
    # widget 类型（INT/FLOAT/STRING/BOOLEAN/combo/COMFY_* 动态组合）永远不会作为输出类型出现，
    # 因此「类型不在输出集合里」就是判定 widget 的可靠依据 —— 比硬编码白名单稳。
    outs = set()
    for info in oi.values():
        for t in (info.get("output") or []):
            if isinstance(t, str):
                outs.add(t)
    globals()["OUTPUT_TYPES"] = outs
    return oi


def is_widget_type(t):
    """widget 判定 —— 两条规则取并集，缺一不可：
      1) 标量/combo 白名单：INT / FLOAT / STRING / BOOLEAN / COMBO，或类型本身就是 list（下拉）；
      2) 「不在输出类型集合里」：覆盖 v3 的 COMFY_DYNAMICCOMBO_V3 之类动态类型。
    规则 2 不能单独使用 —— INT / FLOAT / STRING 也可能是别的节点的输出类型（实测如此），
    只按规则 2 会把 seed / steps / cfg 全判成连线输入。"""
    if isinstance(t, list):
        return True
    if not isinstance(t, str):
        return False
    if t in WIDGET_SCALAR or t == "COMBO":
        return True
    return t not in globals().get("OUTPUT_TYPES", set())


def widget_slots(oi, ctype):
    """返回 (slots, specs)。slots 里 None 表示前端插入的 `control_after_generate` 伪 widget
    （凡 spec 里带 control_after_generate=True 的种子类参数，前端都会在其后多插一个 combo），
    它必须占位以保持 widgets_values 的位置对齐，但不产出 API 输入。
    specs[name] = 该参数的 options dict（用于缺值时回填 default）。"""
    info = oi.get(ctype)
    if not info:
        return None, None
    inp = info.get("input", {}) or {}
    slots, specs = [], {}
    for sect in ("required", "optional"):
        for name, spec in (inp.get(sect) or {}).items():
            t = spec[0] if isinstance(spec, (list, tuple)) and spec else spec
            opts = (spec[1] if isinstance(spec, (list, tuple)) and len(spec) > 1
                    and isinstance(spec[1], dict) else {})
            if is_widget_type(t):
                slots.append(name)
                specs[name] = opts
                if opts.get("control_after_generate"):
                    slots.append(None)
    return slots, specs


# ------------------------------------------------------------ subgraph expansion
def expand_subgraphs(d):
    """把顶层 'type' 为 UUID 的节点替换成其子图内部节点，并把**子图边界上的连线接回来**。

    关键点（踩过坑）：子图节点在内层用「子图自己的输入/输出定义」作为边界 ——
      * 子图的 outputs[i].linkIds 指向内层某条 link，那条 link 的 origin 才是真正的输出源；
      * 子图的 inputs[j].linkIds 指向内层某条 link，那条 link 的 target 才是真正的输入口。
    只把内层节点搬出来、不重建这两侧边界，外层节点就会**丢连线**
    （现象：SaveAudioAdvanced 缺 audio、PreviewAny 缺 source），而节点本身看起来都在。
    """
    defs = (d.get("definitions") or {}).get("subgraphs") or []
    if not defs:
        return d
    sg_by_id = {s.get("id"): s for s in defs}
    nodes = list(d.get("nodes", []))
    links = list(d.get("links", []))

    out_nodes = []
    next_id = max([n.get("id", 0) for n in nodes] + [0]) + 1000
    # 外层连线先把「子图节点边界」记录下来，稍后统一改写
    out_links = []
    for L in links:
        if isinstance(L, dict):
            out_links.append([L.get("id"), L.get("origin_id"), L.get("origin_slot"),
                              L.get("target_id"), L.get("target_slot"), L.get("type", "*")])
        else:
            out_links.append(list(L))

    fix_origin = {}   # (subgraph_node_id, out_slot) -> (inner_id, inner_slot)
    fix_target = {}   # (subgraph_node_id, in_slot)  -> (inner_id, inner_slot)

    for n in nodes:
        sg = sg_by_id.get(n.get("type"))
        if not sg:
            out_nodes.append(n)
            continue

        idmap, newlinks, link_ends = {}, [], {}
        for sn in sg.get("nodes", []):
            if sn["type"] in DROP_TYPES:
                continue
            nn = dict(sn)
            idmap[sn["id"]] = next_id
            nn["id"] = next_id
            next_id += 1
            out_nodes.append(nn)

        # 内层 links：重建并记住 link_id -> (origin_id, origin_slot) / (target_id, target_slot)
        for L in (sg.get("links") or []):
            if isinstance(L, dict):
                lid = L.get("id"); oid = L.get("origin_id"); oslot = L.get("origin_slot")
                tid = L.get("target_id"); tslot = L.get("target_slot")
            else:
                lid, oid, oslot, tid, tslot = (list(L) + [None] * 5)[:5]
            link_ends[lid] = (oid, oslot, tid, tslot)
            if oid in idmap and tid in idmap:
                newlinks.append([lid, idmap[oid], oslot, idmap[tid], tslot, "*"])
        out_links.extend(newlinks)

        # 子图输出：outputs[i].linkIds -> 内层 link -> origin
        for i, o in enumerate(sg.get("outputs") or []):
            for lid in (o.get("linkIds") or []):
                ends = link_ends.get(lid)
                if ends and ends[0] in idmap:
                    fix_origin[(n["id"], i)] = (idmap[ends[0]], ends[1])
        # 子图输入：inputs[j].linkIds -> 内层 link -> target
        for j, inp in enumerate(sg.get("inputs") or []):
            for lid in (inp.get("linkIds") or []):
                ends = link_ends.get(lid)
                if ends and ends[2] in idmap:
                    fix_target[(n["id"], j)] = (idmap[ends[2]], ends[3])

    # 改写外层连线：origin / target 落在子图节点上的，换成内层真实端点
    # 注意：fix_* 的键是 (节点id, 槽位) 元组，不能用 L[1] 单独查成员（int 永远匹配不上元组键）
    for L in out_links:
        if (L[1], L[2]) in fix_origin:
            L[1], L[2] = fix_origin[(L[1], L[2])]
        if (L[3], L[4]) in fix_target:
            L[3], L[4] = fix_target[(L[3], L[4])]

    # 丢掉仍指向子图节点（未映射上）的连线
    sg_ids = set(sg_by_id.keys())

    def alive(L):
        return L[1] not in sg_ids and L[3] not in sg_ids

    d2 = dict(d)
    d2["nodes"] = out_nodes
    d2["links"] = [L for L in out_links if alive(L)]
    return d2


# ------------------------------------------------------------ core conversion
def convert(d, oi):
    d = expand_subgraphs(d)
    nodes = {n["id"]: n for n in d.get("nodes", [])}

    lm = {}
    for L in d.get("links") or []:
        if isinstance(L, dict):
            lm[L["id"]] = (L.get("origin_id"), L.get("origin_slot"))
        else:
            lm[L[0]] = (L[1], L[2])

    warn = []

    def origin_of(nid, slot):
        """回溯 Reroute 与任何本机不存在的包装节点（如 EasyCache），返回 (node_id, slot)。
        PrimitiveNode 原样返回，交给调用方内联成常数。"""
        seen = set()
        while nid is not None and nid not in seen:
            seen.add(nid)
            n = nodes.get(nid)
            if n is None:
                return None
            t = n["type"]
            if t in CONST_TYPES:
                return (nid, slot)
            if t in PASSTHRU_TYPES or t not in oi:
                ins = n.get("inputs") or []
                if not ins or ins[0].get("link") is None:
                    return None
                nid, slot = lm.get(ins[0]["link"], (None, None))
                continue
            return (nid, slot)
        return None

    prompt = {}
    for nid, n in nodes.items():
        ctype = n.get("type")
        if ctype in DROP_TYPES or ctype in PASSTHRU_TYPES or ctype in CONST_TYPES:
            continue
        if ctype not in oi:
            warn.append(f"本机无此节点类型，已按穿透处理: node {nid} type={ctype}")
            continue
        slots, specs = widget_slots(oi, ctype)
        if slots is None:
            warn.append(f"object_info 无 {ctype}，已跳过")
            continue
        wvals = list(n.get("widgets_values") or [])
        inputs = {}
        # 位置对齐赋值，并按需展开 COMFY_DYNAMICCOMBO_V3 的依赖子字段：
        # 动态 combo 选中某个 key 后，前端会在其后追加该 key 声明的子 widget（如 format=mp3 -> quality）。
        # 子字段名必须补进槽位序列，否则 widgets_values 会整体错位、且必填项会缺失。
        queue = list(slots)
        pos = 0
        while queue:
            name = queue.pop(0)
            if name is None:                     # control_after_generate 伪 widget 占一个值
                pos += 1
                continue
            if pos < len(wvals):
                val = wvals[pos]
            else:
                val = specs.get(name, {}).get("default")
            pos += 1
            if val is not None:
                inputs[name] = val
            for opt in (specs.get(name, {}).get("options") or []):
                if not (isinstance(opt, dict) and opt.get("key") == val):
                    continue
                # v3 动态 combo 的子字段在 API 里是「点号命名空间」：
                #   format = "mp3"  ->  子字段写作 "format.quality"
                # （实测：写裸 "quality" 会被判 required_input_missing: format.quality）
                subs = ((opt.get("inputs") or {}).get("required") or {})
                subs_opt = ((opt.get("inputs") or {}).get("optional") or {})
                for sk in reversed(list(subs.keys())):
                    sp = subs[sk]
                    specs.setdefault(f"{name}.{sk}",
                                     sp[1] if isinstance(sp, (list, tuple)) and len(sp) > 1
                                     and isinstance(sp[1], dict) else {})
                    queue.insert(0, f"{name}.{sk}")
                for sk in reversed(list(subs_opt.keys())):
                    sp = subs_opt[sk]
                    specs.setdefault(f"{name}.{sk}",
                                     sp[1] if isinstance(sp, (list, tuple)) and len(sp) > 1
                                     and isinstance(sp[1], dict) else {})
                    queue.insert(0, f"{name}.{sk}")

        # link 覆盖
        for inp in (n.get("inputs") or []):
            lid = inp.get("link")
            if lid is None:
                continue
            src = origin_of(*lm.get(lid, (None, None)))
            if not src:
                continue
            onid, oslot = src
            on = nodes.get(onid)
            if on is None:
                continue
            if on["type"] in CONST_TYPES:
                pv = list(on.get("widgets_values") or [])
                if pv:
                    inputs[inp["name"]] = pv[0]
                continue
            inputs[inp["name"]] = [str(onid), oslot]

        prompt[str(nid)] = {"class_type": ctype, "inputs": inputs}
    return prompt, warn


# ------------------------------------------------------------ validate
def validate(prompt):
    body = json.dumps({"prompt": prompt, "client_id": "ui2api-validate"}).encode()
    req = urllib.request.Request(API_ROOT + "/prompt", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with opener().open(req, timeout=60) as r:
            res = json.load(r)
        print("VALIDATED — prompt_id:", res.get("prompt_id"))
        return True, res
    except urllib.error.HTTPError as e:
        txt = e.read().decode("utf-8", "replace")
        try:
            err = json.loads(txt)
        except Exception:
            print("HTTP", e.code, txt[:1500])
            return False, None
        print("HTTP", e.code)
        if err.get("error"):
            print("  error:", json.dumps(err["error"], ensure_ascii=False)[:600])
        ne = err.get("node_errors") or {}
        only_missing = True
        for k, v in ne.items():
            for e2 in v.get("errors", []):
                t = e2.get("type")
                d2 = json.dumps(e2.get("extra", {}), ensure_ascii=False)[:220]
                print(f"  node {k} [{v.get('class_type')}] {t}: {d2}")
                if t != "value_not_in_list":
                    only_missing = False
        if ne and only_missing:
            print("  => 只报缺模型/枚举值 → 图结构与类型正确")
        return False, err
    except Exception as e:
        print("请求失败:", e)
        return False, None


def find_template(name):
    if os.path.isabs(name) and os.path.exists(name):
        return name
    for D in TPL_DIRS:
        p = os.path.join(D, name)
        if os.path.exists(p):
            return p
    for D in TPL_DIRS:
        for fn in os.listdir(D):
            if name.lower() in fn.lower() and fn.endswith(".json"):
                return os.path.join(D, fn)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("template", nargs="?")
    ap.add_argument("-o", "--out")
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--no-subgraph", action="store_true")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()

    if a.list or not a.template:
        for D in TPL_DIRS:
            print(f"--- {D}")
            for fn in sorted(os.listdir(D)):
                if fn.endswith(".json"):
                    print("   ", fn)
        return

    p = find_template(a.template)
    if not p:
        print("找不到模板:", a.template)
        sys.exit(1)
    print("template:", p)
    d = json.load(open(p, encoding="utf-8"))
    oi = load_object_info()
    prompt, warn = convert(d, oi)
    for w in warn:
        print("  WARN", w)
    print(f"API 节点数: {len(prompt)}")
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
        with open(a.out, "w", encoding="utf-8", newline="\n") as f:
            json.dump(prompt, f, ensure_ascii=False, indent=1)
        print("wrote", a.out)
    else:
        print(json.dumps(prompt, ensure_ascii=False, indent=1)[:4000])
    if a.validate:
        validate(prompt)


if __name__ == "__main__":
    main()
