"""Cek konsistensi data:  python validate_data.py"""
import sys
from pathlib import Path

from extract_waqf import WAQF_SIGNS, is_standalone_sign
from mushaf_data import MushafData

m = MushafData(Path(sys.argv[1])) if len(sys.argv) > 1 else MushafData()
print(f"Halaman        : {m.total_pages}")
print(f"Surah          : {len(m.surah_list)}")
have = m.available_surahs()
print(f"File ayat ada  : {len(have)} surah -> {have if len(have) <= 20 else str(have[:20]) + '...'}")
missing = [i for i in m.surahs if i not in have]
if missing:
    print(f"File ayat belum ada ({len(missing)}): data/ayat/<id>.json untuk id {missing[:15]}{'...' if len(missing) > 15 else ''}")
if m.issues:
    print(f"\n{len(m.issues)} masalah pada mushaf.json:")
    for i in m.issues[:50]:
        print(" -", i)
else:
    print("\nmushaf.json konsisten (semua section berurutan sampai 114:6).")

# Cek kata: word_count tidak boleh melebihi jumlah kata ayat
bad = 0
for page, secs in m._layout.items():
    for s in secs:
        sid, a, wc = s["end"]
        rec = (m.ayat(sid) or {}).get(a)
        if rec and wc is not None and wc >= len(m._words(rec)):
            bad += 1
            print(f" - hal {page}: word_count {wc} >= jumlah kata {len(m._words(rec))} di {sid}:{a}")
nulls = 0
for sid in have:
    for a, rec in (m.ayat(sid) or {}).items():
        if not rec.get("arabic_words"):
            nulls += 1
if nulls:
    print(f"{nulls} ayat tanpa arabic_words -> kata dipecah dari field `arabic` per spasi")
print("word_count OK" if not bad else f"{bad} word_count bermasalah")


# ---- thumn ---------------------------------------------------------------
if not m.thumn:
    print("\nthumn.json belum ada (jalankan: python convert_thumn.py thumn_fix.csv)")
else:
    lost, outside = [], []
    pages = {}
    for t in m.thumn:
        idx = t["word_count"] or 0
        page = m.page_of(t["surah"], t["ayah"], idx)
        if page is None:
            lost.append(t["no"])
            continue
        pages.setdefault(page, []).append(t["no"])
        rec = (m.ayat(t["surah"]) or {}).get(t["ayah"])
        if rec:
            n_words = len(m._words(rec))
            if idx >= n_words:
                outside.append(f'#{t["no"]} {t["surah"]}:{t["ayah"]} word_count {idx} >= jumlah kata {n_words}')
    print(f"\nthumn: {len(m.thumn)} data, jatuh pada {len(pages)} halaman")
    print("semua thumn menemukan halamannya" if not lost else f"thumn tanpa halaman: {lost}")
    for o in outside[:30]:
        print(" -", o)
    multi = {p: ns for p, ns in pages.items() if len(ns) > 1}
    if multi:
        print("halaman dengan lebih dari satu thumn:", {p: ns for p, ns in list(multi.items())[:10]})


# ---- thumn di tengah ayat (Word_Count terisi) -------------------------------
import mushaf_data as md


def _ctx(words, cut):
    """Teks di sekitar titik potong: '... kata-sebelum | kata-sesudah ...'."""
    before = words[max(0, cut - 2):cut]
    # tampilkan kata asli terakhir + token tandanya
    after = words[cut:cut + 1]
    return f"... {' '.join(before)} ۞ {' '.join(after)} ..."


mid = [t for t in m.thumn if t["word_count"]]
if mid:
    print(f"\nThumn di tengah ayat: {len(mid)}  (THUMN_WC_REAL_WORDS = {md.THUMN_WC_REAL_WORDS})")
    print("Dua cara hitung word_count: 'kata asli' (token tanda tidak dihitung) dan 'token' (semua item).")
    print("Cara yang dipakai ditandai <== . Yang benar biasanya jatuh tepat setelah tanda waqaf.\n")
    for t in mid:
        rec = (m.ayat(t["surah"]) or {}).get(t["ayah"])
        head = f'#{t["no"]:<3} {t["label"]:<11} {t["surah"]}:{t["ayah"]} wc={t["word_count"]:<3} hal {t["page"]}'
        if not rec:
            print(f"{head}  | data ayat belum ada")
            continue
        words = m._words(rec)
        n = t["word_count"]
        cuts = {mode: md.raw_cut(words, n, mode) for mode in (True, False)}
        if min(cuts.values()) >= len(words):
            print(f"{head}  | !! word_count >= jumlah kata ({len(words)}), ۞ TIDAK bisa dipasang")
            continue
        print(head)
        same = cuts[True] == cuts[False]
        for mode, name in ((True, "kata asli"), (False, "token    ")):
            if same and not mode:
                continue
            label = name if not same else "keduanya "
            mark = "  <==" if md.THUMN_WC_REAL_WORDS == mode or same else ""
            c = cuts[mode]
            ok = any(ch in md.SIGN_CHARS for ch in words[c - 1]) if c > 0 else False
            print(f"      {label}: {_ctx(words, c)}{mark}{'' if ok else '   (tidak tepat setelah tanda waqaf)'}")

# ---- batas bagian di tengah ayat pada mushaf.json -----------------------------
ends = [(sid, a, wc) for secs in m._layout.values() for sp in secs
        for (sid, a, wc) in [sp["end"]] if wc is not None]
tot = {True: 0, False: 0}
used = 0
for sid, a, wc in ends:
    rec = (m.ayat(sid) or {}).get(a)
    if not rec:
        continue
    words = m._words(rec)
    used += 1
    for mode in (True, False):
        c = md.raw_cut(words, wc, mode)
        if 0 < c < len(words) and any(ch in md.SIGN_CHARS for ch in words[c - 1]):
            tot[mode] += 1
if used:
    print(f"\nBatas bagian di tengah ayat (mushaf.json): {used} dari {len(ends)} punya data ayat")
    print(f"  jatuh tepat setelah tanda waqaf -> kata asli: {tot[True]}, token: {tot[False]}"
          f"   (SECTION_WC_REAL_WORDS = {md.SECTION_WC_REAL_WORDS})")