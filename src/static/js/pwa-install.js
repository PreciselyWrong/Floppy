(function () {
  "use strict";

  if (window.__floppyPwaInstallBound) return;
  window.__floppyPwaInstallBound = true;

  const panel = document.querySelector('[data-pwa-install="true"]');
  if (!panel) return;

  const installButton = panel.querySelector("[data-pwa-install-action]");
  const dismissButton = panel.querySelector("[data-pwa-install-dismiss]");
  const iosHelp = panel.querySelector('[data-pwa-ios-help="true"]');
  let installPrompt = null;

  const isStandalone =
    window.matchMedia("(display-mode: standalone)").matches ||
    navigator.standalone === true;
  const isIos =
    /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);

  function hide() {
    panel.hidden = true;
  }

  function showInstallButton() {
    iosHelp.hidden = true;
    installButton.hidden = false;
    panel.hidden = false;
  }

  if (isStandalone) return;

  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    installPrompt = event;
    showInstallButton();
  });

  installButton.addEventListener("click", async () => {
    if (!installPrompt) return;
    await installPrompt.prompt();
    const choice = await installPrompt.userChoice;
    installPrompt = null;
    if (choice.outcome === "accepted") hide();
  });

  dismissButton.addEventListener("click", hide);
  window.addEventListener("appinstalled", hide);

  if (isIos) {
    installButton.hidden = true;
    iosHelp.hidden = false;
    panel.hidden = false;
  }
})();
