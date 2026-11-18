# Mushaf Al-Marikh

Penampil mushaf berbasis Flask: 604 halaman, **15 baris per halaman**, tiap halaman
dibagi **5 bagian berwarna** (merah, kuning, hijau, biru muda, ungu), dengan tampilan
**1 halaman** atau **2 halaman** (urutan 2 1, 4 3, 6 5, ...).

## Menjalankan

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python validate_data.py     # cek data (opsional)
python app.py               # buka http://127.0.0.1:5000
```

## Data

```
data/
├── mushaf.json        # pembagian halaman -> 5 section (sudah ada)
├── surah-list.json    # 114 surah (sudah ada)
└── ayat/
    ├── 1.json         # contoh (Al-Fatihah)
    ├── 2.json         # <- tambahkan sampai 114.json, format sama dengan 1.json
    └── ...
```

Surah yang file ayatnya belum ada tetap muncul di bagian yang tepat, berisi catatan
"Data surah N belum ada" (di dropdown ditandai •).

### Cara mushaf.json dibaca
- Tiap section hanya menyimpan **akhir** rentang: `surah`, `ayat_end`, `word_count`.
- Awal section = posisi tepat setelah akhir section sebelumnya.
- `word_count` berisi angka → section berakhir **di tengah ayat** setelah kata ke-N
  (kumulatif dari awal ayat, dihitung dari `arabic_words`). `null` → berakhir di ujung ayat.
- Section boleh melintasi batas surah (mis. 93:9 – 94:4 di halaman 596).
- Label kecil di kiri tiap bagian (mis. `2:6–7`) menunjukkan rentang ayatnya; tanda `*`
  berarti bagian itu dimulai/berakhir di tengah ayat.

### Pembagian baris dan bagian
Satu halaman = 15 baris (halaman 1 dan 2 = 7 baris, diatur di `SPECIAL_PAGE_LINES`).
Bagian **mengalir**: seluruh kata di satu halaman dibagi seimbang ke semua baris
(`partition_lines` di `mushaf_data.py`), lalu warna mengikuti bagiannya, sehingga
pergantian bagian bisa terjadi di tengah baris. Rentang ayat tiap bagian ditampilkan
sebagai label berwarna di bawah halaman (tanda `*` = bagian dimulai/berakhir di tengah ayat).
Jika `arabic_words` bernilai `null`, kata dipecah dari field `arabic` per spasi.

### Tampilan 2 halaman
Mengikuti mushaf: `2 1`, `4 3`, `6 5`, ... (genap di kiri, ganjil di kanan).

## Fitur
- Lompat ke surah atau nomor halaman; tombol 1 / 2 halaman
- Navigasi keyboard: `←` berikutnya, `→` sebelumnya (arah baca kanan ke kiri)
- Warna bagian bisa dimatikan (tersimpan di browser)
- Teks satu halaman otomatis mengecil bersama bila ada baris yang terlalu padat
- API: `GET /api/page/<n>` (JSON halaman)

## Data tanda waqaf

```bash
python extract_waqf.py                    # membaca data/ayat/*.json -> data/waqf/
python extract_waqf.py --surah 1 2        # hanya surah tertentu
python extract_waqf.py --ayat-dir D:\\data\\ayat --out-dir hasil
```

Keluaran: `data/waqf/waqf_<source>.json` (meta, ringkasan, semua record) dan
`data/waqf/waqf_<source>.csv` (satu baris per tanda; UTF-8 BOM agar terbaca benar di Excel).

Tiap tanda dicatat **setelah kata ke-N** dalam ayatnya:

| field | arti |
|---|---|
| `position` | `akhir` (setelah kata terakhir ayat) atau `tengah` |
| `word_index` / `total_words` | urutan kata asli; token yang hanya berisi tanda (mis. `ەۙ`) tidak dihitung |
| `token_index` | urutan item di `arabic_words` (sama dengan acuan `word_count` di mushaf.json) |
| `attached` | tanda menempel di kata (`ya`) atau token terpisah (`tidak`) |
| `sign`, `code`, `kind`, `name` | tanda (ۖ ۗ ۘ ۙ ۚ ۛ ۜ), kode Unicode, jenis, nama |

Ringkasan JSON juga memuat jumlah per tanda/posisi/surah, ayat dengan `arabic_words` null,
selisih jumlah tanda antara `arabic` dan `arabic_words`, serta tanda anotasi lain yang bukan
waqaf (mis. U+08D6 di akhir 1:7). Untuk mushaf lain, tambahkan fungsi pembaca di `LOADERS`
pada `extract_waqf.py` dan jalankan dengan `--source <nama>`.

## Catatan
- Fon Arab: **LPMQ IsepMisbah**. Simpan fail fon di `static/fonts/LPMQ IsepMisbah.ttf`
  (nama fail persis seperti itu). Tanpa fail tersebut, tampilan memakai fon cadangan sistem.
- Penanda awal surah berupa label kecil di tepi atas baris, tidak memakai baris sendiri.