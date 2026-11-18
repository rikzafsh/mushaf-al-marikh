"""Mendeteksi dan mendata semua posisi tanda waqaf pada data ayat.

Pemakaian (dari folder proyek):

    python extract_waqf.py                       # Kemenag, data/ayat -> data/waqf/
    python extract_waqf.py --ayat-dir D:\\data\\ayat --out-dir hasil
    python extract_waqf.py --source kemenag --surah 1 2 3

Keluaran (nama mengikuti --source, supaya data mushaf lain bisa berdampingan):

    data/waqf/waqf_<source>.json   # meta + ringkasan + semua record
    data/waqf/waqf_<source>.csv    # satu baris per tanda waqaf (UTF-8 BOM, aman untuk Excel)

Definisi posisi
---------------
Setiap tanda dicatat sebagai "berada SETELAH kata ke-N" dalam ayatnya.

* word_index   : urutan kata asli (1, 2, 3, ...). Token yang isinya hanya tanda
                 (mis. "ەۙ" pada 1:7) TIDAK dihitung sebagai kata; tanda itu dicatat
                 sesudah kata sebelumnya.
* token_index  : urutan item di dalam `arabic_words` (token tanda ikut dihitung).
                 Ini sama dengan acuan `word_count` di mushaf.json.
* attached     : true  -> tanda menempel pada kata itu sendiri
                 false -> tanda berdiri sendiri sebagai token terpisah
* position     : "akhir"  -> tanda berada setelah kata terakhir ayat
                 "tengah" -> masih ada kata sesudahnya dalam ayat itu

Jika `arabic_words` null/kosong, kata dipecah dari `arabic` per spasi
(field `words_source` = "arabic_split").

Menambah sumber mushaf lain: tulis fungsi pembaca yang menghasilkan dict
{surah, ayah, page, juz, words, text} lalu daftarkan di LOADERS.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterator

PROJECT_DIR = Path(__file__).parent

# --------------------------------------------------------------------------
# Tanda waqaf (blok Unicode Arabic: U+06D6 – U+06DC)
# --------------------------------------------------------------------------
WAQF_SIGNS: dict[str, dict[str, str]] = {
    "\u06D6": {"kind": "shila",   "label": "ۖ  صلى",   "name": "Ṣilā – lebih utama dilanjutkan (al-waṣl awlā)"},
    "\u06D7": {"kind": "qila",    "label": "ۗ  قلى",   "name": "Qilā – lebih utama berhenti (al-waqf awlā)"},
    "\u06D8": {"kind": "lazim",   "label": "ۘ  م",     "name": "Mīm – wajib berhenti (waqf lāzim)"},
    "\u06D9": {"kind": "la",      "label": "ۙ  لا",    "name": "Lā – tidak boleh berhenti"},
    "\u06DA": {"kind": "jaiz",    "label": "ۚ  ج",     "name": "Jīm – boleh berhenti atau lanjut (waqf jā'iz)"},
    "\u06DB": {"kind": "muanaqah", "label": "ۛ  ∴",    "name": "Mu'ānaqah – berhenti di salah satu dari dua tanda"},
    "\u06DC": {"kind": "saktah",  "label": "ۜ  س",     "name": "Sīn – saktah (berhenti sejenak tanpa napas)"},
}

# Tanda anotasi lain yang BUKAN waqaf; hanya dilaporkan di ringkasan agar terlihat.
OTHER_MARK_RANGES = [(0x06DD, 0x06DE), (0x06E9, 0x06E9), (0x08D3, 0x08FF)]
# Huruf pengganti sebagai "penopang" tanda yang berdiri sendiri (mis. "ەۙ").
PLACEHOLDERS = {"\u06D5", "\u0640"}


def code(ch: str) -> str:
    return f"U+{ord(ch):04X}"


def is_other_mark(ch: str) -> bool:
    o = ord(ch)
    return any(a <= o <= b for a, b in OTHER_MARK_RANGES)


def is_standalone_sign(token: str) -> bool:
    """True bila token hanya berisi tanda (tanpa huruf kata sebenarnya)."""
    for ch in token:
        if ch in WAQF_SIGNS or ch in PLACEHOLDERS or ch.isspace() or is_other_mark(ch):
            continue
        if unicodedata.category(ch).startswith("L"):
            return False
    return True


# --------------------------------------------------------------------------
# Pembaca data (satu fungsi per sumber)
# --------------------------------------------------------------------------
def load_kemenag(ayat_dir: Path, surahs: list[int] | None) -> Iterator[dict]:
    """Format Kemenag: <ayat_dir>/<id>.json berisi daftar ayat."""
    ids = surahs or range(1, 115)
    for sid in ids:
        path = ayat_dir / f"{sid}.json"
        if not path.exists():
            yield {"missing_surah": sid}
            continue
        with open(path, encoding="utf-8") as f:
            rows = json.load(f)
        for r in sorted(rows, key=lambda x: x["ayah"]):
            yield {
                "surah": r.get("surah_id", sid),
                "ayah": r["ayah"],
                "page": r.get("page"),
                "juz": r.get("juz"),
                "words": r.get("arabic_words"),
                "text": r.get("arabic") or "",
            }


LOADERS: dict[str, Callable[[Path, list[int] | None], Iterator[dict]]] = {
    "kemenag": load_kemenag,
}


# --------------------------------------------------------------------------
# Ekstraksi
# --------------------------------------------------------------------------
def extract_ayah(ayah: dict, source: str):
    """Kembalikan (records, other_marks, info) untuk satu ayat."""
    words = ayah["words"]
    words_source = "arabic_words"
    if not words:
        words = ayah["text"].split()
        words_source = "arabic_split"

    total_words = sum(1 for t in words if not is_standalone_sign(t))
    records, others = [], []
    real = 0
    last_real_text = ""
    for t_idx, token in enumerate(words, 1):
        standalone = is_standalone_sign(token)
        if not standalone:
            real += 1
            last_real_text = token
        for offset, ch in enumerate(token):
            if ch in WAQF_SIGNS:
                info = WAQF_SIGNS[ch]
                after = token if not standalone else last_real_text
                after = "".join(c for c in after if c not in WAQF_SIGNS and c not in PLACEHOLDERS).strip()
                records.append({
                    "source": source,
                    "surah": ayah["surah"],
                    "ayah": ayah["ayah"],
                    "page": ayah["page"],
                    "juz": ayah["juz"],
                    "sign": ch,
                    "code": code(ch),
                    "kind": info["kind"],
                    "name": info["name"],
                    "position": "akhir" if real >= total_words else "tengah",
                    "word_index": real,
                    "total_words": total_words,
                    "token_index": t_idx,
                    "attached": not standalone,
                    "after_word": after,
                })
            elif is_other_mark(ch):
                others.append({"surah": ayah["surah"], "ayah": ayah["ayah"], "char": ch,
                               "code": code(ch), "token_index": t_idx, "word_index": real})

    # cek silang: jumlah tanda di teks `arabic` vs di daftar kata
    mismatch = None
    if ayah["text"] and words_source == "arabic_words":
        in_text = sum(ayah["text"].count(c) for c in WAQF_SIGNS)
        in_words = len(records)
        if in_text != in_words:
            mismatch = {"surah": ayah["surah"], "ayah": ayah["ayah"], "in_arabic": in_text, "in_words": in_words}
    return records, others, {"words_source": words_source, "mismatch": mismatch}


def build(source: str, ayat_dir: Path, surahs: list[int] | None):
    loader = LOADERS[source]
    records: list[dict] = []
    other_counter: Counter = Counter()
    other_examples: dict[str, list[str]] = {}
    missing, mismatches = [], []
    ayat_total = ayat_with_waqf = fallback = 0

    for ayah in loader(ayat_dir, surahs):
        if "missing_surah" in ayah:
            missing.append(ayah["missing_surah"])
            continue
        ayat_total += 1
        recs, others, info = extract_ayah(ayah, source)
        if info["words_source"] == "arabic_split":
            fallback += 1
        if info["mismatch"]:
            mismatches.append(info["mismatch"])
        if recs:
            ayat_with_waqf += 1
        records += recs
        for o in others:
            other_counter[o["code"]] += 1
            ex = other_examples.setdefault(o["code"], [])
            if len(ex) < 3:
                ex.append(f"{o['surah']}:{o['ayah']} (kata ke-{o['word_index']})")

    for i, r in enumerate(records, 1):
        r["id"] = i

    by_sign = Counter(r["code"] for r in records)
    by_pos = Counter(r["position"] for r in records)
    cross: dict[str, dict[str, int]] = {}
    for r in records:
        cross.setdefault(r["code"], {"akhir": 0, "tengah": 0})[r["position"]] += 1
    per_surah = Counter(r["surah"] for r in records)

    summary = {
        "total_signs": len(records),
        "by_position": dict(by_pos),
        "by_sign": {c: {"sign": chr(int(c[2:], 16)), "kind": WAQF_SIGNS[chr(int(c[2:], 16))]["kind"],
                        "count": n, **cross[c]} for c, n in sorted(by_sign.items())},
        "per_surah": {str(k): v for k, v in sorted(per_surah.items())},
        "ayat_processed": ayat_total,
        "ayat_with_waqf": ayat_with_waqf,
        "ayat_words_from_arabic_split": fallback,
        "surah_file_missing": missing,
        "mismatch_arabic_vs_words": mismatches[:50],
        "other_marks_not_waqf": {
            c: {"char": chr(int(c[2:], 16)), "name": unicodedata.name(chr(int(c[2:], 16)), "?"),
                "count": n, "examples": other_examples[c]}
            for c, n in sorted(other_counter.items())
        },
    }
    return records, summary


# --------------------------------------------------------------------------
# Penulisan
# --------------------------------------------------------------------------
CSV_FIELDS = ["id", "source", "surah", "ayah", "page", "juz", "sign", "code", "kind", "name",
              "position", "word_index", "total_words", "token_index", "attached", "after_word"]


def write_json(path: Path, source: str, records: list[dict], summary: dict):
    doc = {
        "source": source,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": ("word_index = urutan kata asli (token tanda tidak dihitung); "
                 "token_index = urutan item di arabic_words; tanda dicatat SETELAH kata tersebut."),
        "signs": {c: {"sign": ch, "kind": v["kind"], "name": v["name"]}
                  for ch, v in WAQF_SIGNS.items() for c in [code(ch)]},
        "summary": summary,
        "records": "__RECORDS__",
    }
    text = json.dumps(doc, ensure_ascii=False, indent=2)
    body = ",\n".join("    " + json.dumps(r, ensure_ascii=False) for r in records)
    text = text.replace('"__RECORDS__"', "[\n" + body + "\n  ]" if records else "[]")
    path.write_text(text + "\n", encoding="utf-8")


def write_csv(path: Path, records: list[dict]):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:  # BOM agar Excel membaca UTF-8
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in records:
            w.writerow({**r, "attached": "ya" if r["attached"] else "tidak"})


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Data posisi tanda waqaf per ayat -> JSON & CSV")
    ap.add_argument("--source", default="kemenag", choices=sorted(LOADERS), help="sumber/format data ayat")
    ap.add_argument("--ayat-dir", type=Path, default=PROJECT_DIR / "data" / "ayat")
    ap.add_argument("--out-dir", type=Path, default=PROJECT_DIR / "data" / "waqf")
    ap.add_argument("--surah", type=int, nargs="*", help="batasi ke surah tertentu (default: semua)")
    args = ap.parse_args(argv)

    if not args.ayat_dir.is_dir():
        print(f"Folder tidak ditemukan: {args.ayat_dir}", file=sys.stderr)
        return 1
    args.out_dir.mkdir(parents=True, exist_ok=True)

    records, summary = build(args.source, args.ayat_dir, args.surah)
    json_path = args.out_dir / f"waqf_{args.source}.json"
    csv_path = args.out_dir / f"waqf_{args.source}.csv"
    write_json(json_path, args.source, records, summary)
    write_csv(csv_path, records)

    print(f"Sumber          : {args.source}")
    print(f"Ayat diproses   : {summary['ayat_processed']} (ada waqaf: {summary['ayat_with_waqf']})")
    print(f"Total tanda     : {summary['total_signs']}  {summary['by_position']}")
    for c, v in summary["by_sign"].items():
        print(f"  {c} {v['sign']} {v['kind']:<9} {v['count']:>5}  (akhir {v['akhir']}, tengah {v['tengah']})")
    if summary["other_marks_not_waqf"]:
        print("Tanda lain (bukan waqaf):")
        for c, v in summary["other_marks_not_waqf"].items():
            print(f"  {c} {v['char']} {v['name']}: {v['count']}x, contoh {', '.join(v['examples'])}")
    if summary["ayat_words_from_arabic_split"]:
        print(f"Ayat tanpa arabic_words (dipecah dari teks): {summary['ayat_words_from_arabic_split']}")
    if summary["mismatch_arabic_vs_words"]:
        print(f"PERINGATAN: {len(summary['mismatch_arabic_vs_words'])} ayat jumlah tandanya berbeda antara `arabic` dan `arabic_words`")
    if summary["surah_file_missing"]:
        m = summary["surah_file_missing"]
        print(f"File surah belum ada ({len(m)}): {m[:10]}{'...' if len(m) > 10 else ''}")
    print(f"\nJSON: {json_path}\nCSV : {csv_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())