(() => {
  const portalFullscreenOverlays = () => {
    document.querySelectorAll(".fixed.inset-0").forEach((overlay) => {
      if (overlay.parentElement !== document.body) {
        document.body.appendChild(overlay);
      }
    });
  };

  document.addEventListener("alpine:initialized", portalFullscreenOverlays);
  document.body.addEventListener("htmx:afterSettle", () => {
    queueMicrotask(portalFullscreenOverlays);
  });
})();
