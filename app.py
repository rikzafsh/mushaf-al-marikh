from __future__ import annotations

from flask import Flask, jsonify, redirect, render_template, request, url_for

from mushaf_data import SECTION_COLORS, SECTION_LABELS, MushafData

app = Flask(__name__)
mushaf = MushafData()

_AR_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


@app.template_filter("ar_digits")
def ar_digits(value) -> str:
    return str(value).translate(_AR_DIGITS)


def _int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _spread(page: int, view: int, total: int) -> list[int]:
    """Nomor halaman yang ditampilkan, urut KIRI -> KANAN di layar.
    Seperti mushaf: 2 1 / 4 3 / 6 5 ... (genap di kiri, ganjil di kanan)."""
    if view == 1:
        return [page]
    left = page if page % 2 == 0 else page + 1
    left = min(left, total - total % 2)   # jaga bila total ganjil
    return [left, left - 1]


@app.route("/")
def home():
    return redirect(url_for("viewer"))


@app.route("/mushaf")
def viewer():
    view = 2 if request.args.get("view") == "2" else 1
    page = _int(request.args.get("page"), 1)
    surah = _int(request.args.get("surah"), 0)
    if surah in mushaf.surahs:
        page = mushaf.surahs[surah]["page"]
    page = max(1, min(mushaf.total_pages, page))

    numbers = _spread(page, view, mushaf.total_pages)
    pages = [mushaf.page(n) for n in numbers]  # None => halaman kosong
    if view == 1:
        prev_page = page - 1 if page > 1 else None
        next_page = page + 1 if page < mushaf.total_pages else None
    else:
        left = numbers[0]
        prev_page = left - 2 if left - 2 >= 2 else None
        next_page = left + 2 if left + 2 <= mushaf.total_pages else None

    shown = sorted(n for n in numbers if 1 <= n <= mushaf.total_pages)
    spread_label = f"Halaman {shown[0]}" if len(shown) == 1 else f"Halaman {shown[0]}–{shown[-1]}"
    current_surah = next((p["surahs"][0]["id"] for p in pages if p), 0)

    return render_template(
        "viewer.html",
        pages=pages,
        numbers=numbers,
        view=view,
        page=page,
        total_pages=mushaf.total_pages,
        prev_page=prev_page,
        next_page=next_page,
        spread_label=spread_label,
        surahs=mushaf.surah_list,
        current_surah=current_surah,
        legend=list(zip(SECTION_COLORS, SECTION_LABELS)),
        available=set(mushaf.available_surahs()),
    )


@app.route("/api/page/<int:n>")
def api_page(n: int):
    data = mushaf.page(n)
    if data is None:
        return jsonify(error="halaman tidak ditemukan"), 404
    return jsonify(data)


if __name__ == "__main__":
    for issue in mushaf.issues:
        print("PERINGATAN data:", issue)
    app.run(debug=True)
