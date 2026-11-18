"""Konversi data thumn (CSV) -> data/thumn.json

Pemakaian:
    python convert_thumn.py thumn_fix.csv              # -> data/thumn.json
    python convert_thumn.py thumn_fix.csv -o hasil.json

Kolom CSV (pemisah ;):  No;Juz;Hizb;Nisf;Rub;Thumn;No_Surah;Ayat_Awal;Word_Count

Arti posisi awal thumn:
  * Word_Count kosong -> thumn dimulai di AWAL ayat (sebelum kata ke-1).
  * Word_Count = N    -> thumn dimulai di TENGAH ayat, setelah N kata pertama
                         (sebelum kata ke-(N+1)); kata dihitung dari `arabic_words`.
    (Sama dengan acuan `word_count` pada mushaf.json.)

Keterangan margin (label) memakai pecahan hizb yang SUDAH dilalui saat thumn dimulai:
    thumn 1 = awal hizb, 2 = 1/8, 3 = 1/4, 4 = 3/8, 5 = 1/2, 6 = 5/8, 7 = 3/4, 8 = 7/8
Ubah tabel FRACTIONS di bawah bila ingin penamaan lain, lalu jalankan ulang skrip ini.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent

FRACTIONS = {1: None, 2: "1/8", 3: "1/4", 4: "3/8", 5: "1/2", 6: "5/8", 7: "3/4", 8: "7/8"}
START_WORD = "awal"
REQUIRED = ["No", "Juz", "Hizb", "Nisf", "Rub", "Thumn", "No_Surah", "Ayat_Awal", "Word_Count"]


def to_int(v: str):
    v = (v or "").strip()
    return int(v) if v else None


def convert(csv_path: Path) -> tuple[list[dict], list[str]]:
    problems: list[str] = []
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(f"Kolom CSV tidak ditemukan: {missing}")
        rows = list(reader)

    records, prev = [], None
    for i, r in enumerate(rows, 1):
        n = {k: to_int(r[k]) for k in REQUIRED}
        # konsistensi struktur: 60 hizb x 8 thumn
        exp_thumn = (i - 1) % 8 + 1
        exp_hizb = (i - 1) // 8 + 1
        for key, exp in (("No", i), ("Thumn", exp_thumn), ("Hizb", exp_hizb),
                         ("Juz", math.ceil(exp_hizb / 2)), ("Rub", math.ceil(exp_thumn / 2)),
                         ("Nisf", math.ceil(exp_thumn / 4))):
            if n[key] != exp:
                problems.append(f"baris {i}: {key}={n[key]}, seharusnya {exp}")
        pos = (n["No_Surah"], n["Ayat_Awal"], n["Word_Count"] or 0)
        if prev and pos <= prev:
            problems.append(f"baris {i}: posisi {pos} tidak berurutan setelah {prev}")
        prev = pos

        frac = FRACTIONS[n["Thumn"]]
        top = frac if frac else START_WORD
        bottom = f"hizb {n['Hizb']}"
        records.append({
            "no": n["No"], "juz": n["Juz"], "hizb": n["Hizb"], "nisf": n["Nisf"],
            "rub": n["Rub"], "thumn": n["Thumn"],
            "surah": n["No_Surah"], "ayah": n["Ayat_Awal"], "word_count": n["Word_Count"],
            "fraction": frac, "top": top, "bottom": bottom, "label": f"{top} {bottom}",
        })
    if len(records) != 480:
        problems.append(f"jumlah baris {len(records)}, seharusnya 480 (60 hizb x 8 thumn)")
    return records, problems


def add_pages(records: list[dict]) -> int:
    """Tambahkan nomor halaman (turunan dari mushaf.json). Mengembalikan jumlah yang tidak ketemu."""
    from mushaf_data import MushafData
    m = MushafData()
    miss = 0
    for r in records:
        page = m.page_of(r["surah"], r["ayah"], r["word_count"] or 0)
        r["page"] = page
        miss += page is None
    return miss


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="CSV thumn -> JSON")
    ap.add_argument("csv", type=Path)
    ap.add_argument("-o", "--out", type=Path, default=PROJECT_DIR / "data" / "thumn.json")
    args = ap.parse_args(argv)

    records, problems = convert(args.csv)
    not_found = add_pages(records)

    doc = {
        "source": args.csv.name,
        "total": len(records),
        "note": ("Awal thumn: word_count null = awal ayat; word_count N = setelah N kata pertama ayat. "
                 "page diturunkan dari mushaf.json."),
        "records": "__RECORDS__",
    }
    text = json.dumps(doc, ensure_ascii=False, indent=2)
    body = ",\n".join("    " + json.dumps(r, ensure_ascii=False) for r in records)
    text = text.replace('"__RECORDS__"', "[\n" + body + "\n  ]")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text + "\n", encoding="utf-8")

    print(f"{len(records)} thumn -> {args.out}")
    if not_found:
        print(f"PERINGATAN: {not_found} thumn tidak ditemukan pada halaman mana pun di mushaf.json")
    for p in problems[:30]:
        print("PERINGATAN:", p)
    if not problems and not not_found:
        print("Struktur data konsisten (60 hizb x 8 thumn, urut, semua menemukan halamannya).")
    return 0


if __name__ == "__main__":
    sys.exit(main())