"""Shared helpers for the LawCodex China (cn) scripts: polite cached HTTP, slugs, front matter."""
import hashlib
import os
import re
import time
import urllib.parse

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.environ.get("CN_RAW", os.path.join(os.path.dirname(ROOT), "_raw", "cn"))
CACHE = os.path.join(RAW, "cache")
UA = "LawCodex/1.0 (+https://github.com/LawCodex)"
DELAY = float(os.environ.get("CN_DELAY", "1.5"))  # seconds between live requests (sequential)

_session = requests.Session()
_session.headers.update({"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
_last = [0.0]


class Blocked(Exception):
    """The server answered with a bot challenge (JavaScript check). We do not try to bypass these."""


CHALLENGE = (b"Please enable JavaScript and refresh the page", "请开启JavaScript并刷新该页".encode())


def is_challenge(data):
    return len(data) < 60000 and any(c in data for c in CHALLENGE) and b'id="Zoom"' not in data


def cache_path(url):
    p = urllib.parse.urlparse(url)
    h = hashlib.sha1(url.encode()).hexdigest()[:16]
    ext = os.path.splitext(p.path)[1] or ".html"
    if len(ext) > 6:
        ext = ".html"
    return os.path.join(CACHE, p.netloc, h + ext)


def fetch(url, binary=False, refresh=False, tries=5):
    """GET url with on-disk cache, a fixed delay between live requests and retry with backoff."""
    path = cache_path(url)
    if not refresh and os.path.exists(path) and os.path.getsize(path) > 0:
        with open(path, "rb") as f:
            data = f.read()
        if is_challenge(data):
            os.remove(path)
            return fetch(url, binary, refresh, tries)
        return data if binary else data.decode("utf-8", "replace")
    if os.environ.get("CN_OFFLINE") == "1":
        raise Blocked(url + " (not cached; CN_OFFLINE=1)")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    err = None
    for i in range(tries):
        wait = _last[0] + DELAY - time.time()
        if wait > 0:
            time.sleep(wait)
        try:
            r = _session.get(url, timeout=60)
            _last[0] = time.time()
            if r.status_code == 404:
                return None
            r.raise_for_status()
            data = r.content
            if is_challenge(data):
                raise Blocked(url)
            with open(path, "wb") as f:
                f.write(data)
            if binary:
                return data
            enc = r.encoding if r.encoding and r.encoding.lower() not in ("iso-8859-1",) else "utf-8"
            try:
                return data.decode(enc)
            except (LookupError, UnicodeDecodeError):
                return data.decode("utf-8", "replace")
        except requests.RequestException as e:
            _last[0] = time.time()
            err = e
            time.sleep(5 * (2 ** i))
    raise RuntimeError(f"failed {url}: {err}")


def slugify_zh(title, maxlen=90):
    from pypinyin import lazy_pinyin

    t = re.sub(r"^中华人民共和国", "", title)
    t = re.sub(r"[（(].*?[）)]", "", t) or t
    parts = []
    for tok in lazy_pinyin(t, errors=lambda s: [c for c in s]):
        tok = tok.lower()
        tok = re.sub(r"[^a-z0-9]+", "-", tok).strip("-")
        if tok:
            parts.append(tok)
    s = "-".join(parts)
    s = re.sub(r"-+", "-", s)
    if len(s) > maxlen:
        s = s[:maxlen].rsplit("-", 1)[0]
    return s or "untitled"


def yaml_str(s):
    s = str(s).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{s}"'


def front_matter(d):
    lines = ["---"]
    for k, v in d.items():
        if v is None or v == "":
            continue
        if isinstance(v, (list, tuple)):
            lines.append(f"{k}:")
            for x in v:
                lines.append(f"  - {yaml_str(x)}")
        elif k in ("date", "last_amended", "retrieved", "effective") and re.match(r"^\d{4}-\d{2}-\d{2}$", str(v)):
            lines.append(f"{k}: {v}")
        elif k in ("type", "jurisdiction", "language", "status"):
            lines.append(f"{k}: {v}")
        else:
            lines.append(f"{k}: {yaml_str(v)}")
    lines.append("---")
    return "\n".join(lines) + "\n"


CN_NUM = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def cn2int(s):
    """Convert a Chinese numeral like 一百二十三 to int (None if not parseable)."""
    if not s:
        return None
    if s.isdigit():
        return int(s)
    total, sec, num = 0, 0, 0
    units = {"十": 10, "百": 100, "千": 1000}
    for ch in s:
        if ch in CN_NUM:
            num = CN_NUM[ch]
        elif ch in units:
            sec += (num or 1) * units[ch]
            num = 0
        elif ch == "万":
            total += (sec + num) * 10000
            sec, num = 0, 0
        else:
            return None
    return total + sec + num
