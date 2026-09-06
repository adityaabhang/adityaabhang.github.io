/* Shared front-end enhancements: scroll reveals, gentle parallax, flow-diagram
   stagger, count-up stats. All motion is opt-out via prefers-reduced-motion. */
(function () {
  "use strict";
  var REDUCED = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var CAN_HOVER = window.matchMedia("(min-width: 860px)").matches;

  /* ---------- scroll reveal ---------- */
  function markArticleReveals() {
    if (!document.querySelector("article")) return;
    var sel = "article > h2, article > p, article > ul, article > .tech-grid," +
              "article > .outcomes-grid, .flow-wrap, .project-img-hero";
    document.querySelectorAll(sel).forEach(function (el) {
      if (!el.hasAttribute("data-reveal") && !el.hasAttribute("data-reveal-stagger")) {
        el.setAttribute("data-reveal", "");
      }
    });
  }

  function initReveal() {
    var nodes = document.querySelectorAll("[data-reveal], [data-reveal-stagger]");
    if (!nodes.length) return;
    if (REDUCED || !("IntersectionObserver" in window)) {
      nodes.forEach(function (n) { n.classList.add("in"); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
      });
    }, { threshold: 0.12, rootMargin: "0px 0px -8% 0px" });
    nodes.forEach(function (n) { io.observe(n); });
  }

  /* ---------- gentle parallax ---------- */
  function initParallax() {
    var els = [].slice.call(document.querySelectorAll("[data-parallax]"));
    if (!els.length || REDUCED || !CAN_HOVER) return;
    els.forEach(function (el) { el.classList.add("is-parallax"); });
    var ticking = false;
    function update() {
      var vh = window.innerHeight;
      els.forEach(function (el) {
        var r = el.getBoundingClientRect();
        var frac = ((r.top + r.height / 2) - vh / 2) / vh; // -1 .. 1
        var amt = parseFloat(el.getAttribute("data-parallax")) || 0.12;
        var px = Math.max(-60, Math.min(60, -frac * amt * 100));
        el.style.transform = "translate3d(0," + px.toFixed(1) + "px,0)";
      });
      ticking = false;
    }
    function onScroll() {
      if (!ticking) { window.requestAnimationFrame(update); ticking = true; }
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    update();
  }

  /* ---------- count-up on reveal ---------- */
  function initCountUp() {
    if (REDUCED || !("IntersectionObserver" in window)) return;
    var stats = document.querySelectorAll(".outcome-card .stat, .is .v, [data-countup]");
    if (!stats.length) return;
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        io.unobserve(e.target);
        var el = e.target, raw = el.textContent.trim();
        var m = raw.match(/^(-?)(\d[\d,]*\.?\d*)(.*)$/s);
        if (!m) return;
        var sign = m[1], target = parseFloat(m[2].replace(/,/g, "")), rest = m[3];
        var dec = (m[2].split(".")[1] || "").length;
        var start = performance.now(), dur = 900;
        function step(now) {
          var t = Math.min(1, (now - start) / dur);
          var eased = 1 - Math.pow(1 - t, 3);
          var val = (target * eased).toFixed(dec);
          el.textContent = sign + Number(val).toLocaleString(undefined, {
            minimumFractionDigits: dec, maximumFractionDigits: dec
          }) + rest;
          if (t < 1) requestAnimationFrame(step);
        }
        requestAnimationFrame(step);
      });
    }, { threshold: 0.6 });
    stats.forEach(function (s) { io.observe(s); });
  }

  function boot() {
    markArticleReveals();
    initReveal();
    initParallax();
    initCountUp();
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else { boot(); }
})();
