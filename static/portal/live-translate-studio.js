(function () {
  "use strict";

  const STATE = {
    deferredPrompt: null,
    account: null,
    csrfToken: "",
    balanceXu: null,
    isAdmin: false,
    walletLinked: false,
    sessionId: null,
    streamToken: null,
    wsUrl: null,
    ws: null,
    mediaStream: null,
    audioCtx: null,
    playbackCtx: null,
    nextPlaybackTime: 0,
    seqCounter: 0,
    pipWindow: null,
    active: false,
    dubMuted: false,
    accountLoaded: false,
    accountPromise: null,
    voiceProfiles: [],
    lastStatus: "",
    lastOrig: "Sẵn sàng nhận lời thoại từ Tab Chrome...",
    lastTrans: "Chọn Tab video (nhớ tích 'Chia sẻ âm thanh thẻ') để dịch & lồng tiếng trực tiếp.",
    spentXu: 0,
  };

  window.addEventListener("beforeinstallprompt", function (event) {
    event.preventDefault();
    STATE.deferredPrompt = event;
    updateInstallButtons();
  });

  window.addEventListener("appinstalled", function () {
    STATE.deferredPrompt = null;
    updateInstallButtons();
  });

  function isSubdubRoute() {
    const clean = (window.location.pathname || "/").replace(/\/+$/, "") || "/";
    return clean === "/subdub";
  }

  function isFocusLiveMode() {
    try {
      return isSubdubRoute() && new URLSearchParams(window.location.search).get("focus") === "live";
    } catch (_) {
      return false;
    }
  }

  function syncFocusModeClass() {
    if (typeof document === "undefined" || !document.documentElement) return;
    document.documentElement.classList.toggle("portal-lt-focus-mode", isFocusLiveMode());
  }

  function isStandaloneChromeApp() {
    return (
      window.matchMedia("(display-mode: standalone)").matches ||
      Boolean(window.navigator.standalone)
    );
  }

  function updateInstallButtons() {
    document.querySelectorAll("[data-lt-install-chrome]").forEach((btn) => {
      if (isStandaloneChromeApp()) {
        btn.textContent = "Đã mở trong ứng dụng Chrome";
        btn.disabled = true;
      } else if (STATE.deferredPrompt) {
        btn.textContent = "Thêm ứng dụng TOAN AAS vào Chrome";
        btn.disabled = false;
      } else {
        btn.textContent = "Mở qua ứng dụng Chrome";
        btn.disabled = false;
      }
    });
  }

  async function triggerChromeAppInstall(statusEl) {
    if (STATE.deferredPrompt) {
      const promptEvent = STATE.deferredPrompt;
      STATE.deferredPrompt = null;
      await promptEvent.prompt();
      const choice = await promptEvent.userChoice;
      updateInstallButtons();
      if (statusEl) {
        statusEl.textContent =
          choice && choice.outcome === "accepted"
            ? "Đã thêm ứng dụng TOAN AAS vào Chrome."
            : "Bạn đã hủy cài đặt ứng dụng Chrome.";
      }
      return;
    }
    if (statusEl) {
      statusEl.textContent = isStandaloneChromeApp()
        ? "Bạn đang sử dụng ứng dụng TOAN AAS độc lập trên Chrome."
        : "Bấm biểu tượng cài đặt ở góc phải thanh địa chỉ Chrome → Cài đặt TOAN AAS, hoặc bấm 'Mở cửa sổ CHỈ Phụ đề & Lồng tiếng'.";
    }
  }

  function applyAccountStateToStudio(studioEl) {
    const acctBadge = studioEl.querySelector("[data-lt-account-pill]");
    const balBadge = studioEl.querySelector("[data-lt-balance-pill]");
    const startBtn = studioEl.querySelector("[data-lt-start]");
    const noticeEl = studioEl.querySelector("[data-lt-auth-notice]");
    const voiceSelect = studioEl.querySelector("[data-lt-voice]");

    if (!STATE.account) {
      if (acctBadge) acctBadge.textContent = "Chưa đăng nhập";
      if (balBadge) balBadge.textContent = "Số dư: — Xu";
      if (noticeEl) {
        const nextPath = encodeURIComponent(isFocusLiveMode() ? "/subdub?focus=live" : "/subdub");
        noticeEl.hidden = false;
        noticeEl.innerHTML =
          `Cần đăng nhập tài khoản <strong>app.toanaas.vn</strong> để liên kết Xu và dịch trực tiếp. <a href="/login?next=${nextPath}">Đăng nhập ngay</a>`;
      }
      if (startBtn) startBtn.disabled = false;
      return;
    }

    const acct = STATE.account;
    const label = acct.display_name || acct.email || "Tài khoản TOAN AAS";
    if (acctBadge) {
      acctBadge.textContent = `Tài khoản: ${label}`;
      acctBadge.classList.add("portal-lt-pill--ok");
    }

    const balanceXu = typeof STATE.balanceXu === "number" ? STATE.balanceXu : 0;
    if (balBadge) {
      balBadge.textContent = `Số dư: ${balanceXu.toLocaleString("vi-VN")} Xu`;
      balBadge.classList.toggle("portal-lt-pill--ok", balanceXu > 0 || STATE.isAdmin);
      balBadge.classList.toggle("portal-lt-pill--warn", balanceXu <= 0 && !STATE.isAdmin);
    }

    if (noticeEl) {
      if (balanceXu <= 0 && !STATE.isAdmin) {
        noticeEl.hidden = false;
        noticeEl.innerHTML =
          'Tài khoản cần nạp Xu (&gt; 0 Xu) để bật Dịch trực tiếp (giá bằng <strong>2x SubDub thông thường</strong>). <a href="/wallet/topup">Nạp Xu ngay</a>';
      } else {
        noticeEl.hidden = true;
      }
    }

    if (voiceSelect && Array.isArray(STATE.voiceProfiles)) {
      STATE.voiceProfiles.forEach((p) => {
        const val = `vault:${p.id}`;
        const exists = Array.from(voiceSelect.options).some((o) => o.value === val);
        if (!exists) {
          const opt = document.createElement("option");
          opt.value = val;
          opt.textContent = `Giọng riêng: ${p.name || p.id}`;
          voiceSelect.appendChild(opt);
        }
      });
    }
  }

  async function loadAccountAndWalletOnce() {
    try {
      const portalCtx = window.__TOAN_AAS_PORTAL__;
      if (portalCtx && portalCtx.session && portalCtx.session.authenticated === false) {
        STATE.account = null;
        STATE.csrfToken = "";
        STATE.balanceXu = null;
        STATE.accountLoaded = true;
        return;
      }

      const authRes = await fetch("/api/v1/auth/me", { credentials: "include" });
      if (!authRes.ok) {
        STATE.account = null;
        STATE.csrfToken = "";
        STATE.balanceXu = null;
        STATE.accountLoaded = true;
        return;
      }

      const authJson = await authRes.json();
      const data = authJson.data || {};
      const acct = data.account || {};
      STATE.account = acct;
      STATE.csrfToken = data.csrf_token || "";
      STATE.isAdmin = String(acct.role || acct.role_cache || "").trim().toLowerCase() === "admin";
      STATE.walletLinked = Boolean(acct.telegram_linked || acct.canonical_user_id);

      let balanceXu = 0;
      let walletOk = false;
      let hasWalletBalance = false;
      if (STATE.walletLinked) {
        let bridgeReady = null;
        const portalBridge = portalCtx && portalCtx.bridge;
        if (portalBridge && typeof portalBridge.bridge_configured === "boolean") {
          bridgeReady = portalBridge.bridge_configured;
        } else {
          try {
            const csRes = await fetch("/api/v1/core/status", { credentials: "include" });
            if (csRes.ok) {
              const csJson = await csRes.json();
              bridgeReady = Boolean(csJson && csJson.data && csJson.data.bridge_configured);
            }
          } catch (_) {}
        }

        if (bridgeReady !== false) {
          const wRes = await fetch("/api/v1/wallet", { credentials: "include" });
          if (wRes.ok) {
            const wJson = await wRes.json();
            const wData = wJson.data || {};
            if (typeof wData.balance_xu === "number") {
              balanceXu = wData.balance_xu;
              hasWalletBalance = true;
            } else if (typeof wData.balance === "number") {
              balanceXu = wData.balance;
              hasWalletBalance = true;
            }
            if (!wJson.ok && wJson.error_code === "ACCOUNT_TELEGRAM_UNLINKED") {
              STATE.walletLinked = false;
            }
            walletOk = Boolean(wJson.ok);
          }
        }
      }
      STATE.balanceXu = balanceXu;

      if (STATE.walletLinked && (walletOk || (STATE.isAdmin && hasWalletBalance))) {
        try {
          const vpRes = await fetch("/api/v1/voice/profiles", { credentials: "include" });
          if (vpRes.ok) {
            const vpJson = await vpRes.json();
            const items = (vpJson.data && vpJson.data.items) || [];
            STATE.voiceProfiles = items.filter(
              (p) => String(p.status || "").toLowerCase() === "ready" && p.id
            );
          }
        } catch (_) {}
      }
    } catch (_) {
    } finally {
      STATE.accountLoaded = true;
      STATE.accountPromise = null;
    }
  }

  async function refreshAccountAndWallet(studioEl) {
    if (STATE.accountLoaded) {
      applyAccountStateToStudio(studioEl);
      return;
    }
    if (!STATE.accountPromise) {
      STATE.accountPromise = loadAccountAndWalletOnce();
    }
    await STATE.accountPromise;
    applyAccountStateToStudio(studioEl);
  }

  function updateStage(studioEl) {
    const origEl = studioEl.querySelector("[data-lt-orig]");
    const transEl = studioEl.querySelector("[data-lt-trans]");
    const statEl = studioEl.querySelector("[data-lt-status]");
    const feeEl = studioEl.querySelector("[data-lt-fee]");
    if (origEl) origEl.textContent = STATE.lastOrig;
    if (transEl) transEl.textContent = STATE.lastTrans;
    if (statEl && STATE.lastStatus) statEl.textContent = STATE.lastStatus;
    if (feeEl) feeEl.textContent = `Đã khấu trừ phiên này: ${STATE.spentXu} Xu`;

    if (STATE.pipWindow && !STATE.pipWindow.closed) {
      const pOrig = STATE.pipWindow.document.getElementById("pip-orig");
      const pTrans = STATE.pipWindow.document.getElementById("pip-trans");
      if (pOrig) pOrig.textContent = STATE.lastOrig;
      if (pTrans) pTrans.textContent = STATE.lastTrans;
    }
  }

  function playTtsBase64(b64) {
    if (!b64 || STATE.dubMuted) return;
    try {
      if (!STATE.playbackCtx || STATE.playbackCtx.state === "closed") {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        STATE.playbackCtx = new AudioCtx();
        STATE.nextPlaybackTime = 0;
      }
      if (STATE.playbackCtx.state === "suspended") {
        STATE.playbackCtx.resume().catch(() => {});
      }
      const bin = atob(b64);
      const bytes = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i += 1) {
        bytes[i] = bin.charCodeAt(i);
      }
      STATE.playbackCtx.decodeAudioData(bytes.buffer.slice(0), function (decoded) {
        const src = STATE.playbackCtx.createBufferSource();
        src.buffer = decoded;
        src.connect(STATE.playbackCtx.destination);
        const now = STATE.playbackCtx.currentTime;
        const startAt = Math.max(now + 0.02, STATE.nextPlaybackTime || now);
        src.start(startAt);
        STATE.nextPlaybackTime = startAt + decoded.duration;
      });
    } catch (_) {}
  }

  function downsampleFloatTo16k(floatBuf, inputSampleRate) {
    const targetRate = 16000;
    const ratio = inputSampleRate / targetRate;
    const outLen = Math.max(1, Math.floor(floatBuf.length / ratio));
    const pcm = new Int16Array(outLen);
    for (let i = 0; i < outLen; i += 1) {
      const srcIdx = Math.min(floatBuf.length - 1, Math.floor(i * ratio));
      const s = Math.max(-1, Math.min(1, floatBuf[srcIdx]));
      pcm[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    return pcm;
  }

  function ensurePlaybackCtxUnlocked() {
    try {
      if (!STATE.playbackCtx || STATE.playbackCtx.state === "closed") {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (AudioCtx) {
          STATE.playbackCtx = new AudioCtx();
          STATE.nextPlaybackTime = 0;
        }
      }
      if (STATE.playbackCtx && STATE.playbackCtx.state === "suspended") {
        STATE.playbackCtx.resume().catch(() => {});
      }
    } catch (_) {}
  }

  function syncMuteUi(studioEl) {
    const muteBtn = studioEl.querySelector("[data-lt-mute]");
    if (muteBtn) {
      muteBtn.textContent = STATE.dubMuted
        ? "🔇 Âm thanh lồng tiếng: Tắt"
        : "🔊 Âm thanh lồng tiếng: Bật";
    }
    if (STATE.pipWindow && !STATE.pipWindow.closed) {
      const pipMute = STATE.pipWindow.document.getElementById("pip-mute");
      if (pipMute) {
        pipMute.textContent = STATE.dubMuted ? "🔇 Tắt dub" : "🔊 Lồng tiếng";
      }
    }
  }

  async function openPipOverlay(studioEl) {
    if (!("documentPictureInPicture" in window)) {
      STATE.lastStatus = "Trình duyệt không hỗ trợ Document Picture-in-Picture; xem phụ đề trực tiếp bên dưới.";
      updateStage(studioEl);
      return;
    }
    try {
      const pipWin = await window.documentPictureInPicture.requestWindow({ width: 460, height: 225 });
      STATE.pipWindow = pipWin;
      const doc = pipWin.document;
      doc.body.style.cssText =
        "margin:0;padding:12px 14px;background:rgba(9,13,22,0.96);color:#f8fafc;font-family:system-ui,sans-serif;display:flex;flex-direction:column;gap:6px;";
      const hdrRow = doc.createElement("div");
      hdrRow.style.cssText = "display:flex;justify-content:space-between;align-items:center;gap:8px;";
      const hdr = doc.createElement("div");
      hdr.style.cssText = "font-size:12px;font-weight:700;color:#51d5bc;";
      hdr.textContent = "TOAN AAS · Phụ đề & Lồng tiếng (2x SubDub)";
      const pipControls = doc.createElement("div");
      pipControls.style.cssText = "display:flex;gap:6px;";
      const pipMute = doc.createElement("button");
      pipMute.id = "pip-mute";
      pipMute.type = "button";
      pipMute.style.cssText =
        "padding:4px 8px;border-radius:6px;border:1px solid #1e4e57;background:#0f2e36;color:#f0fdfa;font-size:11px;cursor:pointer;";
      pipMute.textContent = STATE.dubMuted ? "🔇 Tắt dub" : "🔊 Lồng tiếng";
      pipMute.addEventListener("click", () => {
        STATE.dubMuted = !STATE.dubMuted;
        syncMuteUi(studioEl);
      });
      const pipStop = doc.createElement("button");
      pipStop.id = "pip-stop";
      pipStop.type = "button";
      pipStop.style.cssText =
        "padding:4px 8px;border-radius:6px;border:1px solid #991b1b;background:#dc2626;color:#fff;font-size:11px;cursor:pointer;";
      pipStop.textContent = "⏹ Dừng";
      pipStop.addEventListener("click", () => {
        stopStudioSession(studioEl, { userInitiated: true });
      });
      pipControls.append(pipMute, pipStop);
      hdrRow.append(hdr, pipControls);

      const orig = doc.createElement("div");
      orig.id = "pip-orig";
      orig.style.cssText = "font-size:13px;color:#cbd5e1;line-height:1.4;";
      orig.textContent = STATE.lastOrig;
      const trans = doc.createElement("div");
      trans.id = "pip-trans";
      trans.style.cssText = "font-size:17px;font-weight:700;color:#ffffff;line-height:1.4;";
      trans.textContent = STATE.lastTrans;
      doc.body.append(hdrRow, orig, trans);
    } catch (_) {}
  }

  async function stopStudioSession(studioEl, { userInitiated = true } = {}) {
    const startBtn = studioEl.querySelector("[data-lt-start]");
    const stopBtn = studioEl.querySelector("[data-lt-stop]");

    if (STATE.mediaStream) {
      STATE.mediaStream.getTracks().forEach((t) => {
        try { t.stop(); } catch (_) {}
      });
      STATE.mediaStream = null;
    }
    if (STATE.audioCtx && STATE.audioCtx.state !== "closed") {
      try { await STATE.audioCtx.close(); } catch (_) {}
      STATE.audioCtx = null;
    }
    if (STATE.ws && STATE.ws.readyState === WebSocket.OPEN) {
      if (userInitiated) {
        try {
          STATE.ws.send(JSON.stringify({ type: "session.control", action: "stop" }));
        } catch (_) {}
      }
      setTimeout(() => {
        try { if (STATE.ws) STATE.ws.close(1000, "stopped"); } catch (_) {}
      }, 450);
    }
    if (STATE.sessionId) {
      try {
        await fetch(`/api/v1/live-translate/sessions/${encodeURIComponent(STATE.sessionId)}/stop`, {
          method: "POST",
          credentials: "include",
          headers: STATE.csrfToken ? { "X-CSRF-Token": STATE.csrfToken } : {},
        });
      } catch (_) {}
    }

    STATE.active = false;
    STATE.lastStatus = "Phiên dịch trực tiếp đã dừng.";
    if (startBtn) startBtn.hidden = false;
    if (stopBtn) stopBtn.hidden = true;
    updateStage(studioEl);
    STATE.accountLoaded = false;
    refreshAccountAndWallet(studioEl);
  }

  async function startStudioSession(studioEl) {
    // Unlock audio context synchronously on user gesture so delayed TTS playback works smoothly
    ensurePlaybackCtxUnlocked();

    const mode = studioEl.querySelector("[data-lt-mode]")?.value || "LIVE_DUB_BILINGUAL";
    const sourceLang = studioEl.querySelector("[data-lt-source-lang]")?.value || "auto";
    const targetLang = studioEl.querySelector("[data-lt-lang]")?.value || "vi";
    const voiceRaw = studioEl.querySelector("[data-lt-voice]")?.value || "male";
    const voiceProfileId = voiceRaw.startsWith("vault:") ? voiceRaw.slice(6) : null;
    const genderPreference = voiceRaw.startsWith("vault:") ? "male" : voiceRaw;

    if (!STATE.account) {
      const nextPath = encodeURIComponent(isFocusLiveMode() ? "/subdub?focus=live" : "/subdub");
      window.location.href = `/login?next=${nextPath}`;
      return;
    }

    const startBtn = studioEl.querySelector("[data-lt-start]");
    const stopBtn = studioEl.querySelector("[data-lt-stop]");
    const exportBtn = studioEl.querySelector("[data-lt-export]");

    STATE.spentXu = 0;
    STATE.lastStatus = "Đang khởi tạo phiên trên máy chủ...";
    updateStage(studioEl);

    const headers = { "Content-Type": "application/json" };
    if (STATE.csrfToken) headers["X-CSRF-Token"] = STATE.csrfToken;

    const createRes = await fetch("/api/v1/live-translate/sessions", {
      method: "POST",
      credentials: "include",
      headers,
      body: JSON.stringify({
        source_language: sourceLang,
        target_language: targetLang,
        mode,
        voice_profile_id: voiceProfileId,
        gender_preference: genderPreference,
        device_id: "web-tab-studio",
      }),
    });

    if (!createRes.ok) {
      let msg = "Không thể bắt đầu phiên dịch trực tiếp.";
      try {
        const errJson = await createRes.json();
        msg = errJson.message || errJson.detail || msg;
      } catch (_) {}
      STATE.lastStatus = `Bị từ chối (${createRes.status}): ${msg}`;
      updateStage(studioEl);
      return;
    }

    const sess = await createRes.json();
    STATE.sessionId = sess.session_id;
    STATE.streamToken = sess.stream_token;

    if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
      STATE.lastStatus = "Trình duyệt hiện tại không hỗ trợ bắt âm thanh Tab (hãy dùng Google Chrome trên máy tính).";
      updateStage(studioEl);
      return;
    }

    let stream;
    try {
      stream = await navigator.mediaDevices.getDisplayMedia({
        video: true,
        audio: {
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false,
        },
        systemAudio: "include",
      });
    } catch (err) {
      STATE.lastStatus = "Bạn đã đóng cửa sổ chọn Tab Chrome.";
      await stopStudioSession(studioEl, { userInitiated: false });
      return;
    }

    const audioTracks = stream.getAudioTracks();
    if (!audioTracks || audioTracks.length === 0) {
      stream.getTracks().forEach((t) => t.stop());
      STATE.lastStatus =
        "Chưa nhận được âm thanh Tab! Vui lòng bấm Bắt đầu lại và bật nút 'Chia sẻ âm thanh thẻ' (Share tab audio).";
      await stopStudioSession(studioEl, { userInitiated: false });
      return;
    }

    STATE.mediaStream = stream;
    STATE.active = true;
    STATE.seqCounter = 0;
    let ackCount = 0;
    if (startBtn) startBtn.hidden = true;
    if (stopBtn) stopBtn.hidden = false;
    if (exportBtn) exportBtn.hidden = false;

    audioTracks[0].onended = function () {
      stopStudioSession(studioEl, { userInitiated: true });
    };

    const wsProto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${wsProto}//${window.location.host}${sess.websocket_url}`;
    const ws = new WebSocket(wsUrl);
    ws.binaryType = "arraybuffer";
    STATE.ws = ws;

    ws.onopen = function () {
      STATE.lastStatus = "Đang nghe âm thanh Tab Chrome & dịch trực tiếp...";
      updateStage(studioEl);

      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      const ctx = new AudioCtx();
      STATE.audioCtx = ctx;
      const source = ctx.createMediaStreamSource(new MediaStream([audioTracks[0]]));
      const processor = ctx.createScriptProcessor(4096, 1, 1);
      const silentGain = ctx.createGain();
      silentGain.gain.value = 0;

      let pcmStash = [];
      let stashSamples = 0;
      const FRAME_SAMPLES = 3200; // 200ms @ 16kHz

      processor.onaudioprocess = function (ev) {
        if (!STATE.active || !STATE.ws || STATE.ws.readyState !== WebSocket.OPEN) return;
        const input = ev.inputBuffer.getChannelData(0);
        const pcm16 = downsampleFloatTo16k(input, ctx.sampleRate);
        pcmStash.push(pcm16);
        stashSamples += pcm16.length;

        while (stashSamples >= FRAME_SAMPLES) {
          const merged = new Int16Array(stashSamples);
          let off = 0;
          for (const chunk of pcmStash) {
            merged.set(chunk, off);
            off += chunk.length;
          }
          const slice = merged.subarray(0, FRAME_SAMPLES);
          const rem = merged.subarray(FRAME_SAMPLES);
          pcmStash = rem.length > 0 ? [rem] : [];
          stashSamples = rem.length;

          STATE.seqCounter += 1;
          const pkt = new ArrayBuffer(4 + slice.byteLength);
          new DataView(pkt).setUint32(0, STATE.seqCounter, true);
          new Uint8Array(pkt, 4).set(new Uint8Array(slice.buffer, slice.byteOffset, slice.byteLength));
          try {
            STATE.ws.send(pkt);
          } catch (_) {}
        }
      };

      source.connect(processor);
      processor.connect(silentGain);
      silentGain.connect(ctx.destination);
    };

    ws.onmessage = function (ev) {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === "stt.final") {
          const txt = msg.source_text || msg.text || "";
          if (txt) {
            STATE.lastOrig = txt;
            STATE.lastStatus = "Đang dịch & tổng hợp giọng nói...";
          }
        } else if (msg.type === "translation.final") {
          if (msg.translated_text) {
            STATE.lastTrans = msg.translated_text;
            STATE.lastStatus = "Đang phát lồng tiếng & cập nhật phụ đề...";
          }
        } else if (msg.type === "tts.audio") {
          if (msg.audio_b64) {
            playTtsBase64(msg.audio_b64);
          } else if (msg.error) {
            STATE.lastStatus = `⚠ Lỗi tạo giọng đọc: ${msg.error}`;
          }
        } else if (msg.type === "ack") {
          ackCount += 1;
          STATE.lastStatus = `Đang hoạt động · đã xử lý ${ackCount} đoạn âm thanh.`;
        } else if (msg.type === "settlement.updated" || msg.type === "usage.updated") {
          if (typeof msg.total_xu_consumed === "number") {
            STATE.spentXu = msg.total_xu_consumed;
          }
          if (typeof msg.balance_after === "number") {
            STATE.balanceXu = msg.balance_after;
            const balBadge = studioEl.querySelector("[data-lt-balance-pill]");
            if (balBadge) balBadge.textContent = `Số dư: ${msg.balance_after.toLocaleString("vi-VN")} Xu`;
          }
        } else if (msg.type === "session.error") {
          STATE.lastStatus = msg.message || msg.error_code || "Lỗi phiên dịch.";
          if (msg.error_code === "INSUFFICIENT_FUNDS") {
            stopStudioSession(studioEl, { userInitiated: false });
          }
        }
        updateStage(studioEl);
      } catch (_) {}
    };

    ws.onclose = function (ev) {
      if (STATE.active && ev.code >= 4000) {
        STATE.lastStatus = `Kết nối đã đóng (${ev.code}): ${ev.reason || "Hết phiên"}`;
        stopStudioSession(studioEl, { userInitiated: false });
      }
    };
  }

  function mountStudioIfReady() {
    syncFocusModeClass();
    if (!isSubdubRoute()) return;
    const card = document.querySelector(".portal-subdub-extension-card");
    if (!card || card.querySelector("[data-lt-studio]")) return;

    const focusMode = isFocusLiveMode();
    const el = document.createElement("div");
    el.className = "portal-lt-studio";
    el.setAttribute("data-lt-studio", "true");
    el.innerHTML = `
      <div class="portal-lt-studio-head">
        <div class="portal-lt-studio-meta">
          <span class="portal-lt-pill" data-lt-account-pill>Đang kiểm tra tài khoản...</span>
          <span class="portal-lt-pill" data-lt-balance-pill>Số dư: — Xu</span>
          <span class="portal-lt-pill">Cước: 2x SubDub</span>
        </div>
        <div class="portal-lt-actions">
          ${
            focusMode
              ? '<a class="portal-lt-btn" href="/subdub">↩ Trang đầy đủ</a>'
              : '<button type="button" class="portal-lt-btn" data-lt-open-focus>🗗 Mở cửa sổ CHỈ Phụ đề &amp; Lồng tiếng</button>'
          }
        </div>
      </div>
      <div class="portal-lt-notice" data-lt-auth-notice hidden></div>
      <div class="portal-lt-controls">
        <div class="portal-lt-field">
          <label for="lt-mode-select">Chế độ</label>
          <select id="lt-mode-select" data-lt-mode>
            <option value="LIVE_DUB_BILINGUAL" selected>Lồng tiếng + Phụ đề song ngữ</option>
            <option value="CAPTION_TRANSLATE">Chỉ phụ đề dịch (Không lồng tiếng)</option>
            <option value="CAPTION_ONLY">Chỉ nhận diện phụ đề gốc</option>
          </select>
        </div>
        <div class="portal-lt-field">
          <label for="lt-source-lang-select">Ngôn ngữ video gốc</label>
          <select id="lt-source-lang-select" data-lt-source-lang>
            <option value="auto" selected>Tự động nhận diện</option>
            <option value="zh">Tiếng Trung (zh)</option>
            <option value="en">Tiếng Anh (en)</option>
            <option value="ja">Tiếng Nhật (ja)</option>
            <option value="ko">Tiếng Hàn (ko)</option>
          </select>
        </div>
        <div class="portal-lt-field">
          <label for="lt-lang-select">Dịch sang</label>
          <select id="lt-lang-select" data-lt-lang>
            <option value="vi" selected>Tiếng Việt (vi)</option>
            <option value="en">English (en)</option>
            <option value="zh">Tiếng Trung (zh)</option>
            <option value="ja">Tiếng Nhật (ja)</option>
          </select>
        </div>
        <div class="portal-lt-field">
          <label for="lt-voice-select">Giọng lồng tiếng</label>
          <select id="lt-voice-select" data-lt-voice>
            <option value="male" selected>Nam Minh (Giọng Nam)</option>
            <option value="female">Hoài My (Giọng Nữ)</option>
          </select>
        </div>
      </div>
      <div class="portal-lt-actions">
        <button type="button" class="portal-lt-btn portal-lt-btn--accent" data-lt-start>▶ Dịch &amp; Lồng tiếng Tab Chrome ngay</button>
        <button type="button" class="portal-lt-btn portal-lt-btn--danger" data-lt-stop hidden>⏹ Dừng phiên dịch</button>
        <button type="button" class="portal-lt-btn" data-lt-pip>❐ Phụ đề nổi (PiP)</button>
        <button type="button" class="portal-lt-btn" data-lt-mute>🔊 Âm thanh lồng tiếng: Bật</button>
        <button type="button" class="portal-lt-btn" data-lt-export hidden>⬇ Tải phụ đề (.srt)</button>
      </div>
      <div class="portal-lt-stage">
        <div class="portal-lt-caption-orig" data-lt-orig></div>
        <div class="portal-lt-caption-trans" data-lt-trans></div>
        <div class="portal-lt-status-row">
          <span data-lt-status>Sẵn sàng chạy trực tiếp trên Tab Chrome.</span>
          <span data-lt-fee>Đã khấu trừ phiên này: 0 Xu</span>
        </div>
      </div>
      <details class="portal-lt-ext-details">
        <summary>Cài đặt Chrome Extension / Ứng dụng Chrome độc lập (Tùy chọn)</summary>
        <div class="portal-lt-ext-body">
          <p class="portal-lt-ext-note">
            Chrome không cho phép trang web tự nhét tiện ích chưa lên Chrome Web Store vào menu Tiện ích.
            Bạn có thể dùng ngay nút <strong>▶ Dịch &amp; Lồng tiếng Tab Chrome ngay</strong> ở trên, hoặc cài Extension thủ công 1 lần qua <code>chrome://extensions</code> (bật Developer mode → Load unpacked → chọn thư mục đã giải nén).
          </p>
          <div class="portal-lt-actions">
            <a class="portal-lt-btn" href="/api/v1/live-translate/extension-download" download="toan-aas-chrome-live-translate.zip">⬇ Tải Extension (.zip)</a>
            <button type="button" class="portal-lt-btn" data-lt-copy-ext-url>Copy chrome://extensions</button>
            <button type="button" class="portal-lt-btn" data-lt-install-chrome>Mở qua ứng dụng Chrome</button>
          </div>
        </div>
      </details>
    `;

    card.appendChild(el);
    updateInstallButtons();
    updateStage(el);
    refreshAccountAndWallet(el);

    const openFocusBtn = el.querySelector("[data-lt-open-focus]");
    if (openFocusBtn) {
      openFocusBtn.addEventListener("click", function () {
        const w = window.open(
          "/subdub?focus=live",
          "toanaas_live_subdub",
          "popup=yes,width=490,height=660,menubar=no,toolbar=no,location=no,status=no"
        );
        if (!w) {
          window.location.href = "/subdub?focus=live";
        }
      });
    }

    el.querySelector("[data-lt-install-chrome]").addEventListener("click", function () {
      triggerChromeAppInstall(el.querySelector("[data-lt-status]"));
    });

    el.querySelector("[data-lt-copy-ext-url]").addEventListener("click", async function (ev) {
      const btn = ev.currentTarget;
      try {
        await navigator.clipboard.writeText("chrome://extensions");
        btn.textContent = "Đã copy chrome://extensions!";
        const statusEl = el.querySelector("[data-lt-status]");
        if (statusEl) {
          statusEl.textContent = "Đã copy 'chrome://extensions' — mở tab mới, dán (Ctrl+V), bật Developer mode → Load unpacked → chọn thư mục đã giải nén.";
        }
        setTimeout(() => { btn.textContent = "Copy chrome://extensions"; }, 2500);
      } catch (_) {}
    });

    el.querySelector("[data-lt-start]").addEventListener("click", function () {
      startStudioSession(el);
    });

    el.querySelector("[data-lt-stop]").addEventListener("click", function () {
      stopStudioSession(el, { userInitiated: true });
    });

    el.querySelector("[data-lt-pip]").addEventListener("click", function () {
      openPipOverlay(el);
    });

    el.querySelector("[data-lt-mute]").addEventListener("click", function () {
      STATE.dubMuted = !STATE.dubMuted;
      syncMuteUi(el);
    });

    el.querySelector("[data-lt-export]").addEventListener("click", async function () {
      if (!STATE.sessionId) return;
      const res = await fetch(
        `/api/v1/live-translate/sessions/${encodeURIComponent(STATE.sessionId)}/export?format=srt`,
        { credentials: "include" }
      );
      if (!res.ok) return;
      const data = await res.json();
      const blob = new Blob([data.content || ""], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `toanaas-live-${STATE.sessionId}.srt`;
      a.click();
      URL.revokeObjectURL(url);
    });
  }

  const observer = new MutationObserver(function () {
    mountStudioIfReady();
  });

  function boot() {
    syncFocusModeClass();
    mountStudioIfReady();
    const root = document.getElementById("portal-main") || document.body;
    if (root) {
      observer.observe(root, { childList: true, subtree: true });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
