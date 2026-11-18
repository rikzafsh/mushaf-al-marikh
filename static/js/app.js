(() => {
  "use strict";

  const KEY_COLORS = "mushaf-al-marikh:colors";
  const body = document.body;

  /* ---------- warna bagian on/off ---------- */
  const btn = document.getElementById("toggle-colors");
  function setColors(on) {
    body.classList.toggle("no-colors", !on);
    if (btn) {
      btn.textContent = "Warna bagian: " + (on ? "aktif" : "mati");
      btn.setAttribute("aria-pressed", String(on));
    }
    try { localStorage.setItem(KEY_COLORS, on ? "1" : "0"); } catch (_) {}
  }
  let saved = "1";
  try { saved = localStorage.getItem(KEY_COLORS) ?? "1"; } catch (_) {}
  setColors(saved !== "0");
  btn?.addEventListener("click", () => setColors(body.classList.contains("no-colors")));

  /* ---------- lompat surah ---------- */
  document.getElementById("surah-select")?.addEventListener("change", e => e.target.form.submit());

  /* ---------- keyboard: mushaf dibaca kanan -> kiri ---------- */
  document.addEventListener("keydown", e => {
    if (e.target.matches("input, select, textarea") || e.ctrlKey || e.metaKey || e.altKey) return;
    const go = id => { const a = document.getElementById(id); if (a) location.href = a.href; };
    if (e.key === "ArrowLeft") go("nav-next");
    if (e.key === "ArrowRight") go("nav-prev");
  });

  /* ---------- pas-kan teks ke lebar baris ----------
     Tiap baris satu garis lurus (nowrap). Jika ada baris yang melebihi lebar,
     ukuran huruf seluruh halaman diperkecil bersama-sama supaya seragam. */
  function fitPage(page) {
    const lines = [...page.querySelectorAll(".line")];
    if (!lines.length) return;
    lines.forEach(l => (l.style.fontSize = ""));
    let size = parseFloat(getComputedStyle(lines[0]).fontSize);
    const min = size * 0.3;
    // lebar isi = jumlah lebar potongan teks (keterangan margin absolut tidak ikut dihitung)
    const overflows = () => lines.some(l => {
      let w = 0;
      l.querySelectorAll(".run").forEach(r => (w += r.getBoundingClientRect().width));
      return w > l.getBoundingClientRect().width + 1;
    });
    while (overflows() && size > min) {
      size *= 0.97;
      lines.forEach(l => (l.style.fontSize = size + "px"));
    }
  }
  function fitAll() { document.querySelectorAll(".page").forEach(fitPage); }

  const run = () => requestAnimationFrame(fitAll);
  if (document.fonts?.ready) document.fonts.ready.then(run); else window.addEventListener("load", run);
  run();
  let t;
  window.addEventListener("resize", () => { clearTimeout(t); t = setTimeout(run, 120); });
})();