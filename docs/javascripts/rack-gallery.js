/**
 * Simple carousel for [data-rack-gallery]: one slide visible, prev/next wrap.
 */
(function () {
  function initGallery(gallery) {
    var slides = gallery.querySelectorAll(".rack-gallery__slide");
    var prev = gallery.querySelector("[data-rack-prev]");
    var next = gallery.querySelector("[data-rack-next]");
    var counter = gallery.querySelector("[data-rack-counter]");
    var captionEl = gallery.querySelector("[data-rack-caption]");
    var n = slides.length;
    if (n === 0) return;

    var i = 0;

    function show() {
      slides.forEach(function (slide, j) {
        slide.hidden = j !== i;
      });
      if (counter) {
        counter.textContent = i + 1 + " / " + n;
      }
      if (captionEl) {
        var cap = slides[i].getAttribute("data-caption");
        captionEl.textContent = cap || "";
      }
    }

    function go(delta) {
      i = (i + delta + n) % n;
      show();
    }

    if (prev) prev.addEventListener("click", function () { go(-1); });
    if (next) next.addEventListener("click", function () { go(1); });

    gallery.addEventListener("keydown", function (e) {
      if (e.key === "ArrowLeft") {
        go(-1);
        e.preventDefault();
      } else if (e.key === "ArrowRight") {
        go(1);
        e.preventDefault();
      }
    });

    show();
  }

  document.querySelectorAll("[data-rack-gallery]").forEach(initGallery);
})();
