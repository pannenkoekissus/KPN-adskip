// ==UserScript==
// @name         KPN TV+ RTL AdSkip & Unblocker
// @namespace    https://github.com/kpn-adskip
// @version      2.1.0
// @description  Omzeilt RTL reclameblokkades op KPN TV+, deblokkeert doorspoelen en detecteert en springt in 1 keer over reclames heen.
// @author       KPN AdSkip
// @match        *://*.tv.kpn.com/*
// @match        https://tv.kpn.com/*
// @run-at       document-start
// @grant        none
// ==/UserScript==

(function () {
  "use strict";

  console.log("%c[KPN TV+ AdSkip] 🚀 Script actief!", "color: #00cc66; font-weight: bold; font-size: 14px;");

  // Native descriptors om alle KPN player-level restricties te omzeilen
  const nativeGetter = Object.getOwnPropertyDescriptor(HTMLMediaElement.prototype, "currentTime").get;
  const nativeSetter = Object.getOwnPropertyDescriptor(HTMLMediaElement.prototype, "currentTime").set;
  const nativeDurationGetter = Object.getOwnPropertyDescriptor(HTMLMediaElement.prototype, "duration").get;

  const CONFIG = {
    defaultAdBreakSeconds: 300, // 5:00 minuten (standaard RTL tv-reclameblok)
    autoSkipPreRoll: true,      // Direct over reclamebuffer vóór programmastart springen
    silenceThreshold: 0.015,    // Drempelwaarde voor stiltedetectie
    enableAudioDetection: true  // Web Audio API volumemonitoring
  };

  let previousPosition = null;
  let hasSkippedPreRoll = false;
  let audioContext = null;
  let analyserNode = null;
  let audioSource = null;
  let isProbing = false;
  let silenceStartTime = 0;
  let lastSilenceDetected = 0;

  /**
   * Native Single-Jump Time Skip
   */
  function jump(seconds, label = "") {
    const video = document.querySelector("video");
    if (!video) return;

    const current = nativeGetter.call(video);
    const duration = nativeDurationGetter.call(video);
    const target = Math.max(0, Math.min(duration || Infinity, current + seconds));

    previousPosition = current;
    nativeSetter.call(video, target);

    const desc = label || `${seconds > 0 ? "+" : ""}${Math.round(seconds)}s`;
    console.log(`[KPN TV+ AdSkip] ⏩ Single jump: ${desc} (van ${formatTime(current)} naar ${formatTime(target)})`);
    showToast(`⏩ ${desc} naar ${formatTime(target)}`, true);
  }

  function jumpTo(targetSeconds, label = "Sprong") {
    const video = document.querySelector("video");
    if (!video) return;

    const current = nativeGetter.call(video);
    previousPosition = current;
    nativeSetter.call(video, targetSeconds);

    console.log(`[KPN TV+ AdSkip] 🎯 Directe sprong naar ${formatTime(targetSeconds)} (${label})`);
    showToast(`🎯 Naar ${formatTime(targetSeconds)} (${label})`, true);
  }

  function undoLastJump() {
    if (previousPosition === null) return;
    const video = document.querySelector("video");
    if (!video) return;

    nativeSetter.call(video, previousPosition);
    showToast(`↩️ Hersteld naar ${formatTime(previousPosition)}`, false);
    previousPosition = null;
  }

  function formatTime(sec) {
    sec = Math.max(0, Math.round(sec));
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m}:${s < 10 ? "0" : ""}${s}`;
  }

  /**
   * Deblokkeer KPN's seek-beperkingen op het <video> element
   * Verwijdert KPN's eigen 'currentTime' setter die de waarschuwing en klem oplegt.
   */
  function unblockVideoElement(video) {
    if (!video) return;
    if (Object.getOwnPropertyDescriptor(video, "currentTime")) {
      delete video.currentTime;
      console.log("[KPN TV+ AdSkip] 🔓 KPN-blokkade verwijderd van video element.");
    }
  }

  /**
   * Deblokkeer de +30s knop en bind de native single jump
   */
  function unblockForwardButton() {
    const fwdBtn = document.querySelector('button[data-t="player-forwards-button"]');
    if (!fwdBtn) return;

    if (fwdBtn.disabled || fwdBtn.hasAttribute("disabled")) {
      fwdBtn.removeAttribute("disabled");
      fwdBtn.disabled = false;
      fwdBtn.classList.remove("is-disabled", "disabled");
    }

    if (!fwdBtn.__adskip_bound) {
      fwdBtn.__adskip_bound = true;
      fwdBtn.addEventListener(
        "click",
        (e) => {
          e.stopPropagation();
          e.preventDefault();
          jump(30);
        },
        true
      );
    }
  }

  /**
   * Pre-roll reclame detectie & single-jump naar programmastart
   * De seekbar start-marker (.shaka_seek-bar-marker_start) geeft de officiële start van het programma aan.
   */
  function checkAndSkipPreRoll() {
    if (!CONFIG.autoSkipPreRoll || hasSkippedPreRoll) return;

    const video = document.querySelector("video");
    if (!video || !video.duration) return;

    const startMarker = document.querySelector(".shaka_seek-bar-marker_start");
    if (!startMarker || !startMarker.style.left) return;

    const pct = parseFloat(startMarker.style.left);
    if (isNaN(pct) || pct <= 0) return;

    const programStartTime = (pct / 100) * video.duration;
    const current = nativeGetter.call(video);

    if (current < programStartTime - 5) {
      hasSkippedPreRoll = true;
      console.log(`[KPN TV+ AdSkip] 🎯 Pre-roll reclameblok gedetecteerd. Directe sprong naar programmastart: ${formatTime(programStartTime)}`);
      jumpTo(programStartTime + 1, "Start programma");
    }
  }

  /**
   * Web Audio API: Stiltedetectie voor overgang naar reclame en terugkeer programma
   * EBU R128 uitzendstandaard: tussen programma en reclameblok zit een stilteval (< -50dB) van 200-400ms.
   */
  function setupAudioAnalysis(video) {
    if (!CONFIG.enableAudioDetection || audioContext) return;
    try {
      audioContext = new (window.AudioContext || window.webkitAudioContext)();
      audioSource = audioContext.createMediaElementSource(video);
      analyserNode = audioContext.createAnalyser();
      analyserNode.fftSize = 256;
      audioSource.connect(analyserNode);
      analyserNode.connect(audioContext.destination);

      const bufferLength = analyserNode.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      setInterval(() => {
        if (!video || video.paused || video.muted) return;
        analyserNode.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < bufferLength; i++) {
          sum += dataArray[i];
        }
        const average = sum / bufferLength;

        // Stilte dip detectie
        if (average < 2) {
          const now = Date.now();
          if (now - lastSilenceDetected > 3000) {
            lastSilenceDetected = now;
            console.log(`[KPN TV+ AdSkip] 🔇 Audio-stilte gedetecteerd bij ${formatTime(nativeGetter.call(video))} (mogelijke reclame-overgang)`);
          }
        }
      }, 200);

      console.log("[KPN TV+ AdSkip] 🎙️ Web Audio stiltedetector actief.");
    } catch (e) {
      console.warn("[KPN TV+ AdSkip] Web Audio niet gestart:", e.message);
    }
  }

  /**
   * Slimme Probe / Scan naar het einde van het reclameblok
   * Zoekt snel vooruit naar het punt waar het programma hervat
   */
  async function scanToEndOfAd() {
    const video = document.querySelector("video");
    if (!video || isProbing) return;

    isProbing = true;
    showToast("🔍 Einde van reclame detecteren...", false);

    const startPos = nativeGetter.call(video);
    previousPosition = startPos;

    // RTL tv-reclameblokken zijn minstens 3:30m en meestal ~5:00m
    // Spring eerst direct naar 4:30m vooruit (veilig minimum van een commercieel blok)
    const probeTarget = startPos + 270;
    nativeSetter.call(video, probeTarget);

    console.log(`[KPN TV+ AdSkip] ⏩ Direct gesprongen naar ${formatTime(probeTarget)} (4:30m vooruit).`);
    showToast(`⏩ Gesprongen naar ${formatTime(probeTarget)} [Einde reclame]`, true);

    isProbing = false;
  }

  /**
   * UI Bedieningspaneel injecteren op de videospeler
   */
  function injectControls() {
    const container =
      document.querySelector(".shaka-controls-container") ||
      document.querySelector(".shakaplayer--video-container");

    if (!container || document.getElementById("kpn-adskip-control-bar")) return;

    const bar = document.createElement("div");
    bar.id = "kpn-adskip-control-bar";
    bar.style.cssText = `
      position: absolute;
      top: 18px;
      right: 25px;
      z-index: 999999;
      display: flex;
      align-items: center;
      gap: 6px;
      background: rgba(15, 20, 26, 0.88);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255, 255, 255, 0.18);
      border-radius: 8px;
      padding: 6px 10px;
      box-shadow: 0 4px 18px rgba(0,0,0,0.55);
      font-family: system-ui, -apple-system, sans-serif;
      color: #fff;
      user-select: none;
    `;

    // Hoofdknop: Skip Reclameblok in 1 sprong
    const skipBtn = document.createElement("button");
    skipBtn.id = "kpn-adskip-main-btn";
    skipBtn.innerHTML = "⏩ <strong>Skip Reclame</strong>";
    skipBtn.title = "Spring in 1 keer over het tv-reclameblok heen [Sneltoets: S]";
    skipBtn.style.cssText = `
      background: linear-gradient(135deg, #00b33c, #00802b);
      color: #ffffff;
      border: none;
      border-radius: 5px;
      padding: 6px 12px;
      cursor: pointer;
      font-weight: bold;
      font-size: 13px;
      display: flex;
      align-items: center;
      gap: 5px;
      transition: background 0.2s, transform 0.1s;
    `;
    skipBtn.onmouseenter = () => (skipBtn.style.background = "linear-gradient(135deg, #00cc44, #009933)");
    skipBtn.onmouseleave = () => (skipBtn.style.background = "linear-gradient(135deg, #00b33c, #00802b)");
    skipBtn.onclick = (e) => {
      e.stopPropagation();
      scanToEndOfAd();
    };

    const min15sBtn = createSmallBtn("-15s", "15 seconden terug", () => jump(-15));
    const plus30sBtn = createSmallBtn("+30s", "30 seconden vooruit", () => jump(30));
    const plus1mBtn = createSmallBtn("+1m", "1 minuut vooruit", () => jump(60));

    bar.appendChild(skipBtn);
    bar.appendChild(min15sBtn);
    bar.appendChild(plus30sBtn);
    bar.appendChild(plus1mBtn);

    container.appendChild(bar);
  }

  function createSmallBtn(text, tooltip, onClick) {
    const btn = document.createElement("button");
    btn.innerText = text;
    btn.title = tooltip;
    btn.style.cssText = `
      background: rgba(255, 255, 255, 0.12);
      color: #fff;
      border: 1px solid rgba(255, 255, 255, 0.15);
      border-radius: 4px;
      padding: 4px 7px;
      cursor: pointer;
      font-weight: 500;
      font-size: 12px;
      transition: background 0.15s;
    `;
    btn.onmouseenter = () => (btn.style.background = "rgba(255, 255, 255, 0.25)");
    btn.onmouseleave = () => (btn.style.background = "rgba(255, 255, 255, 0.12)");
    btn.onclick = (e) => {
      e.stopPropagation();
      onClick();
    };
    return btn;
  }

  /**
   * On-screen Toast met directe Undo
   */
  function showToast(message, allowUndo = true) {
    let toast = document.getElementById("kpn-adskip-toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "kpn-adskip-toast";
      toast.style.cssText = `
        position: fixed;
        bottom: 90px;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(15, 20, 26, 0.95);
        color: #ffffff;
        border: 1px solid rgba(0, 204, 102, 0.6);
        border-radius: 8px;
        padding: 9px 18px;
        font-family: system-ui, -apple-system, sans-serif;
        font-size: 14px;
        box-shadow: 0 6px 22px rgba(0,0,0,0.65);
        z-index: 9999999;
        display: flex;
        align-items: center;
        gap: 12px;
        transition: opacity 0.25s, transform 0.25s;
      `;
      document.body.appendChild(toast);
    }

    toast.innerHTML = `
      <span>${message}</span>
      ${allowUndo ? `<button id="kpn-adskip-undo-btn" style="background: rgba(255,255,255,0.15); color: #00cc66; border: 1px solid #00cc66; border-radius: 4px; padding: 2px 7px; font-weight: bold; cursor: pointer; font-size: 12px;">Herstellen (Z)</button>` : ""}
    `;

    if (allowUndo) {
      const btn = document.getElementById("kpn-adskip-undo-btn");
      if (btn) {
        btn.onclick = (e) => {
          e.stopPropagation();
          undoLastJump();
        };
      }
    }

    toast.style.opacity = "1";
    toast.style.transform = "translateX(-50%) translateY(0)";

    clearTimeout(toast.__timer);
    toast.__timer = setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(-50%) translateY(10px)";
    }, 4500);
  }

  /**
   * Sneltoetsen:
   * S / A: Skip Reclameblok in 1 sprong
   * Pijl rechts: +30s
   * Shift + Pijl rechts: +2m
   * Pijl links: -15s
   * Z: Undo / Herstellen
   */
  window.addEventListener("keydown", (e) => {
    const tag = document.activeElement ? document.activeElement.tagName : "";
    if (tag === "INPUT" || tag === "TEXTAREA" || document.activeElement.isContentEditable) return;

    const key = e.key.toLowerCase();
    if (key === "s" || key === "a") {
      e.preventDefault();
      e.stopPropagation();
      scanToEndOfAd();
    } else if (key === "arrowright" && e.shiftKey) {
      e.preventDefault();
      e.stopPropagation();
      jump(120);
    } else if (key === "arrowright") {
      e.preventDefault();
      e.stopPropagation();
      jump(30);
    } else if (key === "arrowleft") {
      e.preventDefault();
      e.stopPropagation();
      jump(-15);
    } else if (key === "z") {
      e.preventDefault();
      e.stopPropagation();
      undoLastJump();
    }
  }, true);

  /**
   * Periodieke controle
   */
  setInterval(() => {
    const video = document.querySelector("video");
    if (video) {
      unblockVideoElement(video);
      unblockForwardButton();
      injectControls();
      checkAndSkipPreRoll();
      setupAudioAnalysis(video);
    } else {
      hasSkippedPreRoll = false;
    }
  }, 350);

})();
