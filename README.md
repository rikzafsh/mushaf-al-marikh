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
Satu halaman = 15 baris (halaman 1 dan 2 = 7 baris, diatur di `SPECIAL_PAGE_LINES`; angka itu
sudah termasuk baris header dan basmalah).

Setiap awal surah: **1 baris header** (nama surah, urutan, jumlah ayat) lalu **1 baris basmalah**
rata tengah — kecuali Al-Fatihah (basmalah sudah ayat 1) dan At-Taubah (`NO_BASMALAH_SURAHS`).
Baris-baris ini ikut dihitung dalam 15 baris, jadi baris teks berkurang sesuai jumlah surah
yang dimulai di halaman itu; teks surah baru selalu mulai di baris baru.
Bagian **mengalir**: seluruh kata di satu halaman dibagi seimbang ke semua baris
(`partition_lines` di `mushaf_data.py`), lalu warna mengikuti bagiannya, sehingga
pergantian bagian bisa terjadi di tengah baris. Rentang ayat tiap bagian ditampilkan
sebagai label berwarna di bawah halaman (tanda `*` = bagian dimulai/berakhir di tengah ayat).
Jika `arabic_words` bernilai `null`, kata dipecah dari field `arabic` per spasi.

### Tampilan 2 halaman
Mengikuti mushaf: `2 1`, `4 3`, `6 5`, ... (genap di kiri, ganjil di kanan).

## Catchword, angka, tema, layar penuh

- **Catchword**: satu kata pertama halaman berikutnya di pojok kiri bawah; dua kata bila kata
  pertama pendek (huruf dasar <= `CATCHWORD_SHORT`, default 3, di `mushaf_data.py`).
  Halaman terakhir tidak punya catchword.
- **Angka Arabic-Indic** (nomor ayat, nomor halaman, urutan surah, jumlah ayat) memakai fon
  angka terpisah, `--num-font` di `style.css` (Noto Naskh Arabic / Amiri / Traditional Arabic /
  Segoe UI, mana yang tersedia). Selain itu angka Arab dikeluarkan dari fon LPMQ lewat
  `unicode-range`. Untuk fon pilihan sendiri, tambahkan `@font-face` lalu taruh namanya paling
  depan di `--num-font`.
- **Mode gelap/terang**: tombol di toolbar; pilihan tersimpan di browser. Sebelum memilih,
  mengikuti pengaturan sistem.
- **Layar penuh**: tombol di toolbar atau tombol `F`. Toolbar tersembunyi dan muncul saat
  kursor ke tepi atas; halaman diperbesar menyesuaikan tinggi layar. Pindah halaman tidak
  memuat ulang browser, sehingga layar penuh tidak terlepas. Tanpa Fullscreen API (mis. iPhone)
  dipakai tampilan penuh di dalam jendela.

## Kata kunci hafalan

Di pinggir luar halaman (kanan untuk halaman kanan, kiri untuk halaman kiri) tiap halaman punya
baris-baris kata kunci, masing-masing sejajar dengan baris teks yang memuatnya dan berwarna
sesuai bloknya:

| baris | bentuk |
|---|---|
| awal halaman | `kata pertama …` |
| akhir ayat | `kata terakhir ‹nomor ayat› kata pertama ayat berikutnya` |
| batas blok di tengah ayat | `kata terakhir (nama tanda waqaf) kata pertama blok berikutnya` |
| akhir halaman | `… kata terakhir` |

Aturan jumlah kata (semua dapat diubah di bagian "Kata kunci hafalan" pada `mushaf_data.py`):
- Kata awal: satu kata; dua kata bila kata pertama pendek (`KEYWORD_SHORT`, default <= 3 huruf)
  atau termasuk kata lemah (`KEYWORD_WEAK_WORDS`, mis. `واذا`).
- Kata akhir: satu kata; dua kata bila kata itu pendek, atau bila kata di depannya penafian
  (`KEYWORD_NEGATORS`: لا لم لن), mis. `لا يشعرون`.
- Batas blok di tengah ayat: selalu dua kata di kedua sisi. Nama tanda waqaf yang tampil:
  صلى (ۖ), قلى (ۗ), م (ۘ), لا (ۙ), ج (ۚ), ∴ (ۛ), س (ۜ); bila tidak ada tanda, tampil `|`.
- Kata tidak melewati batas ayat; kata ditulis tanpa harakat (`KEYWORD_STRIP_DIACRITICS = False`
  untuk memakai harakat). Nomor ayat memakai angka Arabic-Indic dengan fon angka.
- Baris yang bertumpuk pada satu baris teks disusun berurutan di sekitar baris asalnya.

Tombol "Kata kunci" di toolbar menyembunyikannya (margin kembali sempit). Lebar kolom diatur
oleh `--kw-col` di `style.css`.

## Fitur
- Lompat ke surah atau nomor halaman; tombol 1 / 2 halaman
- Navigasi keyboard: `←` berikutnya, `→` sebelumnya (arah baca kanan ke kiri), `F` layar penuh
- Warna bagian bisa dimatikan (tersimpan di browser)
- Teks satu halaman otomatis mengecil bersama bila ada baris yang terlalu padat
- API: `GET /api/page/<n>` (JSON halaman)

## Tanda thumn (۞) dan keterangan hizb

```bash
python convert_thumn.py thumn_fix.csv     # CSV -> data/thumn.json (480 thumn = 60 hizb x 8)
python validate_data.py                   # ikut mengecek posisi thumn
```

- `data/thumn.json` dipakai otomatis oleh aplikasi. Tiap thumn diberi tanda ۞ tepat di
  awalnya: `Word_Count` kosong = awal ayat, `Word_Count` = N = di tengah ayat, setelah N
  kata pertama. Yang dihitung adalah **kata asli**: token yang hanya berisi tanda waqaf
  (mis. `ۗ`, `ەۙ`) tidak dihitung dan ikut kata sebelumnya, sehingga ۞ jatuh tepat setelah
  tanda waqaf tersebut. Pengaturan: `THUMN_WC_REAL_WORDS` (thumn.json) dan
  `SECTION_WC_REAL_WORDS` (word_count di mushaf.json) di `mushaf_data.py`; ubah ke `False`
  untuk menghitung semua token. `python validate_data.py` menampilkan kedua hasilnya.
- ۞ bawaan di data ayat dibuang lebih dulu (token yang hanya berisi ۞ ikut dibuang agar
  tidak dihitung sebagai kata). Fungsinya: `clean_words` di `mushaf_data.py`.
- Baris yang memuat ۞ diberi keterangan di pinggir luar halaman: kanan untuk halaman kanan
  (ganjil), kiri untuk halaman kiri (genap). Isinya pecahan hizb yang sudah dilalui:
  `awal hizb N`, `1/8`, `1/4`, `3/8`, `1/2`, `5/8`, `3/4`, `7/8` + `hizb N`.
  Penamaan ada di tabel `FRACTIONS` pada `convert_thumn.py`.

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