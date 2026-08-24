(function () {
  "use strict";

  if (window.__floppyHorizontalScrollBound) return;
  window.__floppyHorizontalScrollBound = true;

  const selector = '[data-horizontal-scroll="true"]';
  const dragThreshold = 6;
  let activeDrag = null;
  let suppressClick = false;
  let clickResetTimer = null;

  function reducedMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function finishDrag(event) {
    if (!activeDrag || (event && event.pointerId !== activeDrag.pointerId)) return;

    const { surface, pointerId, dragging } = activeDrag;
    surface.classList.remove("is-dragging");
    if (surface.hasPointerCapture && surface.hasPointerCapture(pointerId)) {
      surface.releasePointerCapture(pointerId);
    }
    activeDrag = null;

    if (dragging) {
      clearTimeout(clickResetTimer);
      clickResetTimer = setTimeout(() => {
        suppressClick = false;
      }, 0);
    }
  }

  document.addEventListener("pointerdown", (event) => {
    if (event.pointerType === "touch" || event.button !== 0 || !event.isPrimary) return;

    const surface = event.target.closest(selector);
    if (!surface || event.target.closest("button, input, select, textarea, [contenteditable]")) return;

    activeDrag = {
      surface,
      pointerId: event.pointerId,
      startX: event.clientX,
      startScrollLeft: surface.scrollLeft,
      dragging: false,
    };
  });

  document.addEventListener("pointermove", (event) => {
    if (!activeDrag || event.pointerId !== activeDrag.pointerId) return;

    const deltaX = event.clientX - activeDrag.startX;
    if (!activeDrag.dragging && Math.abs(deltaX) < dragThreshold) return;

    if (!activeDrag.dragging) {
      activeDrag.surface.setPointerCapture(event.pointerId);
    }
    activeDrag.dragging = true;
    suppressClick = true;
    activeDrag.surface.classList.add("is-dragging");
    activeDrag.surface.scrollLeft = activeDrag.startScrollLeft - deltaX;
    event.preventDefault();
  });

  document.addEventListener("pointerup", finishDrag);
  document.addEventListener("pointercancel", finishDrag);

  document.addEventListener(
    "click",
    (event) => {
      if (!suppressClick || !event.target.closest(selector)) return;
      suppressClick = false;
      event.preventDefault();
      event.stopImmediatePropagation();
    },
    true,
  );

  document.addEventListener("dragstart", (event) => {
    if (activeDrag && activeDrag.surface.contains(event.target)) {
      event.preventDefault();
    }
  });

  document.addEventListener("keydown", (event) => {
    const surface = event.target.closest(selector);
    if (!surface || event.target !== surface || !["ArrowLeft", "ArrowRight"].includes(event.key)) return;

    const direction = event.key === "ArrowLeft" ? -1 : 1;
    surface.scrollBy({
      left: direction * surface.clientWidth * 0.85,
      behavior: reducedMotion() ? "auto" : "smooth",
    });
    event.preventDefault();
  });
})();
