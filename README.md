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

## Catatan
- Font Arab (Amiri Quran / Scheherazade New) dimuat dari Google Fonts. Untuk offline,
  taruh file font di `static/` dan tambahkan `@font-face` di `style.css`.
- Penanda awal surah berupa label kecil di tepi atas baris, tidak memakai baris sendiri.
