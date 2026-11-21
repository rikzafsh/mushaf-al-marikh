(() => {
  "use strict";

  const KEY_COLORS = "mushaf-al-marikh:colors";
  const KEY_THEME = "mushaf-al-marikh:theme";
  const root = document.documentElement;
  const body = document.body;
  const $ = id => document.getElementById(id);

  /* ---------- warna bagian on/off ---------- */
  const btnColors = $("toggle-colors");
  function setColors(on) {
    body.classList.toggle("no-colors", !on);
    if (btnColors) {
      btnColors.textContent = "Warna bagian: " + (on ? "aktif" : "mati");
      btnColors.setAttribute("aria-pressed", String(on));
    }
    try { localStorage.setItem(KEY_COLORS, on ? "1" : "0"); } catch (_) {}
  }
  let savedColors = "1";
  try { savedColors = localStorage.getItem(KEY_COLORS) ?? "1"; } catch (_) {}
  setColors(savedColors !== "0");
  btnColors?.addEventListener("click", () => setColors(body.classList.contains("no-colors")));

  /* ---------- kata kunci hafalan on/off ---------- */
  const KEY_KEYS = "mushaf-al-marikh:keys";
  const btnKeys = $("toggle-keys");
  function setKeys(on) {
    body.classList.toggle("no-keys", !on);
    if (btnKeys) {
      btnKeys.textContent = "Kata kunci: " + (on ? "aktif" : "mati");
      btnKeys.setAttribute("aria-pressed", String(on));
    }
    try { localStorage.setItem(KEY_KEYS, on ? "1" : "0"); } catch (_) {}
    if (typeof refit === "function") refit();
  }
  let savedKeys = "1";
  try { savedKeys = localStorage.getItem(KEY_KEYS) ?? "1"; } catch (_) {}
  body.classList.toggle("no-keys", savedKeys === "0");
  if (btnKeys) {
    btnKeys.textContent = "Kata kunci: " + (savedKeys === "0" ? "mati" : "aktif");
    btnKeys.setAttribute("aria-pressed", String(savedKeys !== "0"));
  }
  btnKeys?.addEventListener("click", () => setKeys(body.classList.contains("no-keys")));

  /* ---------- mode gelap / terang ----------
     Nilai awal dipasang oleh skrip kecil di <head> (agar tidak berkedip):
     pilihan tersimpan, atau ikut pengaturan sistem bila belum pernah memilih. */
  const btnTheme = $("toggle-theme");
  function paintThemeButton() {
    const dark = root.dataset.theme === "dark";
    if (btnTheme) {
      btnTheme.textContent = dark ? "☀️ Mode terang" : "🌙 Mode gelap";
      btnTheme.setAttribute("aria-pressed", String(dark));
    }
  }
  function setTheme(t, save = true) {
    root.dataset.theme = t;
    if (save) { try { localStorage.setItem(KEY_THEME, t); } catch (_) {} }
    paintThemeButton();
  }
  paintThemeButton();
  btnTheme?.addEventListener("click", () => setTheme(root.dataset.theme === "dark" ? "light" : "dark"));
  window.matchMedia?.("(prefers-color-scheme: dark)").addEventListener?.("change", e => {
    let saved = null;
    try { saved = localStorage.getItem(KEY_THEME); } catch (_) {}
    if (!saved) setTheme(e.matches ? "dark" : "light", false);   // ikuti sistem selama belum memilih manual
  });

  /* ---------- pas-kan teks ke lebar baris ----------
     Tiap baris satu garis lurus (nowrap). Jika ada baris yang melebihi lebar,
     ukuran huruf seluruh halaman diperkecil bersama-sama supaya seragam. */
  function fitPage(page) {
    const lines = [...page.querySelectorAll(".line.text")];
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
  // kata kunci: kecilkan huruf bila satu baris terlalu panjang untuk kolomnya
  function fitKeys(page) {
    page.querySelectorAll(".kw").forEach(k => {
      k.style.fontSize = "";
      let size = parseFloat(getComputedStyle(k).fontSize);
      const min = size * 0.55;
      while (k.scrollWidth > k.clientWidth + 1 && size > min) {
        size *= 0.95;
        k.style.fontSize = size + "px";
      }
    });
  }
  function fitAll() {
    document.querySelectorAll(".page").forEach(p => { fitPage(p); fitKeys(p); });
  }
  const refit = () => requestAnimationFrame(fitAll);
  if (document.fonts?.ready) document.fonts.ready.then(refit); else window.addEventListener("load", refit);
  refit();
  let resizeTimer;
  window.addEventListener("resize", () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(refit, 120); });

  /* ---------- layar penuh ----------
     Pindah halaman dilakukan TANPA memuat ulang (lihat bagian bawah) supaya mode layar penuh
     tidak terlepas. Bila browser tidak mendukung Fullscreen API (mis. iPhone), dipakai
     tampilan "penuh" di dalam jendela. */
  const btnFs = $("toggle-fs");
  let pseudoFs = false;
  const nativeFs = () => document.fullscreenElement || document.webkitFullscreenElement;
  function paintFs() {
    const on = !!nativeFs() || pseudoFs;
    body.classList.toggle("fs", on);
    if (btnFs) {
      btnFs.textContent = on ? "⤡ Keluar layar penuh" : "⛶ Layar penuh";
      btnFs.setAttribute("aria-pressed", String(on));
    }
    refit();
  }
  async function enterFs() {
    try {
      if (root.requestFullscreen) await root.requestFullscreen();
      else if (root.webkitRequestFullscreen) root.webkitRequestFullscreen();
      else pseudoFs = true;
    } catch (_) { pseudoFs = true; }
    paintFs();
  }
  async function exitFs() {
    pseudoFs = false;
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else if (document.webkitFullscreenElement) document.webkitExitFullscreen();
    } catch (_) {}
    paintFs();
  }
  const toggleFs = () => ((nativeFs() || pseudoFs) ? exitFs() : enterFs());
  btnFs?.addEventListener("click", toggleFs);
  $("fs-exit")?.addEventListener("click", exitFs);
  document.addEventListener("fullscreenchange", paintFs);
  document.addEventListener("webkitfullscreenchange", paintFs);

  /* ---------- pindah halaman tanpa memuat ulang ---------- */
  let navToken = 0;
  async function go(url, push = true) {
    const token = ++navToken;
    try {
      const res = await fetch(url, { headers: { "X-Requested-With": "fetch" } });
      if (!res.ok) throw new Error(res.status);
      const doc = new DOMParser().parseFromString(await res.text(), "text/html");
      if (token !== navToken) return;                      // ada permintaan yang lebih baru
      for (const sel of ["main.spread", "nav.pager"]) {
        const fresh = doc.querySelector(sel), old = document.querySelector(sel);
        if (fresh && old) old.replaceWith(document.importNode(fresh, true));
      }
      // sinkronkan kontrol di toolbar
      const val = (id, v) => { const el = $(id); if (el && v != null) el.value = v; };
      val("page-input", doc.getElementById("page-input")?.value);
      val("surah-select", doc.getElementById("surah-select")?.value);
      const freshView = doc.querySelector('.toolbar input[name="view"]')?.value;
      document.querySelectorAll('.toolbar input[name="view"]').forEach(el => {
        if (freshView != null) el.value = freshView;
      });
      const seg = document.querySelector(".toolbar .seg"), freshSeg = doc.querySelector(".toolbar .seg");
      if (seg && freshSeg) seg.innerHTML = freshSeg.innerHTML;
      document.title = doc.title;
      if (push) history.pushState({}, "", url);
      if (!body.classList.contains("fs")) window.scrollTo({ top: 0 });
      refit();
    } catch (_) {
      if (token === navToken) location.href = url;         // cadangan: muat biasa
    }
  }
  window.addEventListener("popstate", () => go(location.href, false));

  // tautan bertanda data-nav (Berikutnya/Sebelumnya, 1/2 halaman)
  document.addEventListener("click", e => {
    const a = e.target.closest?.("a[data-nav]");
    if (!a || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    go(a.href);
  });
  // formulir lompat surah / halaman
  document.querySelectorAll(".toolbar form").forEach(f => {
    f.addEventListener("submit", e => {
      e.preventDefault();
      go(f.action + "?" + new URLSearchParams(new FormData(f)));
    });
  });
  $("surah-select")?.addEventListener("change", e => e.target.form.requestSubmit());

  /* ---------- keyboard: mushaf dibaca kanan -> kiri ---------- */
  document.addEventListener("keydown", e => {
    if (e.target.matches("input, select, textarea") || e.ctrlKey || e.metaKey || e.altKey) return;
    const click = id => { const a = $(id); if (a) go(a.href); };
    if (e.key === "ArrowLeft") click("nav-next");
    else if (e.key === "ArrowRight") click("nav-prev");
    else if (e.key === "f" || e.key === "F") toggleFs();
  });
})();