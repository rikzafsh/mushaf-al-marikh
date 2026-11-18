"""Cek konsistensi data:  python validate_data.py"""
from mushaf_data import MushafData

m = MushafData()
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
        if rec and wc is not None and wc >= len(rec["arabic_words"]):
            bad += 1
            print(f" - hal {page}: word_count {wc} >= jumlah kata {len(rec['arabic_words'])} di {sid}:{a}")
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