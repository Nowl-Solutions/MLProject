"""
NaviBay v3 Pure-Python Training Pipeline (PyThaiNLP + scikit-learn + SciPy + NumPy)

Reads songs.csv directly in Python, extracts Thai phonetic/rhyme/structural features
via phonetics.py, trains the Hybrid Ordinal Ridge-Gaussian + Complement Naive Bayes
model with 5-fold Artist-Group CV, and exports:
  - dist/syllables.js (dictionary for the web UI)
  - dist/model.js     (browser-ready model consumed directly by dist/engine.js)
  - metrics.json      (artist-group holdout evaluation report)

Usage:
  python train.py data/songs.csv
  # or with uv:
  uv run --with-requirements requirements.txt python train.py data/songs.csv
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from scipy import sparse
from scipy.stats import norm
from sklearn.linear_model import Ridge
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support
from sklearn.model_selection import GroupKFold
from sklearn.naive_bayes import ComplementNB
from sklearn.preprocessing import StandardScaler

import phonetics as P

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

CUTS = [10_000, 100_000, 500_000, 1_000_000, 5_000_000, 10_000_000]
CUTS_LOG = [math.log10(c) for c in CUTS]
LABELS = [
    "ต่ำกว่า 10,000",
    "10,000–99,999",
    "100,000–499,999",
    "500,000–999,999",
    "1,000,000–4,999,999",
    "5,000,000–9,999,999",
    "10,000,000 ขึ้นไป",
]
NUM_CLASSES = 7

FEATURE_WEIGHTS = {"w": 1.0, "b": 0.8, "c": 0.6, "r": 0.4, "s": 0.5}
MIN_DF = {"w:": 2, "b:": 5, "c:": 8, "r:": 8, "s:": 2}
DENSE_SCALE = 0.30
RIDGE_ALPHAS = [15.0, 35.0, 60.0, 100.0]
SIG_MULT = 1.25
CNB_ALPHA = 0.5
CNB_PRIOR_POW = 0.6
CNB_TEMP = 0.35
BLEND_RIDGE = 0.70
TAU = 0.20

RE_WS = re.compile(r"\s")


def q4(v: float) -> float:
    return round(float(v), 4)


def views_to_band(views: int) -> int:
    for i, c in enumerate(CUTS):
        if views < c:
            return i
    return len(CUTS)


def is_test_group(group: str) -> bool:
    return hashlib.sha256(group.encode("utf-8")).digest()[0] < 51


def build_doc_counters(song: dict, include_rich: bool = True) -> dict[str, Counter]:
    tokens = song["tokens"]
    w_cnt = Counter(tokens)
    s_cnt = Counter(song["struct"])
    if not include_rich:
        return {"w:": w_cnt, "s:": s_cnt}

    b_cnt = Counter(f"{tokens[i]}|{tokens[i + 1]}" for i in range(len(tokens) - 1))
    c_cnt: Counter = Counter()
    for w in tokens:
        if 3 <= len(w) <= 12:
            for k in range(len(w) - 2):
                c_cnt[w[k : k + 3]] += 1
    r_cnt = Counter(f for f in song["rhymes"] if f.startswith("r:vowel:") or f.startswith("r:multi:"))
    return {"w:": w_cnt, "b:": b_cnt, "c:": c_cnt, "r:": r_cnt, "s:": s_cnt}


def fit_tfidf(doc_counters: list[dict[str, Counter]]):
    n_docs = len(doc_counters)
    df: Counter = Counter()
    for d in doc_counters:
        for prefix, cnt in d.items():
            for k in cnt.keys():
                df[prefix + k] += 1

    max_df = int(n_docs * 0.95)
    vocab: list[str] = []
    vocab_map: dict[str, int] = {}
    idf: list[float] = []
    for fk, d_val in df.items():
        prefix = fk[:2]
        min_d = MIN_DF.get(prefix, 2)
        if d_val < min_d or d_val > max_df:
            continue
        vocab_map[fk] = len(vocab)
        vocab.append(fk)
        idf.append(math.log((n_docs + 1) / (d_val + 1)) + 1.0)

    return vocab, vocab_map, np.array(idf, dtype=np.float64)


def transform_tfidf(
    doc_counters: list[dict[str, Counter]],
    vocab_map: dict[str, int],
    idf: np.ndarray,
) -> sparse.csr_matrix:
    rows, cols, vals = [], [], []
    for row_idx, d in enumerate(doc_counters):
        row_cols = []
        row_vals = []
        norm2 = 0.0
        for prefix, cnt in d.items():
            w = FEATURE_WEIGHTS[prefix[0]]
            for k, c in cnt.items():
                vid = vocab_map.get(prefix + k)
                if vid is None:
                    continue
                v = (1.0 + math.log(c)) * idf[vid] * w
                row_cols.append(vid)
                row_vals.append(v)
                norm2 += v * v
        inv_norm = 1.0 / (math.sqrt(norm2) or 1.0)
        rows.extend([row_idx] * len(row_cols))
        cols.extend(row_cols)
        vals.extend(v * inv_norm for v in row_vals)

    return sparse.csr_matrix((vals, (rows, cols)), shape=(len(doc_counters), len(idf)), dtype=np.float64)


def ridge_cdf_probs(preds: np.ndarray, sig: float) -> np.ndarray:
    probs = np.zeros((len(preds), NUM_CLASSES), dtype=np.float64)
    prev = np.zeros(len(preds), dtype=np.float64)
    for c in range(6):
        cur = norm.cdf(CUTS_LOG[c], loc=preds, scale=sig)
        probs[:, c] = np.maximum(1e-6, cur - prev)
        prev = cur
    probs[:, 6] = np.maximum(1e-6, 1.0 - prev)
    probs /= probs.sum(axis=1, keepdims=True)
    return probs


def cnb_probs(cnb: ComplementNB, X: sparse.csr_matrix, priors: np.ndarray) -> np.ndarray:
    cnb_w = cnb.feature_log_prob_
    cnb_b = CNB_PRIOR_POW * np.log(priors)
    scores = (X @ cnb_w.T + cnb_b) * CNB_TEMP
    scores -= scores.max(axis=1, keepdims=True)
    exp = np.exp(scores)
    return exp / exp.sum(axis=1, keepdims=True)


def blend_and_adjust(p_cdf: np.ndarray, p_cnb: np.ndarray, priors: np.ndarray) -> np.ndarray:
    raw = BLEND_RIDGE * p_cdf + (1.0 - BLEND_RIDGE) * p_cnb
    adj = np.log(np.maximum(1e-12, raw)) - TAU * np.log(priors)
    adj -= adj.max(axis=1, keepdims=True)
    exp = np.exp(adj)
    return exp / exp.sum(axis=1, keepdims=True)


def fit_and_predict_hybrid(
    train_songs: list[dict],
    eval_songs: list[dict],
    y_train: np.ndarray,
    views_train: np.ndarray,
    ridge_alpha: float = 35.0,
):
    tr_counters = [build_doc_counters(s, include_rich=True) for s in train_songs]
    ev_counters = [build_doc_counters(s, include_rich=True) for s in eval_songs]

    vocab, vocab_map, idf = fit_tfidf(tr_counters)
    X_tr = transform_tfidf(tr_counters, vocab_map, idf)
    X_ev = transform_tfidf(ev_counters, vocab_map, idf)

    D_tr_raw = np.array([s["dense"] for s in train_songs], dtype=np.float64)
    D_ev_raw = np.array([s["dense"] for s in eval_songs], dtype=np.float64)
    scaler = StandardScaler()
    D_tr = np.clip(scaler.fit_transform(D_tr_raw), -4.0, 4.0) * DENSE_SCALE
    D_ev = np.clip(scaler.transform(D_ev_raw), -4.0, 4.0) * DENSE_SCALE

    docs = np.bincount(y_train, minlength=NUM_CLASSES)
    priors = (docs + 1.0) / (len(y_train) + NUM_CLASSES)

    # 1. Complement Naive Bayes (scikit-learn)
    cnb = ComplementNB(alpha=CNB_ALPHA, norm=False)
    cnb.fit(X_tr, y_train)
    p_cnb_ev = cnb_probs(cnb, X_ev, priors)

    # 2. Ordinal Ridge Regression on log10(views) (scikit-learn)
    y_log_tr = np.log10(np.maximum(100.0, views_train))
    X_tr_full = sparse.hstack([X_tr, sparse.csr_matrix(D_tr)], format="csr")
    X_ev_full = sparse.hstack([X_ev, sparse.csr_matrix(D_ev)], format="csr")
    ridge = Ridge(alpha=ridge_alpha, solver="lsqr", tol=1e-5, max_iter=500)
    ridge.fit(X_tr_full, y_log_tr)

    tr_preds = ridge.predict(X_tr_full)
    sig = float(np.sqrt(np.mean((tr_preds - y_log_tr) ** 2)) * SIG_MULT)
    ev_preds = ridge.predict(X_ev_full)
    p_cdf_ev = ridge_cdf_probs(ev_preds, sig)

    probs = blend_and_adjust(p_cdf_ev, p_cnb_ev, priors)
    artifacts = {
        "vocab": vocab,
        "idf": idf,
        "scaler": scaler,
        "ridge": ridge,
        "sig": sig,
        "cnb": cnb,
        "docs": docs,
        "priors": priors,
    }
    return probs, artifacts


def load_and_analyze_csv(csv_path: Path, root: Path) -> tuple[int, list[dict]]:
    dictionary = P.load_default_dictionary(root)
    (root / "dist/syllables.js").write_text(
        "globalThis.NAVIBAY_SYLLABLES=" + json.dumps(dictionary, ensure_ascii=False, separators=(",", ":")) + ";",
        encoding="utf-8",
    )

    songs: list[dict] = []
    seen: set[str] = set()
    source_rows = 0

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            source_rows += 1
            lyrics = r.get("lyrics") or ""
            views_str = (r.get("views") or "").strip()
            key = RE_WS.sub("", lyrics)
            if len(key) < 30 or key in seen or not views_str.isdigit():
                continue
            seen.add(key)
            views = int(views_str)
            group = (r.get("artist_group") or r.get("artist") or r.get("title") or "").strip().lower()
            analysis = P.analyze(lyrics)
            rhymes = [feat for feat in analysis["features"] if feat.startswith("r:")]
            struct = [feat for feat in analysis["features"] if not feat.startswith("w:") and not feat.startswith("r:")]
            dense = P.extract_dense_features(lyrics, analysis)
            songs.append({
                "group": group,
                "views": views,
                "label": views_to_band(views),
                "tokens": analysis["tokens"],
                "rhymes": rhymes,
                "struct": struct,
                "dense": dense,
            })
            if len(songs) % 1000 == 0:
                print(f"Analyzed complete songs (Python): {len(songs)}")

    print(f"Finished Python extraction: {len(songs)} usable songs from {source_rows} rows")
    return source_rows, songs


def main() -> None:
    root = Path(__file__).resolve().parent
    csv_path = Path(sys.argv[1]).resolve() if len(sys.argv) >= 2 else (root / "data/songs.csv")
    if not csv_path.exists():
        raise SystemExit(f"Dataset not found: {csv_path}\nUsage: python train.py data/songs.csv")

    # Step 1: Pure-Python Thai phonetic/rhyme/structural extraction
    source_rows, songs = load_and_analyze_csv(csv_path, root)

    train_songs = [s for s in songs if not is_test_group(s["group"])]
    test_songs = [s for s in songs if is_test_group(s["group"])]
    y_train = np.array([s["label"] for s in train_songs], dtype=np.int64)
    y_test = np.array([s["label"] for s in test_songs], dtype=np.int64)
    views_train = np.array([s["views"] for s in train_songs], dtype=np.float64)
    groups_train = np.array([s["group"] for s in train_songs])

    # Step 2: 5-fold Artist-Group CV on training set only to select Ridge alpha
    gkf = GroupKFold(n_splits=5)
    best_alpha, cv_acc, cv_f1 = RIDGE_ALPHAS[0], -1.0, -1.0
    for alpha_cand in RIDGE_ALPHAS:
        oof_preds = np.zeros(len(train_songs), dtype=np.int64)
        for tr_idx, va_idx in gkf.split(train_songs, y_train, groups_train):
            p_va, _ = fit_and_predict_hybrid(
                [train_songs[i] for i in tr_idx],
                [train_songs[i] for i in va_idx],
                y_train[tr_idx],
                views_train[tr_idx],
                ridge_alpha=alpha_cand,
            )
            oof_preds[va_idx] = p_va.argmax(axis=1)
        acc_c = float(accuracy_score(y_train, oof_preds))
        f1_c = float(f1_score(y_train, oof_preds, average="macro", zero_division=0))
        print(f"  CV alpha={alpha_cand:5.1f} -> Accuracy={acc_c:.4f}, Macro-F1={f1_c:.4f}")
        if acc_c > cv_acc:
            best_alpha, cv_acc, cv_f1 = alpha_cand, acc_c, f1_c
    print(f"Selected Ridge alpha={best_alpha} via 5-fold Artist-Group CV (Acc={cv_acc:.4f}, Macro-F1={cv_f1:.4f})")

    # Step 3: Train final Hybrid v3 model on full training set & evaluate on untouched holdout test set
    probs_test, art = fit_and_predict_hybrid(train_songs, test_songs, y_train, views_train, ridge_alpha=best_alpha)
    y_pred = probs_test.argmax(axis=1)

    # Words+struct-only ComplementNB baseline for fair comparison
    tr_uni = [build_doc_counters(s, include_rich=False) for s in train_songs]
    te_uni = [build_doc_counters(s, include_rich=False) for s in test_songs]
    _, vmap_uni, idf_uni = fit_tfidf(tr_uni)
    X_tr_uni = transform_tfidf(tr_uni, vmap_uni, idf_uni)
    X_te_uni = transform_tfidf(te_uni, vmap_uni, idf_uni)
    cnb_uni = ComplementNB(alpha=CNB_ALPHA, norm=False).fit(X_tr_uni, y_train)
    p_uni = cnb_probs(cnb_uni, X_te_uni, art["priors"])
    unigram_acc = float(accuracy_score(y_test, p_uni.argmax(axis=1)))

    # Metrics
    accuracy = float(accuracy_score(y_test, y_pred))
    majority_class = int(np.argmax(art["docs"]))
    baseline = float(np.mean(y_test == majority_class))
    macro_f1 = float(f1_score(y_test, y_pred, average="macro", zero_division=0))
    within_one = float(np.mean(np.abs(y_pred - y_test) <= 1))
    top2_idx = np.argsort(-probs_test, axis=1)[:, :2]
    top_two = float(np.mean([y_test[i] in top2_idx[i] for i in range(len(y_test))]))
    mat = confusion_matrix(y_test, y_pred, labels=list(range(NUM_CLASSES)))
    prec, rec, f1s, sup = precision_recall_fscore_support(
        y_test, y_pred, labels=list(range(NUM_CLASSES)), zero_division=0
    )

    per_class = [
        {
            "label": LABELS[i],
            "train": int(art["docs"][i]),
            "test": int(sup[i]),
            "precision": float(prec[i]),
            "recall": float(rec[i]),
            "f1": float(f1s[i]),
        }
        for i in range(NUM_CLASSES)
    ]

    dict_bytes = (root / "dist/vendor/syllables-th.txt").read_bytes()
    meta = {
        "sourceRows": source_rows,
        "usable": len(songs),
        "train": len(train_songs),
        "test": len(test_songs),
        "cuts": CUTS,
        "labels": LABELS,
        "accuracy": accuracy,
        "unigramAccuracy": unigram_acc,
        "baseline": baseline,
        "macroF1": macro_f1,
        "withinOne": within_one,
        "topTwo": top_two,
        "cvAccuracy": cv_acc,
        "cvMacroF1": cv_f1,
        "matrix": mat.tolist(),
        "perClass": per_class,
        "classCounts": [int(x) for x in art["docs"]],
        "trainer": "Pure Python (PyThaiNLP + scikit-learn Ridge & ComplementNB + SciPy + NumPy)",
        "featureMode": "whole-song-v3: TF-IDF L2 words + bigrams + char 3-grams + filtered vowel/multi rhymes + 40 song-level structural/phonetic features (Ordinal Ridge-Gaussian + Complement NB hybrid)",
        "method": "artist-group holdout; SHA-256 first byte <51; exact whitespace-normalized lyric deduplication; fixed view bands; entire songs; trained in pure Python with 5-fold GroupKFold CV on training set only",
        "dictionary": {
            "source": "https://github.com/PyThaiNLP/pythainlp/blob/dev/pythainlp/corpus/syllables_th.txt",
            "sha256": hashlib.sha256(dict_bytes).hexdigest(),
            "license": "Apache-2.0",
            "downloaded": "2026-11-23",
        },
    }

    rhyme_freq: Counter = Counter()
    for s in train_songs:
        rhyme_freq.update(s["rhymes"])
    rhyme_pairs = [[f, int(n)] for f, n in rhyme_freq.most_common(25_000) if n >= 3]

    cnb_w = art["cnb"].feature_log_prob_
    cnb_b = CNB_PRIOR_POW * np.log(art["priors"])
    model_obj = {
        "type": "hybrid-v3",
        "version": 3,
        "n": len(train_songs),
        "docs": [int(x) for x in art["docs"]],
        "priors": [q4(x) for x in art["priors"]],
        "vocab": art["vocab"],
        "idf": [q4(x) for x in art["idf"]],
        "weights": FEATURE_WEIGHTS,
        "denseScale": DENSE_SCALE,
        "mean": [q4(x) for x in art["scaler"].mean_],
        "std": [q4(x if x > 0 else 1.0) for x in art["scaler"].scale_],
        "ridgeW": [q4(x) for x in art["ridge"].coef_],
        "ridgeB": q4(art["ridge"].intercept_),
        "ridgeSig": q4(art["sig"]),
        "cnbW": [[q4(v) for v in row] for row in cnb_w],
        "cnbB": [q4(x) for x in cnb_b],
        "tempCnb": CNB_TEMP,
        "blendRidge": BLEND_RIDGE,
        "tau": TAU,
        "rhymePairs": rhyme_pairs,
        "meta": meta,
    }

    (root / "dist/model.js").write_text(
        "globalThis.NAVIBAY_MODEL=" + json.dumps(model_obj, ensure_ascii=False, separators=(",", ":")) + ";",
        encoding="utf-8",
    )
    (root / "metrics.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
