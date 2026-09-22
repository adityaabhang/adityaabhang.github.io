/* Before/after comparison slider: drag to reveal one image over another.
   Reads its slide list from data-pairs (JSON: before/after/beforeAlt/afterAlt/label). */
(function () {
  "use strict";

  document.querySelectorAll(".compare-slider[data-pairs]").forEach(initSlider);

  function initSlider(root) {
    var pairs = JSON.parse(root.getAttribute("data-pairs"));
    var stage = root.querySelector(".compare-stage");
    var afterImg = root.querySelector(".compare-after");
    var beforeImg = root.querySelector(".compare-before");
    var clip = root.querySelector(".compare-clip");
    var handle = root.querySelector(".compare-handle");
    var captionTag = root.querySelector(".compare-tag-caption");
    var dots = root.querySelectorAll(".gallery-dots .dot");

    var current = 0;
    var percent = 50;
    var dragging = false;

    function layout() {
      var w = stage.clientWidth;
      beforeImg.style.setProperty("--stage-w", w + "px");
      beforeImg.style.width = w + "px";
    }

    function setPercent(p) {
      percent = Math.max(0, Math.min(100, p));
      clip.style.width = percent + "%";
      handle.style.left = percent + "%";
    }

    function loadPair(i) {
      current = ((i % pairs.length) + pairs.length) % pairs.length;
      var pair = pairs[current];
      afterImg.src = pair.after;
      afterImg.alt = pair.afterAlt || "";
      beforeImg.src = pair.before;
      beforeImg.alt = pair.beforeAlt || "";
      if (captionTag) captionTag.textContent = pair.label || "";
      dots.forEach(function (d, di) { d.classList.toggle("active", di === current); });
      layout();
      setPercent(50);
    }

    function percentFromClientX(clientX) {
      var rect = stage.getBoundingClientRect();
      return ((clientX - rect.left) / rect.width) * 100;
    }

    function onPointerDown(e) {
      dragging = true;
      stage.setPointerCapture(e.pointerId);
      setPercent(percentFromClientX(e.clientX));
    }
    function onPointerMove(e) {
      if (!dragging) return;
      setPercent(percentFromClientX(e.clientX));
    }
    function onPointerUp(e) {
      dragging = false;
      try { stage.releasePointerCapture(e.pointerId); } catch (err) {}
    }

    stage.addEventListener("pointerdown", onPointerDown);
    stage.addEventListener("pointermove", onPointerMove);
    stage.addEventListener("pointerup", onPointerUp);
    stage.addEventListener("pointercancel", onPointerUp);

    dots.forEach(function (d, i) {
      d.addEventListener("click", function () { loadPair(i); });
    });

    new ResizeObserver(layout).observe(stage);
    loadPair(0);
  }
})();
