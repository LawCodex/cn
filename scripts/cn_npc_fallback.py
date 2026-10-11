"""Resolve npc.gov.cn (中国人大网) pages for laws not (or not up to date) in the MOFCOM database.

Inputs:  _raw/cn/mulu.json, _raw/cn/npc_index.json (from cn_npc_index.py),
         scripts/npc_law_urls.tsv (curated: title<TAB>url, for pages outside the indexed column,
         e.g. the constitution in the legacy zgrdw archive).
Output:  _raw/cn/npc_fallback.json {title: {url, date}}; pages are fetched into the cache.
A page is accepted only if its text's amendment history mentions the latest year in the NPC list.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cn_common import RAW, Blocked, fetch  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def n(s):
    return re.sub(r"[\s　]", "", s).replace("(", "（").replace(")", "）")


def head_years(html):
    m = re.search(r'id="(?:Zoom|UCAP-CONTENT)"(.*)', html, re.S)
    body = re.sub(r"<[^>]+>", "", m.group(1) if m else html)
    body = body.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    i = body.find("（")
    seg = body[i:i + 1500] if i >= 0 else body[:1500]
    seg = seg.split("）")[0]
    return {int(y) for y in re.findall(r"(\d{4})\s*年", seg)}


def main():
    mulu = json.load(open(os.path.join(RAW, "mulu.json")))["entries"]
    idx = json.load(open(os.path.join(RAW, "npc_index.json")))
    by = {}
    for it in idx:
        by.setdefault(n(it["title"]), []).append(it)
    curated = {}
    tsv = os.path.join(HERE, "npc_law_urls.tsv")
    if os.path.exists(tsv):
        for line in open(tsv, encoding="utf-8"):
            if line.strip() and not line.startswith("#"):
                t, u = line.rstrip("\n").split("\t")[:2]
                curated.setdefault(t, []).append({"title": t, "url": u, "date": None})
    only = set(sys.argv[1:])
    mp = os.path.join(RAW, "laws_manifest.json")
    if not only and os.path.exists(mp):
        man = json.load(open(mp))
        only = {x["title"] for x in man["missing"]} | {x["title"] for x in man["matched"] if x.get("stale")}
        only |= {"中华人民共和国宪法"}
    out, blocked = {}, []
    for e in mulu:
        t = e["title"]
        if e["category"] == "宪法":
            t = "中华人民共和国宪法" if "修正案" not in e["title"] else e["title"]
        if only and t not in only and e["title"] not in only:
            continue
        cands = curated.get(t, []) + sorted(by.get(n(t), []), key=lambda x: x["date"] or "", reverse=True)
        for c in cands[:4]:
            try:
                html = fetch(c["url"])
            except Blocked:
                print("BLOCKED (JS challenge, skipped)", t, c["url"], file=sys.stderr)
                blocked.append(t)
                break
            if not html or not re.search(r'id="(?:Zoom|UCAP-CONTENT)"', html):
                continue  # dead link (redirects to the home page) or unknown layout
            ys = head_years(html)
            need = e.get("last_year") or 0
            if e["category"] == "宪法" or c in curated.get(t, []) or (ys and max(ys) >= need):
                out[t] = {"url": c["url"], "date": c["date"], "years": sorted(ys)}
                break
    with open(os.path.join(RAW, "npc_fallback.json"), "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(len(out), "resolved;", len(blocked), "blocked by bot challenge", file=sys.stderr)


if __name__ == "__main__":
    main()
