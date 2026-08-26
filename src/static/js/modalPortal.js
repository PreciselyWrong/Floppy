(() => {
  const portalFullscreenOverlays = () => {
    document.querySelectorAll(".fixed.inset-0").forEach((overlay) => {
      if (overlay.parentElement !== document.body) {
        const dataStack = Alpine.closestDataStack(overlay);
        overlay._modalDataStack = dataStack;
        overlay._x_dataStack = dataStack;
        Alpine.mutateDom(() => {
          document.body.appendChild(overlay);
        });
      }
    });
  };

  document.addEventListener("alpine:initialized", portalFullscreenOverlays);
  document.body.addEventListener("htmx:afterSettle", () => {
    queueMicrotask(portalFullscreenOverlays);
  });
})();
