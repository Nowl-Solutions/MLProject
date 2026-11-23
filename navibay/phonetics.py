"""
Pure-Python Thai Phonetic, Syllable, and Whole-Song Rhyme Analyzer for NaviBay.

Covers:
  - Standard Thai syllables + PyThaiNLP dictionary DP segmentation
  - English & Pali/Sanskrit loanwords (clusters, multi-letter karan, silent final ิ/ุ)
  - Complex leading consonants (อักษรนำ / พยางค์ลดรูป อะ), false clusters (ควบกล้ำไม่แท้), ร หัน (รร), ฤ/ฤๅ
  - Common regional dialects (Isan, Northern/Kam Mueang, Southern)
  - All 8 rhyme/sound relation types + stanza schemes (AABB/ABAB) + 40 dense song features
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

from pythainlp.tokenize import word_tokenize

O = r"(?P<o>ห[งญนมยรลว]|อย|[กขคตปพผบฟดท][รลว]|[สศซจ]ร|ส[ตปมกน]|[ก-ฮ])"
F = r"(?P<c>[ก-ฮ])?"

CODA_GROUPS = {
    "k": "กขคฆ",
    "t": "ดจชซฎฏฐฑฒตถทธศษส",
    "p": "บปพฟภ",
    "ng": "ง",
    "n": "นณญรลฬ",
    "m": "ม",
    "y": "ย",
    "w": "ว",
}
ONSET_GROUPS = {
    "k": "ก", "kh": "ขฃคฅฆ", "ng": "ง", "ch": "ฉชฌ", "c": "จ", "s": "ซศษส",
    "y": "ญย", "d": "ฎด", "t": "ฏต", "th": "ฐฑฒถทธ", "n": "ณน", "b": "บ",
    "p": "ป", "ph": "ผพภ", "f": "ฝฟ", "m": "ม", "r": "ร", "l": "ลฬ",
    "w": "ว", "h": "หฮ", "zero": "อ",
}

CODA_MAP = {ch: k for k, chars in CODA_GROUPS.items() for ch in chars}
ONSET_MAP = {ch: k for k, chars in ONSET_GROUPS.items() for ch in chars}

RAW_RULES = [
    ("เ" + O + "ีย" + F, "ia", "long", None),
    ("เ" + O + "ือ" + F, "uea", "long", None),
    (O + "ัว" + F, "ua", "long", None),
    (O + r"ว(?P<c>[ก-ฮ])", "ua", "long", None),
    ("เ" + O + "า", "a", "short", "w"),
    ("[ใไ]" + O + "ย", "a", "short", "y"),
    ("[ใไ]" + O, "a", "short", "y"),
    (O + "ำ", "a", "short", "m"),
    (O + r"รร(?P<c>[ก-ฮ])", "a", "short", None),
    (O + "รร", "a", "short", "n"),
    ("เ" + O + "อะ", "oe", "short", None),
    ("เ" + O + "อ" + F, "oe", "long", None),
    ("เ" + O + r"ิ(?P<c>[ก-ฮ])", "oe", "long", None),
    ("เ" + O + "ย", "oe", "long", "y"),
    ("เ" + O + "็" + F, "e", "short", None),
    ("เ" + O + "ะ", "e", "short", None),
    ("เ" + O + F, "e", "long", None),
    ("แ" + O + "็" + F, "ae", "short", None),
    ("แ" + O + "ะ", "ae", "short", None),
    ("แ" + O + F, "ae", "long", None),
    ("โ" + O + "ะ", "o", "short", None),
    ("โ" + O + F, "o", "long", None),
    ("เ" + O + "าะ", "aw", "short", None),
    (O + "็อ" + F, "aw", "short", None),
    (O + "อ" + F, "aw", "long", None),
    (O + "ั" + F, "a", "short", None),
    (O + "ะ", "a", "short", None),
    (O + "า" + F, "a", "long", None),
    (O + "ิ" + F, "i", "short", None),
    (O + "ี" + F, "i", "long", None),
    (O + "ึ" + F, "ue", "short", None),
    (O + "ือ", "ue", "long", None),
    (O + r"ื(?P<c>[ก-ฮ])", "ue", "long", None),
    (O + "ุ" + F, "u", "short", None),
    (O + "ู" + F, "u", "long", None),
    (O + "็" + F, "o", "short", None),
    (O + r"(?P<c>[ก-ฮ])", "o", "short", None),
    (r"(?P<o>ฤ)ๅ", "ue", "long", None),
    (r"(?P<o>ฤ)", "ue", "short", None),
]
RULES = [(re.compile("^" + pat + "$"), v, l, forced) for pat, v, l, forced in RAW_RULES]

EXCEPTIONS: dict[str, tuple[str, str, str, str]] = {
    "ก็": ("aw", "short", "", "k"), "บ่": ("aw", "short", "", "b"), "เธอ": ("oe", "long", "", "th"),
    "ทราย": ("a", "long", "y", "s"), "ทราบ": ("a", "long", "p", "s"), "ทรง": ("o", "short", "ng", "s"),
    "ทรัพย์": ("a", "short", "p", "s"), "ทรวง": ("ua", "long", "ng", "s"), "ทราม": ("a", "long", "m", "s"),
    "แทรก": ("ae", "long", "k", "s"), "ทรุด": ("u", "short", "t", "s"), "โทรม": ("o", "long", "m", "s"),
    "จริง": ("i", "short", "ng", "c"), "ไซร้": ("a", "short", "y", "s"),
    "รัก": ("a", "short", "k", "r"), "ฉัน": ("a", "short", "n", "ch"), "ฝัน": ("a", "short", "n", "f"),
    "กัน": ("a", "short", "n", "k"), "วัน": ("a", "short", "n", "w"), "เงิน": ("oe", "long", "n", "ng"),
    "เดิน": ("oe", "long", "n", "d"), "เกิน": ("oe", "long", "n", "k"), "เป็น": ("e", "short", "n", "p"),
    "เพชร": ("e", "short", "t", "ph"), "เหตุ": ("e", "long", "t", "h"), "ชาติ": ("a", "long", "t", "ch"),
    "รถ": ("o", "short", "t", "r"), "กล": ("o", "short", "n", "k"), "คน": ("o", "short", "n", "kh"),
    "ผล": ("o", "short", "n", "ph"), "ไทย": ("a", "short", "y", "th"),
    "ฤดู": ("ue", "short", "", "r"), "ฤทัย": ("ue", "short", "", "r"),
    "กะ": ("a", "short", "", "k"), "บ้อ": ("aw", "short", "", "b"), "น้อ": ("aw", "long", "", "n"),
    "เด้อ": ("oe", "long", "", "d"), "เด้": ("e", "long", "", "d"), "ฮู้": ("u", "long", "", "h"),
    "คึด": ("ue", "short", "t", "kh"), "ถืก": ("ue", "long", "k", "th"), "เพิ่น": ("oe", "long", "n", "ph"),
    "เบิ่ด": ("oe", "short", "t", "b"), "เว่า": ("a", "short", "w", "w"), "ซ่อย": ("aw", "long", "y", "s"),
    "แซ่บ": ("ae", "long", "p", "s"), "เปิ้น": ("oe", "long", "n", "p"), "ปิ๊ก": ("i", "short", "k", "p"),
    "แต๊": ("ae", "long", "", "t"), "หรอย": ("aw", "long", "y", "r"), "พรือ": ("ue", "long", "", "ph-r"),
    "หม้าย": ("a", "long", "y", "m"), "หนัด": ("a", "short", "t", "n"),
    "ป๊อป": ("aw", "short", "p", "p"), "สต็อป": ("aw", "short", "p", "s-t"),
    "สไตล์": ("a", "short", "y", "s-t"), "สไมล์": ("a", "short", "y", "s-m"),
    "เทรนด์": ("e", "short", "n", "th-r"), "สเปซ": ("e", "long", "t", "s-p"),
    "ดริ้งก์": ("i", "short", "ng", "d-r"), "แทร็ป": ("ae", "short", "p", "th-r"),
    "แร็ป": ("ae", "short", "p", "r"), "ฟีล": ("i", "long", "n", "f"), "กรูฟ": ("u", "long", "p", "k-r"),
}

EXTRA_LEXICON = {
    "บ่", "ฮู้", "ใด๋", "ไผ", "เด้อ", "เด้", "น้อ", "คึด", "ฮอด", "ถืก", "เพิ่น", "ถิ่ม", "ฮ้อ", "บ้อ",
    "ถ่า", "เอิ้น", "เบิ่ด", "เว่า", "ซ่อย", "ส่อย", "เมือ", "แซ่บ", "เบิ่ง", "แม่น", "มัก", "เฮ็ด",
    "จั่ง", "จัง", "ส่ำ", "ซำ", "ตั๋ว", "ปาน", "สิ", "แหน่", "พ้อ", "มื้อ", "หยัง", "ข่อย", "เซา",
    "ย่าน", "ม่วน", "คัก", "อ้าย", "ฮัก", "เฮา", "เปิ้น", "กิ๋น", "แอ่ว", "อู้", "ปิ๊ก", "เน้อ", "แต๊",
    "ใจ๋", "ไป๋", "ไผ๋", "หรอย", "แหลง", "พรือ", "หม้าย", "หนัด", "หิด", "ไหร", "เทือน",
    "ไทย", "ทรง", "สร้าง", "เศร้า", "สร้อย", "เสร็จ", "ศรี", "จริง", "ไซร้", "ทรัพย์",
    "จันทร์", "ศาสตร์", "วรรค", "วรรค์", "ธรรม", "กรรม", "พรรค",
    "สไตล์", "สไมล์", "ป๊อป", "สต็อป", "ดรอป", "บล็อก", "ล็อก", "ช็อก", "ร็อก",
    "เทรนด์", "เฟรนด์", "แบรนด์", "แกรนด์", "สเปซ", "เพลส", "ดริ้งก์", "แบงก์",
    "แทร็ป", "แร็ป", "ฟีล", "ชิล", "มูฟ", "กรูฟ", "พรูฟ", "เคลียร์", "เชียร์", "เบียร์", "เกียร์",
    "ทัวร์", "ชัวร์", "เวอร์", "เว่อร์", "เบลอ", "เทิร์น", "เบิร์น", "เวิร์ก", "เซิร์ฟ",
    "การ์ด", "ชาร์จ", "มาร์ก", "พาร์ต", "สตาร์ต", "สมาร์ต", "แมตช์", "เซนส์", "เอนด์",
    "เท็กซ์", "เน็กซ์", "ฟิกซ์", "มิกซ์", "ไวบ์", "ไลฟ์", "ไทม์", "ไนท์", "ไรท์", "ไฟล์", "ไลน์",
    "เซ็ต", "เน็ต", "เจ็ต", "เป๊ะ", "อัพ", "คัพ", "คลับ", "ผับ", "ซับ",
}

LEAD_CONS = set("กขคจฉชตถทปผพฝมศสอ")
RE_THAI_ONLY = re.compile(r"^[ก-๛]+$")
RE_WORD_LIKE = re.compile(r"[ก-๛a-z0-9]", re.IGNORECASE)
RE_TONE = re.compile(r"[่้๊๋]")
RE_KARAN2 = re.compile(r"(?:ทร|ตร|ดร|กษ|ษณ|ทย|รย)์")
RE_KARAN1 = re.compile(r"[ก-ฮ][ิุี]?์")
RE_SILENT_IU = re.compile(r"((?:[เแโ][ก-ฮ]|[ก-ฮ][าีูั])[ก-ฮ])[ิุ]$")
RE_NON_START = re.compile(r"[ะัาำิีึืุู็่้๊๋์]")
RE_H_LEAD = re.compile(r"^ห[งญนมยรลว]$")
RE_FALSE_S = re.compile(r"^[สศซ]ร$")
RE_HEADING = re.compile(r"^\s*\[([^\]]+)\]\s*$")
RE_ENG = re.compile(r"^[a-z]+$", re.IGNORECASE)
RE_NUM = re.compile(r"^\d+$")
RE_HAS_THAI = re.compile(r"[ก-๛]")
RE_BLANK_LINES = re.compile(r"\r?\n\s*\r?\n")

NAMES = {
    "vowel": "สัมผัสสระ",
    "onset": "สัมผัสอักษร",
    "coda": "เสียงตัวสะกดซ้ำ",
    "assonance": "เสียงสระซ้ำ",
    "near": "สัมผัสใกล้เคียง",
    "repeat": "คำ/พยางค์ซ้ำ",
    "multi": "สัมผัสหลายพยางค์",
    "phrase": "วรรคซ้ำ",
}

_sound_cache: dict[str, dict[str, str] | None] = {}
_syllable_cache: dict[str, list[dict[str, Any]]] = {}
_dictionary: set[str] = set()


def lead_sound(ch: str) -> dict[str, str]:
    onset = ONSET_MAP.get(ch, "zero")
    return {"vowel": "a", "length": "short", "coda": "", "onset": onset, "key": "a:short:", "near": "a:"}


def sound(text: str) -> dict[str, str] | None:
    if text in _sound_cache:
        return _sound_cache[text]
    raw_norm = text.replace("เเ", "แ").replace("\u0E4D\u0E32", "ำ")
    clean = RE_SILENT_IU.sub(r"\1", RE_KARAN1.sub("", RE_KARAN2.sub("", RE_TONE.sub("", raw_norm))))
    result: dict[str, str] | None = None
    exc = EXCEPTIONS.get(raw_norm) or EXCEPTIONS.get(clean)
    if exc:
        vowel, length, coda, onset = exc
        result = {"vowel": vowel, "length": length, "coda": coda, "onset": onset}
    elif RE_THAI_ONLY.match(clean):
        for rx, vowel, length, forced in RULES:
            m = rx.match(clean)
            if not m:
                continue
            onset = m.group("o")
            if RE_H_LEAD.match(onset):
                onset = onset[1:]
            elif onset == "อย":
                onset = "ย"
            elif RE_FALSE_S.match(onset):
                onset = "ซ"
            elif onset == "จร":
                onset = "จ"
            elif onset == "ฤ":
                onset = "ร"
            initial = ONSET_MAP.get(onset[0], "zero")
            c_char = m.groupdict().get("c") or " "
            coda = forced if forced is not None else CODA_MAP.get(c_char, "")
            result = {
                "vowel": vowel,
                "length": length,
                "coda": coda,
                "onset": initial + ("-" + onset[1:] if len(onset) > 1 else ""),
            }
            break
    if result is not None:
        result["key"] = f"{result['vowel']}:{result['length']}:{result['coda']}"
        result["near"] = f"{result['vowel']}:{result['coda']}"
    _sound_cache[text] = result
    return result


def rhyme(word: str) -> str | None:
    s = sound(word)
    return s["key"] if s else None


def set_dictionary(words_list: list[str]) -> None:
    global _dictionary
    _dictionary = {s for s in (*words_list, *EXTRA_LEXICON) if sound(s) is not None}
    _syllable_cache.clear()


def load_default_dictionary(base_dir: Path | None = None) -> list[str]:
    root = base_dir or Path(__file__).resolve().parent
    path = root / "dist/vendor/syllables-th.txt"
    items = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if RE_THAI_ONLY.match(line.strip())]
    set_dictionary(items)
    return items


def syllables(word: str) -> list[dict[str, Any]]:
    if word in _syllable_cache:
        return _syllable_cache[word]
    if not RE_THAI_ONLY.match(word):
        out = [{"text": word, "known": False, "lead": False}]
        _syllable_cache[word] = out
        return out
    n = len(word)
    dp: list[tuple[int, list[dict[str, Any]]] | None] = [None] * (n + 1)
    dp[n] = (0, [])
    for i in range(n - 1, -1, -1):
        max_end = min(n, i + 16)
        for end in range(i + 1, max_end + 1):
            nxt = dp[end]
            if nxt is None:
                continue
            if end < n and RE_NON_START.match(word[end]):
                continue
            if word[end : end + 2] == "รร":
                continue
            part = word[i:end]
            valid = sound(part) is not None
            norm_part = RE_TONE.sub("", part.replace("เเ", "แ"))
            in_dict = (part in _dictionary) or (part in EXCEPTIONS) or (norm_part in EXCEPTIONS)
            is_lead = (end == i + 1) and (end < n) and (part in LEAD_CONS) and bool(nxt[1] and nxt[1][0]["known"])
            if not valid and not in_dict and not is_lead and end != n:
                continue
            known = is_lead or (valid and (in_dict or len(part) >= 2))
            step_cost = 4 if is_lead else ((1 if in_dict else 3) if valid else (30 + len(part)))
            cost = step_cost + nxt[0]
            if dp[i] is None or cost < dp[i][0]:
                dp[i] = (cost, [{"text": part, "known": known, "lead": is_lead}, *nxt[1]])
    result = dp[0][1] if dp[0] is not None else [{"text": word, "known": False, "lead": False}]
    _syllable_cache[word] = result
    return result


def pair_key(rel_type: str, a: str, b: str, scope: str = "inner") -> str:
    p1, p2 = (a, b) if a <= b else (b, a)
    return f"r:{rel_type}:{scope}:{p1}|{p2}"


def _bucket(n: float) -> str:
    if n == 0:
        return "none"
    if n < 0.05:
        return "low"
    if n < 0.2:
        return "mid"
    return "high"


def segment_line_words(raw: str) -> list[tuple[str, int]]:
    """Tokenize a line using PyThaiNLP newmm and return (word_lower, start_offset) pairs."""
    lower = raw.lower()
    tokens = word_tokenize(lower, engine="newmm", keep_whitespace=True)
    out: list[tuple[str, int]] = []
    offset = 0
    for tok in tokens:
        if RE_WORD_LIKE.search(tok):
            out.append((tok, offset))
        offset += len(tok)
    return out


def analyze(text: str) -> dict[str, Any]:
    norm_text = unicodedata.normalize("NFC", text)
    lines: list[dict[str, Any]] = []
    units: list[dict[str, Any]] = []
    tokens: list[str] = []
    edges: list[dict[str, Any]] = []
    features: list[str] = []
    sections: list[dict[str, Any]] = []

    section = -1
    next_section = True

    for idx, raw in enumerate(re.split(r"\r?\n", norm_text)):
        heading = RE_HEADING.match(raw)
        if not raw.strip() or heading:
            next_section = True
            if heading:
                sections.append({"after": len(lines), "title": heading.group(1)})
            continue
        if next_section:
            section += 1
            next_section = False
        line: dict[str, Any] = {
            "index": len(lines),
            "number": idx + 1,
            "section": section,
            "raw": raw,
            "units": [],
            "words": [],
            "scheme": "?",
        }
        for word, local_offset in segment_line_words(raw):
            tokens.append(word)
            line["words"].append(word)
            features.append("w:" + word)
            pos = local_offset
            for part in syllables(word):
                u_sound = lead_sound(part["text"]) if part["lead"] else (sound(part["text"]) if part["known"] else None)
                u = {
                    "id": len(units),
                    "text": part["text"],
                    "word": word,
                    "line": line["index"],
                    "lineNumber": line["number"],
                    "position": len(line["units"]) + 1,
                    "start": pos,
                    "end": pos + len(part["text"]),
                    "known": part["known"],
                    "sound": u_sound,
                }
                line["units"].append(u)
                units.append(u)
                pos = u["end"]
        if line["units"]:
            lines.append(line)

    edge_keys: set[str] = set()

    def add_edge(rel_type: str, a: dict[str, Any], b: dict[str, Any], scope: str, extra: dict[str, Any] | None = None) -> None:
        if a["id"] == b["id"]:
            return
        size = (extra or {}).get("size", "")
        a_id, b_id = (a["id"], b["id"]) if a["id"] < b["id"] else (b["id"], a["id"])
        key = f"{rel_type}:{a_id}:{b_id}:{size}"
        if key in edge_keys:
            return
        edge_keys.add(key)
        edge: dict[str, Any] = {"id": len(edges), "type": rel_type, "a": a["id"], "b": b["id"], "scope": scope}
        if extra:
            edge.update(extra)
        edges.append(edge)
        features.append(pair_key(rel_type, a["text"], b["text"], scope))

    def compare(a: dict[str, Any], b: dict[str, Any], scope: str, all_types: bool = True) -> None:
        if a["text"] == b["text"]:
            add_edge("repeat", a, b, scope)
            return
        x, y = a["sound"], b["sound"]
        if not x or not y:
            return
        if x["key"] == y["key"]:
            add_edge("vowel", a, b, scope)
        elif x["near"] == y["near"]:
            add_edge("near", a, b, scope)
        elif all_types and x["vowel"] == y["vowel"] and x["length"] == y["length"]:
            add_edge("assonance", a, b, scope)
        if all_types and x["onset"] == y["onset"]:
            add_edge("onset", a, b, scope)
        if all_types and x["coda"] and x["coda"] == y["coda"] and x["key"] != y["key"]:
            add_edge("coda", a, b, scope)

    # Inner-line pairs
    for line in lines:
        u_list = line["units"]
        for i in range(len(u_list)):
            for j in range(i + 1, len(u_list)):
                compare(u_list[i], u_list[j], "inner", True)

    # End-to-word across next 3 lines in section + first line of next section
    for i, line in enumerate(lines):
        last = line["units"][-1]
        for j in range(i + 1, min(len(lines), i + 4)):
            if lines[j]["section"] != line["section"] and j != i + 1:
                break
            scope = "outer" if lines[j]["section"] == line["section"] else "section"
            for u in lines[j]["units"]:
                compare(last, u, scope, False)

    # End groups spanning the whole song
    ending_groups: dict[str, list[dict[str, Any]]] = {}
    scheme_keys: dict[str, int] = {}
    for line in lines:
        last = line["units"][-1]
        key = last["sound"]["key"] if last["sound"] else None
        if not key:
            continue
        if key not in scheme_keys:
            scheme_keys[key] = len(scheme_keys)
        ix = scheme_keys[key]
        line["scheme"] = chr(65 + ix % 26) + (str(ix // 26) if ix >= 26 else "")
        prevs = ending_groups.setdefault(key, [])
        for prev in prevs:
            compare(prev, last, "end", False)
        prevs.append(last)

    # Multi-syllable end rhymes (2 & 3 syllables)
    multi_groups: dict[str, list[list[dict[str, Any]]]] = {}
    for line in lines:
        for size in (2, 3):
            tail = line["units"][-size:]
            if len(tail) < size or any(u["sound"] is None for u in tail):
                continue
            key = "/".join(u["sound"]["key"] for u in tail)
            tail_text = "".join(u["text"] for u in tail)
            for prev in multi_groups.get(key, []):
                if "".join(u["text"] for u in prev) != tail_text:
                    add_edge(
                        "multi",
                        prev[-1],
                        tail[-1],
                        "end",
                        {"aIds": [u["id"] for u in prev], "bIds": [u["id"] for u in tail], "size": size},
                    )
            multi_groups.setdefault(key, []).append(tail)

    # Repeated whole lines
    repeated_lines: dict[str, dict[str, Any]] = {}
    for line in lines:
        key = "|".join(line["words"])
        if not key:
            continue
        prev = repeated_lines.get(key)
        if prev is not None:
            add_edge(
                "phrase",
                prev["units"][0],
                line["units"][0],
                "song",
                {"aIds": [u["id"] for u in prev["units"]], "bIds": [u["id"] for u in line["units"]]},
            )
        else:
            repeated_lines[key] = line

    edge_type_counts = Counter(e["type"] for e in edges)
    counts = {t: edge_type_counts.get(t, 0) for t in NAMES}
    n_units = max(1, len(units))
    for t, n in counts.items():
        features.append(f"density:{t}:{_bucket(n / n_units)}")
    features.extend([
        f"length:{min(12, len(units) // 50)}",
        f"sections:{min(10, section + 1)}",
        f"linecount:{min(15, len(lines) // 4)}",
    ])

    structures: list[dict[str, Any]] = []
    for s in range(section + 1):
        local = [l for l in lines if l["section"] == s]
        local_map: dict[str, str] = {}
        scheme_chars: list[str] = []
        for l in local:
            if l["scheme"] == "?":
                scheme_chars.append("?")
            else:
                if l["scheme"] not in local_map:
                    local_map[l["scheme"]] = chr(65 + len(local_map))
                scheme_chars.append(local_map[l["scheme"]])
        structures.append({
            "section": s,
            "scheme": "".join(scheme_chars),
            "from": local[0]["number"] if local else None,
            "to": local[-1]["number"] if local else None,
        })
        for i in range(0, len(local) - 3, 4):
            keys = [l["scheme"] for l in local[i : i + 4]]
            seen: dict[str, str] = {}
            shape_chars: list[str] = []
            for k in keys:
                if k == "?":
                    shape_chars.append("?")
                else:
                    if k not in seen:
                        seen[k] = chr(65 + len(seen))
                    shape_chars.append(seen[k])
            features.append("scheme:" + "".join(shape_chars))

    return {
        "text": text,
        "tokens": tokens,
        "lines": len(lines),
        "lineDetails": lines,
        "units": units,
        "edges": edges,
        "features": features,
        "counts": counts,
        "structures": structures,
        "sections": sections,
        "recognized": sum(1 for u in units if u["sound"] is not None),
    }


def extract_dense_features(text: str, analysis: dict[str, Any]) -> list[float]:
    raw_lines = [l.strip() for l in re.split(r"\r?\n", text) if l.strip() and not RE_HEADING.match(l.strip())]
    line_freq: Counter = Counter()
    sum_len = 0
    sum_len2 = 0
    dup_lines = 0
    for l in raw_lines:
        norm = re.sub(r"\s+", " ", l.lower())
        line_freq[norm] += 1
        if line_freq[norm] > 1:
            dup_lines += 1
        sum_len += len(l)
        sum_len2 += len(l) * len(l)
    max_line_freq = max(line_freq.values(), default=0)

    eng_words = num_words = thai_words = long_words = short_words = 0
    unique_eng: set[str] = set()
    unique_words: set[str] = set()
    for w in analysis["tokens"]:
        unique_words.add(w)
        if RE_ENG.match(w):
            eng_words += 1
            unique_eng.add(w)
        elif RE_NUM.match(w):
            num_words += 1
        elif RE_HAS_THAI.search(w):
            thai_words += 1
        if len(w) >= 6:
            long_words += 1
        if len(w) <= 2:
            short_words += 1

    n_lines = max(1, len(raw_lines) or analysis["lines"] or 1)
    avg_len = sum_len / n_lines
    std_len = math.sqrt(max(0.0, sum_len2 / n_lines - avg_len * avg_len))
    chars = max(1, len(text))
    blank_lines = len(RE_BLANK_LINES.findall(text))
    n_words = max(1, len(analysis["tokens"]))
    n_units = max(1, len(analysis["units"]))
    n_sections = max(1, len(analysis["structures"]))
    c = analysis["counts"]

    return [
        math.log1p(n_words), math.log1p(n_units), math.log1p(n_lines), math.log1p(len(unique_words)),
        len(unique_words) / n_words, dup_lines / n_lines, math.log1p(max_line_freq), len(line_freq) / n_lines,
        n_words / n_lines, n_units / n_words, n_lines / n_sections, math.log1p(n_sections), math.log1p(blank_lines),
        eng_words / n_words, math.log1p(len(unique_eng)), thai_words / n_words, num_words / n_words,
        long_words / n_words, short_words / n_words, analysis["recognized"] / n_units,
        math.log1p(avg_len), math.log1p(std_len), std_len / max(1.0, avg_len), math.log1p(chars),
        1.0 if re.search(r"\[[^\]]+\]", text) else 0.0,
        (text.count("(") + text.count(")")) / n_lines,
        (text.count("!") + text.count("?")) / n_lines,
        text.count("่") / chars, text.count("้") / chars, text.count("๊") / chars, text.count("๋") / chars,
        c["vowel"] / n_units, c["onset"] / n_units, c["coda"] / n_units,
        c["assonance"] / n_units, c["near"] / n_units, c["repeat"] / n_units,
        c["multi"] / n_lines, c["phrase"] / n_lines, (c["vowel"] + c["multi"]) / n_lines,
    ]
