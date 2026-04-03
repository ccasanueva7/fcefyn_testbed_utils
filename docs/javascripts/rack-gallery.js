/**
 * Carousel for [data-rack-gallery]: one slide visible, prev/next wrap.
 * Clicking the image (not the arrow buttons) opens a full-screen lightbox with the same navigation.
 */
(function () {
  var lightbox = null;
  var lbImg = null;
  var lbCaption = null;
  var lbCounter = null;
  var lbPrev = null;
  var lbNext = null;
  var lbClose = null;
  var activeSlides = null;
  var activeIndex = 0;
  var activeCount = 0;
  var syncCarousel = null;
  var previousFocus = null;
  var onLightboxKeydown = null;

  function ensureLightbox() {
    if (lightbox) return;

    lightbox = document.createElement("div");
    lightbox.id = "rack-gallery-lightbox";
    lightbox.className = "rack-gallery-lightbox";
    lightbox.setAttribute("role", "dialog");
    lightbox.setAttribute("aria-modal", "true");
    lightbox.setAttribute("aria-label", "Vista ampliada de la galería");
    lightbox.setAttribute("hidden", "");

    var backdrop = document.createElement("button");
    backdrop.type = "button";
    backdrop.className = "rack-gallery-lightbox__backdrop";
    backdrop.setAttribute("aria-label", "Cerrar vista ampliada");

    lbClose = document.createElement("button");
    lbClose.type = "button";
    lbClose.className = "rack-gallery-lightbox__close";
    lbClose.setAttribute("aria-label", "Cerrar");
    lbClose.innerHTML = "&times;";

    var stage = document.createElement("div");
    stage.className = "rack-gallery-lightbox__stage";

    lbPrev = document.createElement("button");
    lbPrev.type = "button";
    lbPrev.className = "rack-gallery-lightbox__nav rack-gallery__btn";
    lbPrev.setAttribute("data-rack-lb-prev", "");
    lbPrev.setAttribute("aria-label", "Imagen anterior");
    lbPrev.innerHTML = "&#8249;";

    lbImg = document.createElement("img");
    lbImg.className = "rack-gallery-lightbox__img";
    lbImg.alt = "";

    lbNext = document.createElement("button");
    lbNext.type = "button";
    lbNext.className = "rack-gallery-lightbox__nav rack-gallery__btn";
    lbNext.setAttribute("data-rack-lb-next", "");
    lbNext.setAttribute("aria-label", "Imagen siguiente");
    lbNext.innerHTML = "&#8250;";

    stage.appendChild(lbPrev);
    stage.appendChild(lbImg);
    stage.appendChild(lbNext);

    lbCaption = document.createElement("p");
    lbCaption.className = "rack-gallery-lightbox__caption";

    lbCounter = document.createElement("span");
    lbCounter.className = "rack-gallery-lightbox__counter";
    lbCounter.setAttribute("aria-live", "polite");

    lightbox.appendChild(backdrop);
    lightbox.appendChild(lbClose);
    lightbox.appendChild(lbCounter);
    lightbox.appendChild(stage);
    lightbox.appendChild(lbCaption);
    document.body.appendChild(lightbox);

    function lbGo(delta) {
      activeIndex = (activeIndex + delta + activeCount) % activeCount;
      if (syncCarousel) syncCarousel(activeIndex);
      updateLightboxView();
    }

    function closeLightbox() {
      lightbox.setAttribute("hidden", "");
      document.body.classList.remove("rack-gallery-lightbox-open");
      if (onLightboxKeydown) {
        document.removeEventListener("keydown", onLightboxKeydown);
      }
      if (previousFocus && typeof previousFocus.focus === "function") {
        previousFocus.focus();
      }
      previousFocus = null;
      activeSlides = null;
      syncCarousel = null;
    }

    onLightboxKeydown = function (e) {
      if (e.key === "Escape") {
        e.preventDefault();
        closeLightbox();
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        lbGo(-1);
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        lbGo(1);
      }
    };

    backdrop.addEventListener("click", closeLightbox);
    lbClose.addEventListener("click", closeLightbox);
    lbPrev.addEventListener("click", function (e) {
      e.stopPropagation();
      lbGo(-1);
    });
    lbNext.addEventListener("click", function (e) {
      e.stopPropagation();
      lbGo(1);
    });

    lightbox.addEventListener("click", function (e) {
      if (e.target === lightbox) closeLightbox();
    });
  }

  function updateLightboxView() {
    if (!activeSlides || !lbImg) return;
    var slide = activeSlides[activeIndex];
    if (!slide) return;
    var img = slide.querySelector("img");
    if (!img) return;
    lbImg.src = img.currentSrc || img.src;
    lbImg.alt = img.getAttribute("alt") || "";
    var cap = slide.getAttribute("data-caption");
    lbCaption.textContent = cap || "";
    lbCaption.hidden = !cap;
    lbCounter.textContent = activeIndex + 1 + " / " + activeCount;
  }

  function openLightbox(slides, index, onSync) {
    ensureLightbox();
    activeSlides = slides;
    activeCount = slides.length;
    activeIndex = index;
    syncCarousel = onSync;
    previousFocus = document.activeElement;
    updateLightboxView();
    lightbox.removeAttribute("hidden");
    document.body.classList.add("rack-gallery-lightbox-open");
    document.addEventListener("keydown", onLightboxKeydown);
    lbClose.focus();
  }

  function initGallery(gallery) {
    var slides = gallery.querySelectorAll(".rack-gallery__slide");
    var viewport = gallery.querySelector(".rack-gallery__viewport");
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

    if (prev) prev.addEventListener("click", function (e) {
      e.stopPropagation();
      go(-1);
    });
    if (next) next.addEventListener("click", function (e) {
      e.stopPropagation();
      go(1);
    });

    gallery.addEventListener("keydown", function (e) {
      if (document.body.classList.contains("rack-gallery-lightbox-open")) return;
      if (e.key === "ArrowLeft") {
        go(-1);
        e.preventDefault();
      } else if (e.key === "ArrowRight") {
        go(1);
        e.preventDefault();
      }
    });

    if (viewport) {
      viewport.addEventListener("click", function (e) {
        if (e.target.closest(".rack-gallery__btn")) return;
        var slide = e.target.closest(".rack-gallery__slide");
        if (!slide || !gallery.contains(slide)) return;
        var idx = Array.prototype.indexOf.call(slides, slide);
        if (idx < 0) return;
        i = idx;
        show();
        openLightbox(slides, i, function (j) {
          i = j;
          show();
        });
      });
    }

    show();
  }

  document.querySelectorAll("[data-rack-gallery]").forEach(initGallery);
})();
