"""
Pure-Python Unit Test Suite for NaviBay (phonetics, rhymes, loanwords, อักษรนำ,
regional dialects, exported dist/model.js, and metrics.json).

Usage:
  python test.py
  # or with uv:
  uv run --with-requirements requirements.txt python test.py
"""

from __future__ import annotations

import json
import sys
import math
from collections import Counter
from pathlib import Path

from scipy.stats import norm

import phonetics as P

# Windows consoles default to a legacy code page; force UTF-8 so Thai prints correctly.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent


def load_exported_model() -> dict:
    raw = (ROOT / "dist/model.js").read_text(encoding="utf-8").strip()
    prefix = "globalThis.NAVIBAY_MODEL="
    assert raw.startswith(prefix) and raw.endswith(";"), "Invalid dist/model.js wrapper"
    return json.loads(raw[len(prefix) : -1])


def predict_from_exported(model: dict, text: str) -> dict:
    analysis = P.analyze(text)
    vmap = {k: i for i, k in enumerate(model["vocab"])}
    tokens = analysis["tokens"]
    w_cnt = Counter(tokens)
    b_cnt = Counter(f"{tokens[i]}|{tokens[i + 1]}" for i in range(len(tokens) - 1))
    c_cnt: Counter = Counter()
    for w in tokens:
        if 3 <= len(w) <= 12:
            for k in range(len(w) - 2):
                c_cnt[w[k : k + 3]] += 1
    r_cnt = Counter(f for f in analysis["features"] if f.startswith("r:vowel:") or f.startswith("r:multi:"))
    s_cnt = Counter(f for f in analysis["features"] if not f.startswith("w:") and not f.startswith("r:"))

    vec: list[tuple[int, float]] = []
    norm2 = 0.0
    for prefix, cnt in (("w:", w_cnt), ("b:", b_cnt), ("c:", c_cnt), ("r:", r_cnt), ("s:", s_cnt)):
        weight = model["weights"][prefix[0]]
        for k, n in cnt.items():
            vid = vmap.get(prefix + k)
            if vid is None:
                continue
            val = (1.0 + math.log(n)) * model["idf"][vid] * weight
            vec.append((vid, val))
            norm2 += val * val
    inv_norm = 1.0 / (math.sqrt(norm2) or 1.0)
    vec = [(vid, val * inv_norm) for vid, val in vec]

    k_classes = len(model["docs"])
    sc_cnb = [
        (model["cnbB"][c] + sum(model["cnbW"][c][vid] * val for vid, val in vec)) * model["tempCnb"]
        for c in range(k_classes)
    ]
    mx_cnb = max(sc_cnb)
    e_cnb = [math.exp(s - mx_cnb) for s in sc_cnb]
    p_cnb = [v / sum(e_cnb) for v in e_cnb]

    cuts_log = [math.log10(c) for c in model["meta"]["cuts"]]
    v_len = len(model["vocab"])
    dense = P.extract_dense_features(text, analysis)
    pred = model["ridgeB"] + sum(model["ridgeW"][vid] * val for vid, val in vec)
    for d, x in enumerate(dense):
        z = max(-4.0, min(4.0, (x - model["mean"][d]) / model["std"][d])) * model["denseScale"]
        pred += model["ridgeW"][v_len + d] * z

    p_cdf: list[float] = []
    prev = 0.0
    for c in range(6):
        cur = float(norm.cdf(cuts_log[c], loc=pred, scale=model["ridgeSig"]))
        p_cdf.append(max(1e-6, cur - prev))
        prev = cur
    p_cdf.append(max(1e-6, 1.0 - prev))
    s_cdf = sum(p_cdf)
    p_cdf = [v / s_cdf for v in p_cdf]

    w_r = model["blendRidge"]
    raw = [w_r * p_cdf[c] + (1.0 - w_r) * p_cnb[c] for c in range(k_classes)]
    adj = [math.log(max(1e-12, raw[c])) - model["tau"] * math.log(model["priors"][c]) for c in range(k_classes)]
    mx_a = max(adj)
    e_a = [math.exp(s - mx_a) for s in adj]
    prob = [v / sum(e_a) for v in e_a]
    best = max(range(k_classes), key=lambda c: prob[c])
    known_words = sum(1 for w in tokens if ("w:" + w) in vmap)
    return {"analysis": analysis, "prob": prob, "label": best, "knownWords": known_words}


def run_tests() -> None:
    P.load_default_dictionary(ROOT)

    # Core Thai rhymes & onsets
    assert P.rhyme("ใจ") == P.rhyme("ไกล")
    assert P.rhyme("รัก") == P.rhyme("พัก")
    assert P.rhyme("คิด") == P.rhyme("จิต")
    assert P.rhyme("เธอ") == P.rhyme("เจอ")
    assert P.rhyme("รอ") == P.rhyme("ขอ")
    assert P.rhyme("ใจ") != P.rhyme("กาย")
    assert P.sound("ฟ้า")["onset"] == P.sound("ฝัน")["onset"]
    assert P.sound("กล้า")["onset"] != P.sound("กา")["onset"]
    assert [s["text"] for s in P.syllables("หัวใจ")] == ["หัว", "ใจ"]
    assert [s["text"] for s in P.syllables("ความหวัง")] == ["ความ", "หวัง"]

    # Loanwords
    assert P.rhyme("สไตล์") == P.rhyme("ใจ")
    assert P.rhyme("เบียร์") == P.rhyme("เชียร์")
    assert P.rhyme("แคร์") == P.rhyme("แพ้")
    assert P.rhyme("ป๊อป") == P.rhyme("สต็อป")
    assert P.rhyme("ดรอป") == P.rhyme("ชอบ")
    assert P.rhyme("เทรนด์") == P.rhyme("เป็น")
    assert P.rhyme("แทร็ป") == P.rhyme("แร็ป")
    assert P.rhyme("ฟีล") == P.rhyme("ปีน")
    assert P.rhyme("กรูฟ") == P.rhyme("จูบ")

    # Complex อักษรนำ, false clusters, ร หัน, multi-letter karan
    assert [s["text"] for s in P.syllables("สบาย")] == ["ส", "บาย"]
    assert any(e["type"] == "vowel" and e["scope"] == "outer" for e in P.analyze("สบาย\nกาย")["edges"])
    assert [s["text"] for s in P.syllables("อร่อย")] == ["อ", "ร่อย"]
    assert any(e["type"] == "vowel" and e["scope"] == "outer" for e in P.analyze("อร่อย\nคอย")["edges"])
    assert [s["text"] for s in P.syllables("ถนน")] == ["ถ", "นน"]
    assert any(e["type"] == "vowel" and e["scope"] == "outer" for e in P.analyze("ถนน\nคน")["edges"])
    assert [s["text"] for s in P.syllables("สวรรค์")] == ["ส", "วรรค์"]
    assert any(e["type"] == "vowel" and e["scope"] == "outer" for e in P.analyze("สวรรค์\nฝัน")["edges"])
    assert P.rhyme("จันทร์") == P.rhyme("ฝัน")
    assert P.rhyme("ศาสตร์") == P.rhyme("ขาด")
    assert P.rhyme("ธรรม") == P.rhyme("คำ")
    assert P.rhyme("สร้าง") == P.rhyme("ทาง") and P.sound("สร้าง")["onset"] == "s"
    assert P.rhyme("เศร้า") == P.rhyme("เหงา") and P.sound("เศร้า")["onset"] == "s"
    assert P.rhyme("ทรง") == P.rhyme("หลง") and P.sound("ทรง")["onset"] == "s"

    # Regional dialects (Isan, Northern, Southern)
    assert P.rhyme("บ่") == P.rhyme("ก็")
    assert P.rhyme("ฮู้") == P.rhyme("รู้")
    assert P.rhyme("ฮัก") == P.rhyme("รัก")
    assert P.rhyme("เด้อ") == P.rhyme("เธอ")
    assert P.rhyme("ซ่อย") == P.rhyme("คอย")
    assert P.rhyme("คึด") == P.rhyme("ยึด")
    assert P.rhyme("แซ่บ") == P.rhyme("แอบ")
    assert P.rhyme("เปิ้น") == P.rhyme("เดิน")
    assert P.rhyme("ปิ๊ก") == P.rhyme("พริก")
    assert P.rhyme("กิ๋น") == P.rhyme("ดิน")
    assert P.rhyme("ใจ๋") == P.rhyme("ไกล")
    assert P.rhyme("แต๊") == P.rhyme("แท้")
    assert P.rhyme("หรอย") == P.rhyme("คอย")
    assert P.rhyme("หม้าย") == P.rhyme("กาย")
    assert P.rhyme("หนัด") == P.rhyme("ชัด")
    assert P.rhyme("พรือ") == P.rhyme("มือ")

    # All 8 relation types, offsets, stanza boundaries, AABB/ABAB
    a = P.analyze("[Verse]\nใจ ไป ไกล\nรัก พัก\n\n[Chorus]\nรัก พัก\nใจ ไป ไกล")
    assert a["lines"] == 4
    assert len(a["structures"]) == 2
    assert a["lineDetails"][0]["number"] == 2
    assert a["counts"]["phrase"] > 0
    assert any(e["type"] == "vowel" and e["scope"] == "inner" for e in a["edges"])
    assert any(e["type"] == "repeat" and e["scope"] != "inner" for e in a["edges"])
    assert "verse" not in a["tokens"]
    for u in a["units"]:
        assert a["lineDetails"][u["line"]]["raw"][u["start"] : u["end"]] == u["text"]

    assert any(e["type"] == "vowel" and e["scope"] == "outer" for e in P.analyze("ใจ\nไกล")["edges"])
    assert any(e["type"] == "near" for e in P.analyze("ใจ กาย")["edges"])
    assert not any(e["type"] == "vowel" for e in P.analyze("ใจ กาย")["edges"])
    assert any(e["type"] == "assonance" for e in P.analyze("รัก ฝัน")["edges"])
    assert any(e["type"] == "coda" for e in P.analyze("รัก มาก")["edges"])
    assert any(e["type"] == "onset" for e in P.analyze("ฟ้า ฝัน")["edges"])
    assert all(e["type"] == "repeat" for e in P.analyze("ใจ ใจ")["edges"])
    assert any(e["type"] == "multi" and e.get("size") == 2 for e in P.analyze("ขอ ใจ\nรอ ไกล")["edges"])
    assert P.analyze("ใจ\nไกล\nรัก\nพัก")["structures"][0]["scheme"] == "AABB"
    assert P.analyze("ใจ\nรัก\nไกล\nพัก")["structures"][0]["scheme"] == "ABAB"
    assert P.analyze("english only")["recognized"] == 0
    assert len(P.analyze("")["units"]) == 0

    # Exported model.js & metrics.json checks
    model = load_exported_model()
    assert model["version"] == 3 and model["type"] == "hybrid-v3"
    full = "\n".join("รอ ใจ ไกล" if i % 2 else "รัก พัก ฝัน" for i in range(40))
    res = predict_from_exported(model, full)
    assert res["analysis"]["lines"] == 40
    assert len(res["prob"]) == 7
    assert all(math.isfinite(p) for p in res["prob"])
    assert abs(sum(res["prob"]) - 1.0) < 1e-9
    assert res["knownWords"] > 0

    m = model["meta"]
    assert m["train"] + m["test"] == m["usable"]
    assert sum(sum(row) for row in m["matrix"]) == m["test"]
    assert len(m["classCounts"]) == 7
    assert sum(c["test"] for c in m["perClass"]) == m["test"]
    assert m["cuts"] == [10000, 100000, 500000, 1000000, 5000000, 10000000]
    assert m["accuracy"] > m["baseline"]

    print(
        "PASS (Python): syllables, loanwords, อักษรนำ, dialects, all 8 relation types, "
        "offsets, stanza boundaries, AABB/ABAB, full-song inference, and 7-class evaluation"
    )


if __name__ == "__main__":
    run_tests()
