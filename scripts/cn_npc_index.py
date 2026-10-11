"""Crawl the NPC website (www.npc.gov.cn) "权威发布 > 法律文件" column index and list every item.

Writes _raw/cn/npc_index.json: [{title, url, date}].
"""
import json
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cn_common import RAW, fetch  # noqa: E402

BASE = os.environ.get("NPC_COL", "http://www.npc.gov.cn/npc/c2/c12435/c12488/")


def main():
    items, seen = [], set()
    first = fetch(BASE, refresh=True)
    pages = [int(x) for x in re.findall(r"index_(\d+)\.html", first)]
    last = max(pages) if pages else 0
    for i in range(0, last + 1):
        url = BASE if i == 0 else f"{BASE}index_{i}.html"
        html = first if i == 0 else fetch(url, refresh=True)
        for m in re.finditer(r'<li[^>]*>.*?</li>', html, re.S):
            li = m.group(0)
            a = re.search(r'href="([^"]+)"[^>]*>([^<]+)</a>', li)
            if not a:
                continue
            href = urllib.parse.urljoin(url, a.group(1))
            if href in seen or not re.search(r"/t\d{8}_\d+\.html", href):
                continue
            seen.add(href)
            d = re.search(r"(\d{4}-\d{2}-\d{2})", li)
            items.append({"title": a.group(2).strip(), "url": href, "date": d.group(1) if d else None})
        print(i, len(items), file=sys.stderr)
    os.makedirs(RAW, exist_ok=True)
    with open(os.path.join(RAW, os.environ.get("NPC_OUT", "npc_index.json")), "w") as f:
        json.dump(items, f, ensure_ascii=False, indent=0)


if __name__ == "__main__":
    main()
