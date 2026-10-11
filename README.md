# China (People's Republic of China) — legislation as Markdown

Part of [LawCodex](https://github.com/LawCodex): the legislation of every country as plain Markdown in git.

This repository holds, in Simplified Chinese (the official language of the texts):

- the **Constitution of the PRC** (中华人民共和国宪法, consolidated text) and its five amendments (宪法修正案);
- the **national laws in force** (法律) adopted by the National People's Congress and its Standing Committee,
  organised by the eight legal departments (法律部门) of the NPC's official list of laws in force;
- the **administrative regulations in force** (行政法规) of the State Council;
- the **judicial interpretations in force** (司法解释) held by the MOFCOM law database (a partial set, see below).

Retrieved: 2026-10-12. Reference list of laws: NPC *现行有效法律目录（303件）*, as of 2026-08-28
(close of the 24th session of the 14th NPC Standing Committee).

## Coverage

| Part | Directory | Files |
|---|---|---:|
| Constitution (consolidated, 2018) + amendments 1988, 1993, 1999, 2004, 2018 | `constitution/` | 6 |
| Laws — 宪法相关法 (constitution-related laws) | `laws/xianfa-xiangguanfa/` | 46 / 56 |
| Laws — 民法商法 (civil and commercial law) | `laws/minfa-shangfa/` | 24 / 24 |
| Laws — 行政法 (administrative law) | `laws/xingzhengfa/` | 61 / 75 |
| Laws — 经济法 (economic law) | `laws/jingjifa/` | 69 / 71 |
| Laws — 社会法 (social law) | `laws/shehuifa/` | 29 / 32 |
| Laws — 生态环境法 (ecological and environmental law) | `laws/shengtai-huanjingfa/` | 27 / 27 |
| Laws — 刑法 (criminal law) | `laws/xingfa/` | 6 / 7 |
| Laws — 诉讼与非诉讼程序法 (procedural law) | `laws/susong-yu-feisusong-chengxufa/` | 10 / 10 |
| **Laws total** | `laws/` | **272 / 302** |
| Administrative regulations in force (行政法规, 现行有效) | `administrative-regulations/<year>/` | 606 / 606 |
| Judicial interpretations in force (司法解释) | `judicial-interpretations/<year>/` | 199 |

"x / y" = files present / items in the official list. Three laws whose newest revision has been adopted but is
not yet in force also have the version currently in force as `<slug>--current.md` (农业法, 商标法, 监狱法).

### Not covered / known gaps

- **30 laws of the NPC list are missing** (mostly military, police and state-organ laws, and old NPCSC
  approval resolutions that the MOFCOM database does not carry). Their texts are on www.npc.gov.cn, but while
  this corpus was being built npc.gov.cn started answering every request with a JavaScript bot challenge
  ("请开启JavaScript并刷新该页"), which we do not circumvent. Missing:
  人民法院组织法, 人民检察院组织法, 全国人大常委会关于县级以下人民代表大会代表直接选举的若干规定,
  全国人大常委会关于在沿海港口城市设立海事法院的决定 (no online text found), 全国人民代表大会常务委员会议事规则,
  全国人大常委会关于批准中央军事委员会《关于授予军队离休干部中国人民解放军功勋荣誉章的规定》的决定,
  香港特别行政区驻军法, 澳门特别行政区驻军法, 英雄烈士保护法, 陆地国界法,
  全国人大常委会关于批准《国务院关于安置老弱病残干部的暂行办法》的决议,
  全国人大常委会关于批准《国务院关于老干部离职休养的暂行规定》的决议, 中国人民解放军军官军衔条例, 现役军官法,
  人民警察警衔条例, 人民警察法, 枪支管理法, 人民防空法, 防震减灾法, 国家情报法, 消防救援衔条例, 海警法,
  军人地位和权益保障法, 全国人大常委会关于中国人民解放军现役士兵衔级制度的决定,
  全国人大常委会关于批准《广东省经济特区条例》的决议, 耕地占用税法,
  全国人大常委会关于批准《国务院关于工人退休、退职的暂行办法》的决议,
  全国人大常委会关于批准《国务院关于职工探亲待遇的规定》的决议, 退役军人保障法, 反恐怖主义法.
- **Outdated texts** (front matter carries a `warning:`): 律师法 (2026 amendment), 注册会计师法 (2026 amendment),
  村民委员会组织法 (2025 amendment) and 中国人民解放军选举全国人民代表大会和县级以上地方各级人民代表大会代表的办法
  (2021 amendment). For these only the amending decision (修改决定) has been published online by the sources
  used, not a consolidated text; the file contains the latest consolidated text available.
- Annexes of the Hong Kong / Macao Basic Laws, flag and emblem drawings and other images are not reproduced
  (images are kept as links to the official URL where the source embeds them).
- **Judicial interpretations** are the subset held by the MOFCOM database (199 in force, mostly civil,
  commercial, IP, procedure and economic-crime matters). The Supreme People's Court / Supreme People's
  Procuratorate publish many more; they are not covered.
- Not covered at all: departmental rules (部门规章), local regulations (地方性法规), State Council normative
  documents (国务院规范性文件), treaties, Hong Kong / Macao / Taiwan law.

## Sources

| Part | Source | Notes |
|---|---|---|
| List of laws in force + legal departments | NPC, *现行有效法律目录（303件）*, <http://www.npc.gov.cn/npc/c2597/c5854/c5855/202609/P020260904396146393500.pdf> | official PDF, parsed by `cn_mulu.py` |
| Law texts (254 laws + 3 current versions) | 商务部 全球法规网 / MOFCOM *China Laws & Regulations* database, <https://policy.mofcom.gov.cn/claw/> | official database of the Ministry of Commerce; each record names its own source (mostly 中国人大网) |
| Constitution, amendments, 17 law texts | 中国人大网 (NPC website), <http://www.npc.gov.cn/> (incl. its legacy `zgrdw` archive) | used where MOFCOM lacks the law or has an older version |
| 1 law text (精神卫生法) | 中国政府网, <https://www.gov.cn/> | |
| Administrative regulations | 国家行政法规库 (State Council administrative regulations database, Ministry of Justice), <https://xzfg.moj.gov.cn/> | the official compilation under the 行政法规制定程序条例; also embedded at gov.cn/zhengce/xzfgk |
| Judicial interpretations | MOFCOM 全球法规网, 效力级别 = 司法解释 | |

**Not used: 国家法律法规数据库 (<https://flk.npc.gov.cn>).** It is the NPC's official database (with a JSON
API and DOCX downloads), but its robots.txt disallows all crawling and states
"禁止使用任何自动化工具、脚本、爬虫程序采集或复制网站数据" (any automated collection or copying is prohibited).
Using it would require the NPC Standing Committee General Office's consent. `sousuo.www.gov.cn` (gov.cn search)
is likewise disallowed by robots.txt and was not used.

## Format

One Markdown file per instrument with YAML front matter:

```yaml
title: "中华人民共和国民法典"       # official Chinese title (also the H1)
identifier: "中华人民共和国主席令第45号"   # promulgation order / document number when known
type: code                         # constitution | constitutional_amendment | code | act | decision | regulation | judicial_interpretation
category: "民法商法"                # NPC legal department (laws)
jurisdiction: cn
language: zh-Hans
date: 2020-05-28                   # original adoption / promulgation
last_amended: 2020-05-28           # date of the version reproduced
effective: 2021-01-01              # entry into force of that version
status: in_force                   # in_force | not_yet_in_force (adopted, takes effect at `effective`)
history: "2020年通过"              # adoption/amendment history from the NPC list
npc_list_no: "民法商法 1"           # position in the NPC list
source: "https://policy.mofcom.gov.cn/claw/clawContent.shtml?id=70524"
source_note: "..."                 # database used and the original source it cites
retrieved: 2026-10-12
```

The hierarchy 编 / 分编 / 章 / 节 is mapped to Markdown headings (`##` downwards, only the levels that occur in
the text), and each 条 (article) is a heading at the next level (bold label if deeper than `######`).
款 (paragraphs) are separate paragraphs and 项 / 目 (items "（一）", "1.") are kept as written. The
parenthesised adoption/amendment note at the top of each text is preserved. Tables become Markdown tables
(HTML when cells are merged). Tables of contents (目录) are dropped because the headings carry them.

File names are pinyin slugs of the title without the 中华人民共和国 prefix (e.g. `min-fa-dian.md`);
homophones get a numeric suffix (`jian-cha-guan-fa.md` = 检察官法, `jian-cha-guan-fa-2.md` = 监察官法).
Regulations and judicial interpretations are sharded by year of first promulgation / issue.

## Copyright

Under Article 5 of the Copyright Law of the PRC (著作权法), laws, regulations, resolutions, decisions and orders
of state organs and other documents of a legislative, administrative or judicial nature, and their official
translations, are not protected by copyright. The texts here are reproduced unchanged for non-commercial
reference; the formatting and scripts in this repository are offered under CC0. The authoritative texts are the
printed official editions (gazettes of the NPC Standing Committee, State Council and Supreme People's Court).

## Regenerating

```sh
python -m pip install -r scripts/requirements.txt
python scripts/cn_npc_index.py          # index of npc.gov.cn "法律文件" column -> _raw/cn/npc_index.json
python scripts/cn_fetch.py laws regs jis   # NPC list + MOFCOM laws/JIs + xzfg regulations (cached in _raw/cn/cache)
python scripts/cn_npc_fallback.py       # npc.gov.cn / gov.cn texts for laws missing or outdated in MOFCOM
                                        # (uses scripts/npc_law_urls.tsv for pages outside the indexed column)
CN_OFFLINE=1 python scripts/cn_convert.py laws regs jis   # write Markdown from the cache
```

Requests are sequential with a 1.5 s delay and a descriptive User-Agent; responses are cached under
`../_raw/cn/` so re-runs do not re-download. Bot-challenge pages are detected, never cached, and reported.
