"""Fetch Chinese national legislation for LawCodex (cn) into the _raw/cn cache.

Stages (run all by default, or name some: laws regs jis):

  laws  NPC 现行有效法律目录 (list of laws in force, by legal department; npc.gov.cn PDF)
        + MOFCOM 全球法规网 (policy.mofcom.gov.cn/claw) law list (效力级别=法律) and texts.
  regs  国家行政法规库 (xzfg.moj.gov.cn): list of 现行有效 administrative regulations + texts.
  jis   MOFCOM 全球法规网 judicial interpretations (效力级别=司法解释) in force + texts.

Writes manifests to _raw/cn/*.json; all HTTP responses cached under _raw/cn/cache/.
flk.npc.gov.cn is NOT used: its robots.txt disallows all crawling and states
"禁止使用任何自动化工具、脚本、爬虫程序采集或复制网站数据".
"""
import json
import os
import re
import subprocess
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cn_common import RAW, fetch  # noqa: E402

MOF = "https://policy.mofcom.gov.cn"
XZFG = "https://xzfg.moj.gov.cn"


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def save(name, obj):
    with open(os.path.join(RAW, name), "w") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def clean(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


# ---------------------------------------------------------------- MOFCOM lists
def mof_list(sort_id, sort_name):
    out, page, maxp = [], 1, 1
    while page <= maxp:
        q = {
            "pageNum": page, "sortName": sort_name, "fg": "2", "xiaoliTp": sort_id,
            "queryCon": json.dumps([{"fg": "2", "sortId": sort_id, "sortName": sort_name}], ensure_ascii=False,
                                   separators=(",", ":")),
        }
        url = MOF + "/claw/keySearchMore.shtml?" + urllib.parse.urlencode(q)
        html = fetch(url, refresh=os.environ.get("CN_REFRESH") == "1")
        m = re.search(r'name="maxNum" value="(\d+)"', html)
        maxp = int(m.group(1)) if m else page
        for li in re.findall(r'<li>\s*<p class="p1">(.*?)</li>', html, re.S):
            a = re.search(r'clawContent\.shtml\?id=(\d+)">([^<]+)<', li)
            if not a:
                continue
            p2 = re.search(r'class="p2">(.*?)</p>', li, re.S)
            parts = [x.strip() for x in clean(p2.group(1)).split(" / ")] if p2 else []
            rec = {"id": int(a.group(1)), "title": a.group(2).strip(), "docno": None, "status": None,
                   "published": None, "effective": None}
            for p in parts:
                if p.endswith("发布"):
                    rec["published"] = p[:-2].replace(".", "-")
                elif p.endswith("实施"):
                    rec["effective"] = p[:-2].replace(".", "-")
                elif p in ("现行有效", "已被修改", "已经失效", "尚未生效", "部分失效"):
                    rec["status"] = p
                elif p:
                    rec["docno"] = p
            out.append(rec)
        log(f"mofcom {sort_name} page {page}/{maxp} ({len(out)})")
        page += 1
    return out


def norm_title(t):
    t = re.sub(r"[\s　]", "", t)
    t = t.replace("(", "（").replace(")", "）").replace("〈", "《").replace("〉", "》")
    t = re.sub(r"（(\d{4})?(年)?(修正|修订|修改|第[一二三四五六七八九十]+次修正)?(文本)?）$", "", t)
    t = re.sub(r"（\d{4}年?[^（）]*）$", "", t)
    t = t.replace("全国人大常委会", "全国人民代表大会常务委员会")
    return t


def stage_laws():
    subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "cn_mulu.py")], check=True)
    mulu = json.load(open(os.path.join(RAW, "mulu.json")))
    recs = mof_list("1", "法律")
    save("mof_laws_list.json", recs)
    by = {}
    for r in recs:
        by.setdefault(norm_title(r["title"]), []).append(r)
    matched, missing = [], []
    for e in mulu["entries"]:
        key = norm_title(e["title"])
        if e["category"] == "宪法":
            key = "中华人民共和国宪法" if "修正案" not in e["title"] else e["title"]
        cands = by.get(norm_title(key), [])
        good = [c for c in cands if c["status"] in ("现行有效", "尚未生效", "部分失效")]
        pick = None
        if good:
            pick = max(good, key=lambda c: (c["published"] or "", c["id"]))
        elif cands:
            pick = max(cands, key=lambda c: (c["published"] or "", c["id"]))
        if pick and e.get("last_year") and pick["published"] and int(pick["published"][:4]) < e["last_year"]:
            log("STALE", e["title"], pick["published"], e["last_year"])
            e["stale"] = True
        if pick:
            e["mofcom"] = pick
            # current in-force version too when the newest one is not yet in force
            if pick["status"] == "尚未生效":
                cur = [c for c in cands if c["status"] in ("现行有效", "部分失效") and c is not pick]
                if cur:
                    e["mofcom_current"] = max(cur, key=lambda c: (c["published"] or "", c["id"]))
            matched.append(e)
        else:
            missing.append(e)
    log(f"laws: {len(matched)} matched, {len(missing)} missing")
    for e in missing:
        log("  MISSING", e["category"], e["title"])
    for e in matched:
        for k in ("mofcom", "mofcom_current"):
            if k in e:
                fetch(f"{MOF}/claw/clawContent.shtml?id={e[k]['id']}")
    mulu["matched"] = matched
    mulu["missing"] = missing
    save("laws_manifest.json", mulu)


def stage_jis():
    recs = mof_list("3", "司法解释")
    save("mof_jis_list.json", recs)
    keep = [r for r in recs if r["status"] in ("现行有效", "部分失效", "尚未生效")]
    log(f"judicial interpretations: {len(recs)} listed, {len(keep)} in force")
    for r in keep:
        fetch(f"{MOF}/claw/clawContent.shtml?id={r['id']}")
    save("jis_manifest.json", keep)


# ---------------------------------------------------------------- xzfg (State Council regulations)
def stage_regs():
    out, page, maxp = [], 1, 1
    while page <= maxp:
        url = f"{XZFG}/search2.html" + (f"?PageIndex={page}" if page > 1 else "")
        html = fetch(url, refresh=os.environ.get("CN_REFRESH") == "1")
        m = re.search(r'id="page-count" value="(\d+)"', html)
        maxp = int(m.group(1)) if m else page
        total = re.search(r'id="law-total" value="(\d+)"', html)
        for li in re.findall(r'<li class="list-item">(.*?)</li>\s*(?=<li class="list-item">|</ul>)', html, re.S):
            a = re.search(r'detail\?LawID=(\d+)">([^<]+)<', li)
            if not a:
                continue
            pub = re.search(r"(\d{4}-\d{2}-\d{2})公布", li)
            imp = re.search(r"(\d{4}-\d{2}-\d{2})施行", li)
            hist = re.findall(r'data-time="([\d-]+)">\s*<a class="[^"]*"[^>]*LawID=(\d+)"', li)
            out.append({"id": int(a.group(1)), "title": a.group(2).strip(),
                        "published": pub.group(1) if pub else None,
                        "effective": imp.group(1) if imp else None,
                        "history": [{"date": d, "id": int(i)} for d, i in hist]})
        log(f"xzfg page {page}/{maxp} ({len(out)}/{total.group(1) if total else '?'})")
        page += 1
    seen, uniq = set(), []
    for r in out:
        if r["id"] not in seen:
            seen.add(r["id"])
            uniq.append(r)
    save("regs_manifest.json", uniq)
    for r in uniq:
        fetch(f"{XZFG}/front/law/detail?LawID={r['id']}")
    log(f"regs: {len(uniq)}")


def main():
    stages = sys.argv[1:] or ["laws", "regs", "jis"]
    os.makedirs(RAW, exist_ok=True)
    for s in stages:
        {"laws": stage_laws, "regs": stage_regs, "jis": stage_jis}[s]()


if __name__ == "__main__":
    main()
