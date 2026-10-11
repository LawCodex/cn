"""Parse the NPC "现行有效法律目录" (list of laws in force, by legal department) PDF.

Usage: cn_mulu.py <pdf-url>
Writes _raw/cn/mulu.json: [{no, category, title, history, last_year, annexes}].
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cn_common import RAW, fetch  # noqa: E402

DEFAULT_URL = "http://www.npc.gov.cn/npc/c2597/c5854/c5855/202609/P020260904396146393500.pdf"
CATS = ["宪法相关法", "民法商法", "行政法", "经济法", "社会法", "生态环境法", "刑法", "诉讼与非诉讼程序法"]


def main():
    import pypdf

    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    data = fetch(url, binary=True)
    r = pypdf.PdfReader(io.BytesIO(data))
    text = "\n".join(p.extract_text() for p in r.pages)
    head = text[:300]
    m = re.search(r"现行有效法律目录（(\d+)\s*件）", head)
    total = int(m.group(1)) if m else None
    asof = re.search(r"截至\s*(\d{4})\s*年\s*(\d+)\s*月\s*(\d+)\s*日", re.sub(r"\s+", " ", head))
    lines = [ln.strip() for ln in text.split("\n")]
    lines = [ln for ln in lines if ln and not re.fullmatch(r"\d{1,3}", ln)]
    # join everything, then split on item / category markers
    blob = "".join(lines)
    blob = re.sub(r"\s+", "", blob)
    entries = []
    # constitution block
    cat = None
    pos = 0
    tokens = re.split(r"((?:" + "|".join(CATS) + r")（\d+件）|\d{1,3}．)", blob)
    pre = tokens[0]
    for c in re.findall(r"(中华人民共和国宪法(?:修正案)?（\d{4}年）)", pre):
        entries.append({"no": None, "category": "宪法", "title": c, "history": "", "last_year": int(re.search(r"\d{4}", c).group())})
    i = 1
    no = None
    while i < len(tokens):
        tok = tokens[i]
        body = tokens[i + 1] if i + 1 < len(tokens) else ""
        i += 2
        mc = re.fullmatch(r"(.+?)（\d+件）", tok)
        if mc and mc.group(1) in CATS:
            cat = mc.group(1)
            continue
        no = int(tok[:-1])
        annexes = []
        mm = re.search(r"附件", body)
        main = body
        if mm:
            main, rest = body[: mm.start()], body[mm.start():]
            annexes = [a for a in re.split(r"(?=附件)", rest) if a]
        # history = last parenthesised group containing 通过/修正/修订
        hm = re.search(r"（([^（）]*?(?:通过|修正|修订|决定|批准)[^（）]*)）$", main)
        if hm:
            title, history = main[: hm.start()], hm.group(1)
        else:
            title, history = main, ""
        years = [int(y) for y in re.findall(r"(\d{4})年", history)]
        entries.append({"no": no, "category": cat, "title": title, "history": history,
                        "last_year": max(years) if years else None, "annexes": annexes})
    out = {"source": url, "total": total,
           "as_of": "%s-%02d-%02d" % (asof.group(1), int(asof.group(2)), int(asof.group(3))) if asof else None,
           "entries": entries}
    with open(os.path.join(RAW, "mulu.json"), "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    from collections import Counter
    print(total, out["as_of"], len(entries), Counter(e["category"] for e in entries))


if __name__ == "__main__":
    main()
