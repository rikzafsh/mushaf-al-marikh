"""Lapisan data Mushaf Al-Marikh.

Membaca:
  data/mushaf.json      -> pembagian tiap halaman menjadi 5 bagian (section)
  data/surah-list.json  -> daftar 114 surah
  data/ayat/<id>.json   -> ayat per surah (format sama dengan 1.json)

Aturan pada mushaf.json:
  * Setiap section hanya menyimpan AKHIR rentangnya: (surah, ayat_end, word_count).
  * Awal section = posisi tepat setelah akhir section sebelumnya.
  * word_count != null berarti section berakhir DI TENGAH ayat tersebut, yaitu
    setelah kata ke-N (kumulatif dari awal ayat). null = berakhir di ujung ayat.
  * Satu section boleh melintasi batas surah (mis. akhir Ad-Duha + awal Asy-Syarh).
"""
from __future__ import annotations

import json
import unicodedata
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

GRID_ROWS = 15  # jumlah baris satu halaman
# Halaman dengan jumlah baris khusus: halaman 1 dan 2 hanya 7 baris
# (TERMASUK baris header surah dan basmalah).
SPECIAL_PAGE_LINES = {1: 7, 2: 7}

# Surah tanpa baris basmalah: Al-Fatihah (basmalah sudah ayat 1) dan At-Taubah.
NO_BASMALAH_SURAHS = {1, 9}
BASMALAH_FALLBACK = "بِسْمِ اللّٰهِ الرَّحْمٰنِ الرَّحِيْمِ"

SECTION_COLORS = ["red", "yellow", "green", "blue", "purple"]
SECTION_LABELS = ["Merah", "Kuning", "Hijau", "Biru muda", "Ungu"]


# --------------------------------------------------------------------------
# Utilitas teks
# --------------------------------------------------------------------------
THUMN_SIGN = "\u06DE"  # ۞ (tanda awal rub'/thumn)

# Cara menghitung `word_count`:
#   True  -> hitung KATA ASLI saja; token yang hanya berisi tanda waqaf (mis. "ۗ", "ەۙ")
#            tidak dihitung dan ikut kata sebelumnya.
#   False -> hitung semua item `arabic_words` / hasil pecah spasi (token tanda ikut dihitung).
SECTION_WC_REAL_WORDS = True   # word_count pada mushaf.json
THUMN_WC_REAL_WORDS = True     # Word_Count pada thumn.json

SIGN_CHARS = set("\u06D6\u06D7\u06D8\u06D9\u06DA\u06DB\u06DC")  # tanda waqaf
_PLACEHOLDERS = {"\u06D5", "\u0640"}
_OTHER_RANGES = [(0x06DD, 0x06DE), (0x06E9, 0x06E9), (0x08D3, 0x08FF)]


def _is_other_mark(ch: str) -> bool:
    o = ord(ch)
    return any(a <= o <= b for a, b in _OTHER_RANGES)


def is_sign_token(token: str) -> bool:
    """True bila token hanya berisi tanda (waqaf / anotasi), tanpa huruf kata sebenarnya."""
    for ch in token:
        if ch in SIGN_CHARS or ch in _PLACEHOLDERS or ch.isspace() or _is_other_mark(ch):
            continue
        if unicodedata.category(ch).startswith("L"):
            return False
    return True


def clean_words(words: list[str]) -> list[str]:
    """Bersihkan daftar kata:
    * buang ۞ bawaan (dipasang ulang dari thumn.json); token yang hanya ۞ dibuang,
    * tanda waqaf yang menempel di AWAL kata (mis. "ۗوَلَقَدْ") dipindah ke akhir kata sebelumnya,
      supaya tanda itu tidak berada di depan kata berikutnya."""
    out: list[str] = []
    for w in words:
        w = " ".join(w.replace(THUMN_SIGN, "").split())
        if not w:
            continue
        k = 0
        while k < len(w) and w[k] in SIGN_CHARS:
            k += 1
        if 0 < k < len(w) and out and not is_sign_token(w):
            out[-1] += w[:k]
            w = w[k:]
        out.append(w)
    return out


def raw_cut(words: list[str], n: int, real_words: bool) -> int:
    """Ubah 'n kata' menjadi indeks item (0-based) tempat berhenti.
    Mode kata asli: berhenti setelah kata asli ke-n beserta token tanda yang langsung menyusulnya.
    Mengembalikan len(words) bila n melebihi jumlah kata."""
    if not real_words or n <= 0:
        return min(n, len(words)) if n > 0 else 0
    count = 0
    for idx, w in enumerate(words):
        if not is_sign_token(w):
            count += 1
            if count == n:
                j = idx + 1
                while j < len(words) and is_sign_token(words[j]):
                    j += 1
                return j
    return len(words)


def base_len(text: str) -> int:
    """Jumlah huruf dasar (tanpa harakat/tanda baca kecil) -> perkiraan lebar kata."""
    return sum(1 for c in text if not unicodedata.category(c).startswith("M"))


def partition_all(weights: list[float], kmax: int):
    """Tabel DP pembagian `weights` ke k baris untuk SEMUA k = 1..kmax (minimal jumlah kuadrat
    bobot tiap baris => baris seimbang). Mengembalikan (dp, cut); dp[k][n] = biaya k baris."""
    n = len(weights)
    kmax = max(1, min(kmax, n))
    pre = [0.0]
    for w in weights:
        pre.append(pre[-1] + w)
    inf = float("inf")
    dp = [[inf] * (n + 1) for _ in range(kmax + 1)]
    cut = [[0] * (n + 1) for _ in range(kmax + 1)]
    dp[0][0] = 0.0
    for j in range(1, kmax + 1):
        for i in range(j, n + 1):
            best, arg = inf, j - 1
            for m in range(j - 1, i):
                prev = dp[j - 1][m]
                if prev == inf:
                    continue
                c = prev + (pre[i] - pre[m]) ** 2
                if c < best:
                    best, arg = c, m
            dp[j][i], cut[j][i] = best, arg
    return dp, cut


def partition_sizes(cut, n: int, k: int) -> list[int]:
    """Ukuran (jumlah token) tiap baris untuk pembagian n token ke k baris."""
    sizes, i = [], n
    for j in range(k, 0, -1):
        m = cut[j][i]
        sizes.append(i - m)
        i = m
    return sizes[::-1]


def partition_lines(weights: list[float], k: int) -> list[int]:
    """Bagi bobot menjadi tepat k baris (baris kosong di akhir bila token < k)."""
    n = len(weights)
    if n == 0:
        return [0] * k
    if n <= k:
        return [1] * n + [0] * (k - n)
    _, cut = partition_all(weights, k)
    return partition_sizes(cut, n, k)


# --------------------------------------------------------------------------
# Data mushaf
# --------------------------------------------------------------------------
class MushafData:
    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = Path(data_dir)
        with open(self.data_dir / "surah-list.json", encoding="utf-8") as f:
            self.surah_list = json.load(f)
        self.surahs = {s["id"]: s for s in self.surah_list}
        with open(self.data_dir / "mushaf.json", encoding="utf-8") as f:
            raw = json.load(f)
        self.issues: list[str] = []
        self._layout = self._build_layout(raw["pages"])
        self.total_pages = len(self._layout)
        self.thumn = self._load_thumn()
        # {(surah, ayat): {indeks_kata_awal(0-based): record}}
        self.thumn_at: dict[tuple[int, int], dict[int, dict]] = {}
        for t in self.thumn:
            self.thumn_at.setdefault((t["surah"], t["ayah"]), {})[t["word_count"] or 0] = t
        self.page = lru_cache(maxsize=700)(self._page)

    # ---- ayat ----------------------------------------------------------
    @lru_cache(maxsize=120)
    def ayat(self, surah_id: int):
        """dict {nomor_ayat: record} atau None bila file surah belum ada."""
        path = self.data_dir / "ayat" / f"{surah_id}.json"
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            rows = json.load(f)
        return {r["ayah"]: r for r in rows}

    def available_surahs(self) -> list[int]:
        return [i for i in self.surahs if (self.data_dir / "ayat" / f"{i}.json").exists()]

    # ---- layout --------------------------------------------------------
    def _next_pos(self, s: int, a: int) -> tuple[int, int]:
        if a < self.surahs[s]["num_ayah"]:
            return s, a + 1
        return s + 1, 1

    def _build_layout(self, pages: list[dict]) -> dict[int, list[dict]]:
        layout: dict[int, list[dict]] = {}
        cursor = (1, 1, 0)  # surah, ayat, jumlah kata yang sudah terpakai
        for p in pages:
            secs = []
            for sec in p["sections"]:
                end = (sec["surah"], sec["ayat_end"], sec["word_count"])
                start = cursor
                label = f"p{p['page']}/s{sec['section']}"
                if (start[0], start[1]) > (end[0], end[1]):
                    self.issues.append(f"{label}: awal {start[:2]} melewati akhir {end[:2]}")
                elif (start[0], start[1]) == (end[0], end[1]) and end[2] is not None and end[2] <= start[2]:
                    self.issues.append(f"{label}: word_count {end[2]} <= offset {start[2]}")
                secs.append({"start": start, "end": end})
                if end[2] is not None:
                    cursor = (end[0], end[1], end[2])
                else:
                    cursor = (*self._next_pos(end[0], end[1]), 0)
            layout[p["page"]] = secs
        last = self.surahs[114]
        if cursor[:2] != (115, 1):
            self.issues.append(f"akhir mushaf di {cursor}, seharusnya selesai di 114:{last['num_ayah']}")
        return layout

    # ---- thumn -----------------------------------------------------------
    def _load_thumn(self) -> list[dict]:
        path = self.data_dir / "thumn.json"
        if not path.exists():
            return []
        with open(path, encoding="utf-8") as f:
            return json.load(f)["records"]

    def page_of(self, surah: int, ayah: int, word_index: int = 0):
        """Nomor halaman yang memuat posisi (surah, ayat, indeks kata 0-based)."""
        pos = (surah, ayah, word_index)
        for n, secs in self._layout.items():
            for sp in secs:
                en = sp["end"]
                end_pos = (en[0], en[1], en[2] if en[2] is not None else 10 ** 9)
                if sp["start"] <= pos < end_pos:
                    return n
        return None

    # ---- halaman -------------------------------------------------------
    @staticmethod
    def _words(rec):
        """Daftar kata ayat. Bila arabic_words null/kosong, pecah teks `arabic` per spasi."""
        words = rec.get("arabic_words")
        if not words:
            words = (rec.get("arabic") or "").split()
        return clean_words(words)

    def _section_tokens(self, start, end, sec_index):
        s0, a0, off = start
        s1, a1, wc = end
        tokens: list[dict] = []
        missing: set[int] = set()
        s, a = s0, a0
        while (s, a) <= (s1, a1) and s <= 114:
            is_first_of_surah = a == 1 and ((s, a) != (s0, a0) or off == 0)
            data = self.ayat(s)
            rec = data.get(a) if data else None
            words = self._words(rec) if rec else []
            if not words:
                missing.add(s)
            else:
                first = raw_cut(words, off, SECTION_WC_REAL_WORDS) if (s, a) == (s0, a0) else 0
                last = (raw_cut(words, wc, SECTION_WC_REAL_WORDS)
                        if ((s, a) == (s1, a1) and wc is not None) else len(words))
                complete = last >= len(words)
                added = 0
                marks = {raw_cut(words, k, THUMN_WC_REAL_WORDS): v
                         for k, v in self.thumn_at.get((s, a), {}).items()}
                pending = None
                for i in range(first, min(last, len(words))):
                    w = words[i]
                    if i in marks:
                        pending = marks[i]
                    # tanda baca kecil (mis. "ەۙ") digabung ke kata sebelumnya
                    if added and base_len(w) <= 1:
                        tokens[-1]["text"] += " " + w
                    else:
                        tokens.append({"text": w, "end": None, "sec": sec_index, "header": None,
                                       "thumn": pending})
                        pending = None
                        if added == 0 and is_first_of_surah:
                            tokens[-1]["header"] = self.surahs[s]
                    added += 1
                if complete and tokens:
                    tokens[-1]["end"] = a
            s, a = self._next_pos(s, a)
        return tokens, missing

    @staticmethod
    def _range_label(start, end):
        s0, a0, off = start
        s1, a1, wc = end
        label = f"{s0}:{a0}" if a0 == a1 and s0 == s1 else (
            f"{s0}:{a0}–{a1}" if s0 == s1 else f"{s0}:{a0}–{s1}:{a1}")
        return label + ("*" if off or wc is not None else "")

    def _page(self, n: int):
        """Satu halaman = rangkaian kata yang MENGALIR melintasi semua bagian.
        Kata dibagi seimbang ke N baris; pergantian bagian (warna) bisa terjadi
        di tengah baris."""
        if n not in self._layout:
            return None
        specs = self._layout[n]
        total_lines = SPECIAL_PAGE_LINES.get(n, GRID_ROWS)
        row_start = (GRID_ROWS - total_lines) // 2 + 1

        tokens, missing, sections, surah_ids, juz = [], set(), [], [], None
        for i, spec in enumerate(specs):
            toks, miss = self._section_tokens(spec["start"], spec["end"], i)
            tokens += toks
            missing |= miss
            for sid in range(spec["start"][0], spec["end"][0] + 1):
                if sid not in surah_ids:
                    surah_ids.append(sid)
            if juz is None:
                rec = (self.ayat(spec["start"][0]) or {}).get(spec["start"][1])
                juz = rec.get("juz") if rec else None
            sections.append({
                "index": i + 1,
                "color": SECTION_COLORS[i % 5],
                "color_label": SECTION_LABELS[i % 5],
                "label": self._range_label(spec["start"], spec["end"]),
            })

        lines: list[dict] = []
        warnings: list[str] = []
        if not missing:
            lines, warnings = self._layout_lines(n, tokens, sections, total_lines, row_start)
        return {
            "number": n,
            "juz": juz,
            "surahs": [self.surahs[s] for s in surah_ids],
            "sections": sections,
            "line_count": total_lines,
            "row_start": row_start,
            "lines": lines,
            "warnings": warnings,
            "missing": sorted(missing),
        }

    def basmalah_text(self) -> str:
        rec = (self.ayat(1) or {}).get(1)
        text = " ".join(self._words(rec)) if rec else ""
        return text or BASMALAH_FALLBACK

    def _layout_lines(self, n, tokens, sections, total_lines, row_start):
        """Susun baris halaman: header surah (1 baris) + basmalah (1 baris, rata tengah,
        kecuali surah 1 dan 9) di setiap awal surah, sisanya baris teks yang mengalir.
        Seluruhnya = total_lines baris. Teks surah baru selalu mulai di baris baru."""
        warnings: list[str] = []
        # --- pecah token menjadi segmen: lanjutan surah sebelumnya + tiap surah yang dimulai
        segs: list[dict] = []
        for t in tokens:
            if t["header"] or not segs:
                segs.append({"surah": t["header"], "tokens": []})
            segs[-1]["tokens"].append(t)

        def blocks(with_header=True, with_basmalah=True):
            return sum((1 if with_header else 0) + (1 if with_basmalah and sg["surah"]["id"] not in NO_BASMALAH_SURAHS else 0)
                       for sg in segs if sg["surah"])

        with_header, with_basmalah = True, True
        L = total_lines - blocks()
        if L < len(segs):
            with_basmalah = False
            L = total_lines - blocks(with_basmalah=False)
            warnings.append("baris tidak cukup: basmalah dihilangkan")
        if L < len(segs):
            with_header = False
            L = total_lines - blocks(False, False)
            warnings.append("baris tidak cukup: header surah dihilangkan")

        # --- alokasi jumlah baris teks per segmen (biaya total minimum)
        weights = [[base_len(t["text"]) + 1 + (2 if t["end"] else 0) + (2 if t["thumn"] else 0)
                    for t in sg["tokens"]] for sg in segs]
        tables = []
        for w in weights:
            dp, cut = partition_all(w, L)
            tables.append((dp, cut, min(len(w), L)))
        inf = float("inf")
        J = min(L, sum(k for _, _, k in tables))
        f = [[inf] * (J + 1) for _ in range(len(segs) + 1)]
        back = [[0] * (J + 1) for _ in range(len(segs) + 1)]
        f[0][0] = 0.0
        for i, (dp, _, kmax) in enumerate(tables, 1):
            for j in range(i, J + 1):
                for k in range(1, min(kmax, j) + 1):
                    c = f[i - 1][j - k] + dp[k][len(weights[i - 1])]
                    if c < f[i][j]:
                        f[i][j], back[i][j] = c, k
        alloc, j = [0] * len(segs), J
        for i in range(len(segs), 0, -1):
            alloc[i - 1] = back[i][j]
            j -= alloc[i - 1]

        # --- rakit baris berurutan
        lines: list[dict] = []
        row = row_start
        for sg, (dp, cut, _), w, k in zip(segs, tables, weights, alloc):
            sid = sg["surah"]["id"] if sg["surah"] else None
            if sid and with_header:
                lines.append({"type": "header", "row": row, "surah": sg["surah"]})
                row += 1
                if with_basmalah and sid not in NO_BASMALAH_SURAHS:
                    lines.append({"type": "basmalah", "row": row, "text": self.basmalah_text()})
                    row += 1
            toks, pos = sg["tokens"], 0
            for sz in partition_sizes(cut, len(w), k) if k else []:
                chunk = toks[pos:pos + sz]
                pos += sz
                runs = []
                for t in chunk:
                    if not runs or runs[-1]["sec"] != t["sec"]:
                        runs.append({"sec": t["sec"], "color": sections[t["sec"]]["color"],
                                     "label": sections[t["sec"]]["label"], "tokens": []})
                    runs[-1]["tokens"].append(t)
                lines.append({
                    "type": "text",
                    "row": row,
                    "runs": runs,
                    "sparse": len(chunk) < 4,
                    "notes": [t["thumn"] for t in chunk if t["thumn"]],
                })
                row += 1
        if row - row_start != total_lines:
            warnings.append(f"jumlah baris {row - row_start} dari {total_lines}")
        return lines, warnings