"""Convert cached Chinese legislation pages (_raw/cn/cache) into LawCodex Markdown.

Usage: cn_convert.py [laws] [regs] [jis]
Reads the manifests written by cn_fetch.py / cn_npc_fallback.py; writes into the repo root.
"""
import datetime
import json
import os
import re
import sys
import urllib.parse

import lxml.html

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cn_common import RAW, ROOT, cn2int, fetch, front_matter, slugify_zh  # noqa: E402

TODAY = datetime.date.today().isoformat()
RETRIEVED = os.environ.get("CN_RETRIEVED", TODAY)
MOF = "https://policy.mofcom.gov.cn"
XZFG = "https://xzfg.moj.gov.cn"

CAT_DIRS = {
    "宪法相关法": "xianfa-xiangguanfa",
    "民法商法": "minfa-shangfa",
    "行政法": "xingzhengfa",
    "经济法": "jingjifa",
    "社会法": "shehuifa",
    "生态环境法": "shengtai-huanjingfa",
    "刑法": "xingfa",
    "诉讼与非诉讼程序法": "susong-yu-feisusong-chengxufa",
}

NUM = "零〇一二三四五六七八九十百千两0-9０-９"
RE_HEAD = re.compile(rf"^第([{NUM}]+)(编|分编|章|节)(?:[\s　]+(.*)|([^\s　].{{0,30}}))?$")
RE_ART = re.compile(rf"^(第[{NUM}]+条(?:之[{NUM}]+)?)(?:[\s　]+|$)(.*)$", re.S)
RE_ART_NS = re.compile(rf"^(第([{NUM}]+)条(之[{NUM}]+)?)([^\s　].*)$", re.S)
RE_ART_LOOSE = re.compile(rf"^(?:@@[\s　]*)?第([{NUM}]+)(?:[\s　]*条|(?=[\s　]))(之[{NUM}]+)?[\s　]*(.+)$", re.S)
RE_ANNEX = re.compile(r"^(附件|附表|附录)[一二三四五六七八九十\d]*(?:[：:　\s].{0,60})?$")
BLOCK_TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "center", "pre", "blockquote", "dd", "dt"}
LEVEL_KEYS = ["编", "分编", "章", "节"]


# ------------------------------------------------------------------ HTML -> blocks
def norm_ws(s):
    s = s.replace("\xa0", " ").replace("​", "").replace("﻿", "").replace("\r", "")
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip(" \t\n　")


def render_table(tbl, base):
    rows = []
    complex_ = False
    for tr in tbl.iter("tr"):
        cells = []
        for td in tr:
            if td.tag not in ("td", "th"):
                continue
            if int(td.get("rowspan", "1") or 1) > 1 or int(td.get("colspan", "1") or 1) > 1:
                complex_ = True
            txt = "\n".join(norm_ws(x) for x in td.itertext())
            txt = re.sub(r"\n+", "<br>", txt.strip("\n")).strip()
            cells.append((td.get("rowspan"), td.get("colspan"), txt))
        if cells:
            rows.append(cells)
    if not rows:
        return None
    if not complex_:
        n = max(len(r) for r in rows)
        out = []
        for i, r in enumerate(rows):
            vals = [c[2].replace("|", "\\|") for c in r] + [""] * (n - len(r))
            out.append("| " + " | ".join(vals) + " |")
            if i == 0:
                out.append("|" + " --- |" * n)
        return "\n".join(out)
    out = ["<table>"]
    for r in rows:
        tds = []
        for rs, cs, txt in r:
            attrs = (f' rowspan="{rs}"' if rs and rs != "1" else "") + (f' colspan="{cs}"' if cs and cs != "1" else "")
            tds.append(f"<td{attrs}>{txt}</td>")
        out.append("<tr>" + "".join(tds) + "</tr>")
    out.append("</table>")
    return "\n".join(out)


def html_blocks(el, base):
    """Flatten an HTML content element into a list of text blocks (paragraphs / tables / image links)."""
    blocks = []
    for br in el.iter("br"):
        br.tail = "\n" + (br.tail or "")

    def text_of(e):
        parts = []
        for node in e.iter():
            if node.tag == "img":
                src = node.get("src", "")
                if src and not src.startswith("data:"):
                    parts.append(f"[图片]({urllib.parse.urljoin(base, src)})")
            if node is e:
                parts.append(node.text or "")
            else:
                if node.tag in ("script", "style"):
                    continue
                parts.append(node.text or "")
            if node is not e:
                parts.append(node.tail or "")
        return "".join(parts)

    def walk(e):
        if not isinstance(e.tag, str) or e.tag in ("script", "style"):
            return
        if e.tag == "table":
            t = render_table(e, base)
            if t:
                blocks.append(("table", t))
            return
        has_block_child = any(isinstance(c.tag, str) and (c.tag in BLOCK_TAGS or c.tag in ("div", "table", "section", "ul", "ol"))
                              for c in e.iterdescendants())
        if e.tag in BLOCK_TAGS or not has_block_child:
            txt = "".join(lxml.html.tostring(e, method="text", encoding="unicode", with_tail=False))
            imgs = [i.get("src", "") for i in e.iter("img")]
            for line in txt.split("\n"):
                line = norm_ws(line)
                if line:
                    blocks.append(("p", line))
            for src in imgs:
                if src and not src.startswith("data:"):
                    blocks.append(("p", f"[图片]({urllib.parse.urljoin(base, src)})"))
            return
        if e.text and norm_ws(e.text):
            blocks.append(("p", norm_ws(e.text)))
        for c in e:
            walk(c)
            if c.tail and norm_ws(c.tail):
                blocks.append(("p", norm_ws(c.tail)))

    walk(el)
    return blocks


# ------------------------------------------------------------------ blocks -> markdown
def squash(s):
    """Remove typographic spacing inside short headings: '总　　则' -> '总则'."""
    return re.sub(r"(?<=[一-鿿])[\s　]+(?=[一-鿿])", "", s)


def head_label(m):
    num, kind = m.group(1), m.group(2)
    rest = (m.group(3) or m.group(4) or "").strip()
    return f"第{num}{kind}", squash(rest)


def is_heading_block(t, structure=True):
    if not structure or len(t) > 45 or "。" in t or "；" in t:
        return None
    m = RE_HEAD.match(t)
    return m


def md_escape(line):
    if re.match(r"^(#|>|[-+*] |\d+[.)] |=+$|-{3,}$)", line):
        return "\\" + line
    return line


def to_markdown(title, blocks, structure=True):
    norm_title = re.sub(r"[\s　（）()]", "", title)
    # drop leading title repeats / empties
    out_blocks = []
    i = 0
    while i < len(blocks) and blocks[i][0] == "p" and (
            re.sub(r"[\s　（）()]", "", blocks[i][1]) in (norm_title, "") or
            re.fullmatch(r"新华社.{0,20}电", blocks[i][1]) or
            norm_title.startswith(re.sub(r"[\s　（）()]", "", blocks[i][1])) and len(blocks[i][1]) > 4 or
            re.sub(r"[\s　（）()]", "", blocks[i][1]).startswith(norm_title) and
            re.fullmatch(r"\d{4}年?(修正|修订|修改)?(文本)?", re.sub(r"[\s　（）()]", "", blocks[i][1])[len(norm_title):])):
        i += 1
    blocks = blocks[i:]
    # strip table of contents
    toc, j = [], 0
    for k, (kind, t) in enumerate(blocks[:8]):
        if kind == "p" and re.fullmatch(r"目[\s　]*录", t):
            j = k + 1
            first = None
            while j < len(blocks):
                kd, tt = blocks[j]
                if kd != "p":
                    break
                if tt.startswith(("（", "(")) or len(tt) > 60 or "。" in tt:
                    break
                key = squash(tt)
                if first is None:
                    first = key
                elif key == first:
                    break
                toc.append(tt)
                j += 1
            blocks = blocks[:k] + blocks[j:]
            break
    present = set()
    for kind, t in blocks:
        if kind == "p":
            m = is_heading_block(t, structure)
            if m:
                present.add(m.group(2))
    levels = {k: 2 + n for n, k in enumerate([k for k in LEVEL_KEYS if k in present])}
    art_level = 2 + len(levels)
    lines = []

    def emit(s):
        lines.append(s)
        lines.append("")

    articles = 0
    spaced = sum(1 for kind, t in blocks if kind == "p" and RE_ART.match(t))
    nospace = True
    expect = [1]

    def art_match(t):
        m = RE_ART.match(t)
        if m or not nospace:
            return m
        m2 = RE_ART_NS.match(t)
        if not m2:
            m3 = RE_ART_LOOSE.match(t)
            if m3 and cn2int(m3.group(1)) == expect[0]:
                return m3
            return None
        num = cn2int(m2.group(2))
        if num is None or num != expect[0] or m2.group(4)[:1] in "的、，之":
            return None
        return m2

    for kind, t in blocks:
        if kind == "table":
            emit(t)
            continue
        m = is_heading_block(t, structure)
        if m:
            lab, rest = head_label(m)
            emit("#" * levels[m.group(2)] + " " + (f"{lab} {rest}" if rest else lab))
            continue
        if re.fullmatch(r"序[\s　]*言", t):
            emit("## 序言")
            continue
        if RE_ANNEX.match(t) and "。" not in t and articles > 0:
            emit("## " + squash(t) if len(t) < 12 else "## " + t)
            continue
        ma = art_match(t)
        if ma:
            articles += 1
            if ma.re is RE_ART_LOOSE:
                label, body = f"第{ma.group(1)}条" + (ma.group(2) or ""), ma.group(3).strip()
                expect[0] += 1
            elif ma.re is RE_ART_NS:
                label, body = ma.group(1), ma.group(4).strip()
                expect[0] += 1
            else:
                label, body = ma.group(1), ma.group(2).strip()
                n_ = cn2int(re.sub(r"^第|条.*$", "", label))
                if n_:
                    expect[0] = n_ + 1
            if art_level <= 6:
                emit("#" * art_level + " " + label)
                if body:
                    emit(md_escape(body))
            else:
                emit(f"**{label}**" + ("　" + body if body else ""))
            continue
        emit(md_escape(t))
    return "\n".join(lines).rstrip() + "\n", articles, toc


# ------------------------------------------------------------------ source parsers
def parse_mofcom(cid):
    url = f"{MOF}/claw/clawContent.shtml?id={cid}"
    html = fetch(url)
    doc = lxml.html.fromstring(html)
    meta = {}
    for td in doc.xpath('//table[@class="table_01"]//td'):
        sp = td.find("span")
        if sp is None:
            continue
        k = norm_ws(sp.text_content()).strip("【】")
        v = norm_ws(td.text_content().replace(sp.text_content(), ""))
        meta[k] = re.sub(r"\s*;\s*", "; ", v)
    src = doc.xpath('//h3[@class="tit_09"]//em')
    meta["信息来源"] = norm_ws(src[0].text_content()) if src else None
    t = doc.xpath('//h2[@class="tit_08"]')
    meta["title"] = norm_ws(t[0].text_content()) if t else None
    art = doc.xpath('//div[@class="article"]')
    blocks = html_blocks(art[0], url) if art else []
    return url, meta, blocks


def parse_xzfg(lid):
    url = f"{XZFG}/front/law/detail?LawID={lid}"
    html = fetch(url)
    doc = lxml.html.fromstring(html)
    ch = doc.xpath('//div[@class="law-chapter"]')
    blocks = html_blocks(ch[0], url) if ch else []
    t = doc.xpath('//div[@class="text-title"]')
    return url, (norm_ws(t[0].text_content()) if t else None), blocks


def parse_npc(url):
    html = fetch(url)
    doc = lxml.html.fromstring(html)
    z = doc.xpath('//div[@id="Zoom"]') or doc.xpath('//div[@id="UCAP-CONTENT"]')
    blocks = html_blocks(z[0], url) if z else []
    t = doc.xpath('//div[@class="tit"]/h1')
    return url, (norm_ws(t[0].text_content()) if t else None), blocks


def history_note(blocks):
    for kind, t in blocks[:6]:
        if kind == "p" and t.startswith(("（", "(")) and re.search(r"(通过|公布|发布|修正|修订)", t):
            return t
    return None


def first_date(s):
    if not s:
        return None
    m = re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", s)
    return "%s-%02d-%02d" % (m.group(1), int(m.group(2)), int(m.group(3))) if m else None


def write(path, fm, title, body):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(front_matter(fm))
        f.write("\n# " + title + "\n\n")
        f.write(body)


def unique(path, used):
    base, ext = os.path.splitext(path)
    p, n = path, 2
    while p in used:
        p = f"{base}-{n}{ext}"
        n += 1
    used.add(p)
    return p


def status_for(effective, listed):
    if listed == "尚未生效" or (effective and effective > TODAY):
        return "not_yet_in_force"
    return "in_force"


# ------------------------------------------------------------------ stages
def law_type(title):
    if title.endswith("法典"):
        return "code"
    if "决定" in title[-6:] or "决议" in title[-6:]:
        return "decision"
    if title.endswith(("条例", "规定", "办法", "规则")):
        return "act"
    return "act"


def conv_laws(stats, used):
    man = json.load(open(os.path.join(RAW, "laws_manifest.json")))
    fb_path = os.path.join(RAW, "npc_fallback.json")
    fallback = json.load(open(fb_path)) if os.path.exists(fb_path) else {}
    rows = []
    entries = man["matched"] + man["missing"]
    for e in entries:
        title = e["title"]
        fb = fallback.get(title)
        rec = e.get("mofcom")
        use_npc = fb and (not rec or e.get("stale"))
        if e["category"] == "宪法":
            continue  # handled by conv_constitution
        if use_npc:
            url, pt, blocks = parse_npc(fb["url"])
            meta = {}
            source_note = "中国人大网 (www.npc.gov.cn)"
            last = fb.get("date")
            eff = None
            docno = None
            listed = None
        elif rec:
            url, meta, blocks = parse_mofcom(rec["id"])
            source_note = "商务部全球法规网 (policy.mofcom.gov.cn); 信息来源: " + (meta.get("信息来源") or "?")
            last = meta.get("发布日期") or rec.get("published")
            eff = meta.get("实施日期") or rec.get("effective")
            docno = meta.get("发布文号") or rec.get("docno")
            listed = meta.get("时效状态") or rec.get("status")
        else:
            stats["missing"].append(title)
            continue
        body, nart, _ = to_markdown(title, blocks)
        if len(body) < 200:
            stats["empty"].append((title, url))
            continue
        hist = history_note(blocks)
        slug = slugify_zh(title)
        path = unique(os.path.join(ROOT, "laws", CAT_DIRS[e["category"]], slug + ".md"), used)
        fm = {
            "title": title,
            "identifier": docno,
            "type": law_type(title),
            "category": e["category"],
            "jurisdiction": "cn",
            "language": "zh-Hans",
            "date": first_date(hist) or first_date(e.get("history")),
            "last_amended": last,
            "effective": eff,
            "status": status_for(eff, listed),
            "history": e.get("history") or None,
            "npc_list_no": f"{e['category']} {e['no']}",
            "source": url,
            "source_note": source_note,
            "retrieved": RETRIEVED,
        }
        if e.get("stale") and not use_npc:
            fm["warning"] = (f"Source text is older than the latest amendment listed by the NPC "
                             f"({e.get('last_year')}); a newer consolidated text was not available from the sources used.")
        write(path, fm, title, body)
        stats["laws"][e["category"]] = stats["laws"].get(e["category"], 0) + 1
        rows.append((e["category"], title, os.path.relpath(path, ROOT), nart))
        if e.get("mofcom_current"):
            c = e["mofcom_current"]
            url2, meta2, blocks2 = parse_mofcom(c["id"])
            body2, nart2, _ = to_markdown(title, blocks2)
            if len(body2) > 200:
                p2 = unique(os.path.join(ROOT, "laws", CAT_DIRS[e["category"]], slug + "--current.md"), used)
                fm2 = dict(fm, last_amended=meta2.get("发布日期") or c.get("published"),
                           effective=meta2.get("实施日期") or c.get("effective"),
                           identifier=meta2.get("发布文号") or c.get("docno"),
                           status="in_force", source=url2,
                           date=first_date(history_note(blocks2)) or fm["date"],
                           note=f"Version currently in force; superseded on {eff} by {os.path.basename(path)}.")
                fm2.pop("warning", None)
                write(p2, fm2, title, body2)
                stats["current_versions"] += 1
    stats["law_rows"] = rows


def conv_constitution(stats, used):
    fb_path = os.path.join(RAW, "npc_fallback.json")
    fallback = json.load(open(fb_path)) if os.path.exists(fb_path) else {}
    for key, fn, typ in [("中华人民共和国宪法", "xianfa.md", "constitution")] + [
            (f"中华人民共和国宪法修正案（{y}年）", f"xianfa-xiuzhengan-{y}.md", "constitutional_amendment")
            for y in (1988, 1993, 1999, 2004, 2018)]:
        fb = fallback.get(key)
        if not fb:
            stats["missing"].append(key)
            continue
        url, pt, blocks = parse_npc(fb["url"])
        body, nart, _ = to_markdown(key, blocks, structure=(typ == "constitution"))
        hist = history_note(blocks)
        alld = re.findall(r"(\d{4})年(\d{1,2})月(\d{1,2})日", "".join(t for _, t in blocks[:8]))
        last = max(("%s-%02d-%02d" % (y, int(m), int(d)) for y, m, d in alld), default=None)
        fb["last_amended"] = last
        fm = {"title": key, "type": typ, "category": "宪法", "jurisdiction": "cn", "language": "zh-Hans",
              "date": first_date(hist) or fb.get("enacted"), "last_amended": fb.get("last_amended"),
              "status": "in_force", "source": url, "source_note": "中国人大网 (www.npc.gov.cn)",
              "retrieved": RETRIEVED}
        path = os.path.join(ROOT, "constitution", fn)
        used.add(path)
        write(path, fm, key, body)
        stats["constitution"] += 1


def conv_regs(stats, used):
    man = json.load(open(os.path.join(RAW, "regs_manifest.json")))
    for r in man:
        url, pt, blocks = parse_xzfg(r["id"])
        title = r["title"]
        body, nart, _ = to_markdown(title, blocks)
        if len(body) < 100:
            stats["empty"].append((title, url))
            continue
        hist = history_note(blocks)
        dates = [h["date"] for h in r.get("history", [])]
        first = min(dates) if dates else (first_date(hist) or r["published"])
        orders = re.findall(r"国务院令第\s*(\d+)\s*号", hist or "")
        ident = f"国务院令第{orders[-1]}号" if orders else None
        if not ident:
            docs = re.findall(r"([\u4e00-\u9fff]{1,6}[〔\[［(（]\d{4}[〕\]］)）]\d+号)", hist or "")
            ident = docs[-1] if docs else None
        year = (first or r["published"] or "0000")[:4]
        path = unique(os.path.join(ROOT, "administrative-regulations", year, slugify_zh(title) + ".md"), used)
        fm = {
            "title": title, "identifier": ident, "xzfg_law_id": str(r["id"]), "type": "regulation",
            "jurisdiction": "cn", "language": "zh-Hans", "date": first, "last_amended": r["published"],
            "effective": r["effective"], "status": status_for(r["effective"], None),
            "source": url, "source_note": "国家行政法规库 (xzfg.moj.gov.cn), 司法部", "retrieved": RETRIEVED,
        }
        write(path, fm, title, body)
        stats["regs"] += 1


def conv_jis(stats, used):
    man = json.load(open(os.path.join(RAW, "jis_manifest.json")))
    for r in man:
        url, meta, blocks = parse_mofcom(r["id"])
        title = re.sub(r"（\d{4}(修正|修订)?）$", "", r["title"])
        body, nart, _ = to_markdown(r["title"], blocks)
        if len(body) < 100:
            stats["empty"].append((r["title"], url))
            continue
        pub = meta.get("发布日期") or r["published"]
        year = (pub or "0000")[:4]
        path = unique(os.path.join(ROOT, "judicial-interpretations", year, slugify_zh(title) + ".md"), used)
        eff = meta.get("实施日期") or r["effective"]
        fm = {
            "title": r["title"], "identifier": meta.get("发布文号") or r["docno"], "type": "judicial_interpretation",
            "issuer": meta.get("发布部门"), "jurisdiction": "cn", "language": "zh-Hans",
            "date": pub, "effective": eff,
            "status": status_for(eff, meta.get("时效状态") or r["status"]),
            "source": url,
            "source_note": "商务部全球法规网 (policy.mofcom.gov.cn); 信息来源: " + (meta.get("信息来源") or "?"),
            "retrieved": RETRIEVED,
        }
        write(path, fm, r["title"], body)
        stats["jis"] += 1


def main():
    stages = sys.argv[1:] or ["laws", "regs", "jis"]
    stats = {"laws": {}, "regs": 0, "jis": 0, "constitution": 0, "current_versions": 0, "missing": [], "empty": []}
    used = set()
    if "laws" in stages:
        conv_constitution(stats, used)
        conv_laws(stats, used)
    if "regs" in stages:
        conv_regs(stats, used)
    if "jis" in stages:
        conv_jis(stats, used)
    rows = stats.pop("law_rows", None)
    print(json.dumps(stats, ensure_ascii=False, indent=1))
    with open(os.path.join(RAW, "convert_stats.json"), "w") as f:
        json.dump(stats, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
