/**
 * Offscreen Document Worker for TOAN AAS Live Translate & Dub (Manifest V3 / RT-FIX11).
 * Handles tab audio capture, 16kHz PCM downsampling, binary sequence streaming,
 * WebSocket lifecycle with unacked frame buffer and session reconnect/replay,
 * audio ducking with TTS playback, lossless buffer retention with fail-closed overflow,
 * handshake-governed reconnect budget, and authoritative stop confirmation.
 * Governed by owner-governed-codex, locked-focus-engineering.
 */

let audioContext = null;
let mediaStream = null;
let originalGainNode = null;
let scriptProcessor = null;
let webSocket = null;
let currentSeq = 0;
let lastAckSeq = 0;
let isCapturing = false;
let currentConfig = null;
let reconnectAttempts = 0;
let reconnectTimer = null;
let isReplaying = false;
let isReconnecting = false;
let stopConfirmationResolver = null;

const MAX_RECONNECT_ATTEMPTS = 5;
const INITIAL_RECONNECT_DELAY_MS = 500;
const MAX_UNACKED_FRAMES = 500;

// Bounded map of sequence -> Uint8Array binary frame [uint32 sequence LE][PCM 16-bit bytes]
const unackedFrames = new Map();

// Terminal closure codes that must fail-closed immediately without reconnect (AUTH_TERMINAL_CLOSE_NO_RETRY)
const TERMINAL_CLOSE_CODES = new Set([4401, 4403, 4404, 4001, 4003, 4004, 1008]);

if (typeof chrome !== "undefined" && chrome.runtime?.onMessage) {
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === "INIT_AUDIO_CAPTURE") {
      startCapture(message.streamId, message.config).then(() => {
        if (typeof sendResponse === "function") sendResponse({ ok: true });
      }).catch((err) => {
        console.error("[TOAN_AAS_OFFSCREEN] Capture initialization failed:", err);
        notifyFailure(err.message);
        if (typeof sendResponse === "function") sendResponse({ ok: false, error: err.message });
      });
      return true;
    } else if (message.type === "STOP_AUDIO_CAPTURE") {
      stopCapture({ force: !!message.force })
        .then((res) => {
          if (typeof sendResponse === "function") sendResponse(res);
        })
        .catch((err) => {
          if (typeof sendResponse === "function") sendResponse({ ok: false, error: err.message });
        });
      return true;
    }
  });
}

function notifyFailure(errorMessage) {
  stopCapture({ force: true });
  if (typeof chrome !== "undefined" && chrome.runtime?.sendMessage) {
    chrome.runtime.sendMessage({
      type: "OFFSCREEN_ERROR",
      error: errorMessage,
    });
  }
}

async function startCapture(streamId, config) {
  await stopCapture({ force: true });
  currentSeq = 0;
  lastAckSeq = 0;
  reconnectAttempts = 0;
  isReplaying = false;
  isReconnecting = false;
  unackedFrames.clear();
  currentConfig = config;
  isCapturing = true;

  if (!config?.websocketUrl) {
    throw new Error("Missing exact websocketUrl in offscreen configuration");
  }

  // 1. Capture tab media stream
  try {
    if (typeof navigator !== "undefined" && navigator.mediaDevices?.getUserMedia) {
      mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          mandatory: {
            chromeMediaSource: "tab",
            chromeMediaSourceId: streamId,
          },
        },
        video: false,
      });
    }
  } catch (err) {
    throw new Error(`getUserMedia tabCapture failed: ${err.message}`);
  }

  const AudioContextClass = typeof window !== "undefined" ? (window.AudioContext || window.webkitAudioContext) : null;
  if (AudioContextClass) {
    audioContext = new AudioContextClass();
    const source = audioContext.createMediaStreamSource(mediaStream);

    // 2. Loopback to destination with Audio Ducking GainNode (NO TAB MUTING)
    originalGainNode = audioContext.createGain();
    originalGainNode.gain.setValueAtTime(1.0, audioContext.currentTime);
    source.connect(originalGainNode);
    originalGainNode.connect(audioContext.destination);

    // 3. Downsample to 16kHz mono PCM and stream with monotonic sequence
    const inputSampleRate = audioContext.sampleRate;
    const targetSampleRate = 16000;
    const bufferSize = 4096;

    scriptProcessor = audioContext.createScriptProcessor(bufferSize, 1, 1);
    scriptProcessor.onaudioprocess = (e) => {
      if (!isCapturing) return;

      const inputData = e.inputBuffer.getChannelData(0);
      const pcm16 = downsampleAndConvertToPcm16(inputData, inputSampleRate, targetSampleRate);
      if (pcm16 && pcm16.byteLength > 0) {
        currentSeq += 1;
        // Binary envelope: [uint32 sequence LE][PCM 16-bit bytes]
        const frame = new Uint8Array(4 + pcm16.byteLength);
        new DataView(frame.buffer).setUint32(0, currentSeq, true);
        frame.set(new Uint8Array(pcm16.buffer), 4);

        // Retain frame in unacked buffer (lossless, bounded with fail-closed overflow)
        const recorded = recordUnackedFrame(currentSeq, frame);
        if (!recorded) return;

        if (webSocket && webSocket.readyState === (typeof WebSocket !== "undefined" ? WebSocket.OPEN : 1) && !isReplaying) {
          webSocket.send(frame.buffer);
        }
      }
    };

    source.connect(scriptProcessor);
    scriptProcessor.connect(audioContext.destination);
  }

  // 4. Connect WebSocket with lifecycle management
  initWebSocket();
}

/**
 * Lossless unacked-frame buffer retention (RT-FIX10/11).
 * Prevents silent audio loss (UNACKED_FRAME_SILENT_DROP=0).
 * When capacity is reached, applies fail-closed backpressure (UNACKED_OVERFLOW_FAIL_CLOSED_OR_BACKPRESSURE=PASS).
 */
function recordUnackedFrame(seq, frame) {
  if (unackedFrames.size >= MAX_UNACKED_FRAMES) {
    console.error(`[TOAN_AAS_OFFSCREEN] Unacked buffer limit reached (${unackedFrames.size} >= ${MAX_UNACKED_FRAMES}). Failing closed to prevent silent audio loss.`);
    notifyFailure(`Bộ đệm khung chưa xác nhận đã đầy (${MAX_UNACKED_FRAMES} khung). Dừng phiên làm việc.`);
    return false;
  }
  unackedFrames.set(seq, frame);
  return true;
}

function attachWebSocketHandlers(ws) {
  if (!ws) return;
  ws.binaryType = "arraybuffer";

  ws.onopen = () => {
    console.log("[TOAN_AAS_OFFSCREEN] WebSocket connected.");
    // Note: Reconnect budget resets strictly after authoritative server handshake (session.ready / session.reconnected)

    // CLIENT_SESSION_RECONNECT_SENT: If reconnecting existing session with prior sequence progress
    if (currentSeq > 0 || lastAckSeq > 0) {
      isReconnecting = true;
      console.log(`[TOAN_AAS_OFFSCREEN] Sending session.reconnect with lastAckSeq=${lastAckSeq}`);
      const reconMsg = JSON.stringify({
        type: "session.reconnect",
        last_ack_seq: lastAckSeq,
      });
      ws.send(reconMsg);
    }
  };

  ws.onerror = (err) => {
    console.error("[TOAN_AAS_OFFSCREEN] WebSocket error:", err);
  };

  ws.onclose = (event) => {
    console.warn(`[TOAN_AAS_OFFSCREEN] WebSocket closed (code ${event.code}): ${event.reason}`);

    // If waiting for stop confirmation and socket closed cleanly (code 1000/ended), resolve stop
    if (typeof stopConfirmationResolver === "function") {
      stopConfirmationResolver(true);
      stopConfirmationResolver = null;
    }

    // AUTH_TERMINAL_CLOSE_NO_RETRY: Terminal close codes must fail closed immediately
    if (TERMINAL_CLOSE_CODES.has(event.code)) {
      console.error(`[TOAN_AAS_OFFSCREEN] Terminal server close (${event.code}): ${event.reason}. No retry.`);
      notifyFailure(`Máy chủ từ chối kết nối (${event.code}): ${event.reason}`);
      return;
    }

    // RECONNECT_RETRY_BOUNDED: Non-terminal disconnection, attempt bounded reconnect
    if (isCapturing) {
      scheduleReconnect();
    }
  };

  ws.onmessage = (event) => {
    handleDownstreamEvent(event.data);
  };
}

function initWebSocket() {
  if (!isCapturing || !currentConfig?.websocketUrl) return;

  try {
    webSocket = new WebSocket(currentConfig.websocketUrl);
  } catch (e) {
    console.error("[TOAN_AAS_OFFSCREEN] Failed to initialize WebSocket:", e);
    scheduleReconnect();
    return;
  }

  attachWebSocketHandlers(webSocket);
}

function scheduleReconnect() {
  if (!isCapturing) return;

  if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
    console.error(`[TOAN_AAS_OFFSCREEN] Reconnect attempts exhausted (${MAX_RECONNECT_ATTEMPTS}).`);
    notifyFailure("Kết nối máy chủ bị ngắt và không thể khôi phục sau nhiều lần thử lại.");
    return;
  }

  isReconnecting = true;
  reconnectAttempts += 1;
  const delay = INITIAL_RECONNECT_DELAY_MS * Math.pow(2, reconnectAttempts - 1);
  console.log(`[TOAN_AAS_OFFSCREEN] Scheduling reconnect attempt #${reconnectAttempts} in ${delay}ms...`);

  if (reconnectTimer) clearTimeout(reconnectTimer);
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    if (isCapturing) {
      initWebSocket();
    }
  }, delay);
}

function evictAcknowledgedFrames(ackedSeq) {
  for (const seq of unackedFrames.keys()) {
    if (seq <= ackedSeq) {
      unackedFrames.delete(seq);
    }
  }
}

function replayUnackedFrames() {
  if (!webSocket || webSocket.readyState !== (typeof WebSocket !== "undefined" ? WebSocket.OPEN : 1)) {
    return;
  }

  isReplaying = true;
  console.log(`[TOAN_AAS_OFFSCREEN] Replaying ${unackedFrames.size} unacked frames starting after seq=${lastAckSeq}...`);

  for (const [seq, frame] of unackedFrames.entries()) {
    if (seq > lastAckSeq) {
      webSocket.send(frame.buffer);
    }
  }
  isReplaying = false;
}

function downsampleAndConvertToPcm16(inputData, inputSampleRate, targetSampleRate) {
  if (!inputData || inputData.length === 0) return null;
  if (inputSampleRate === targetSampleRate) {
    const pcm16 = new Int16Array(inputData.length);
    for (let i = 0; i < inputData.length; i++) {
      let s = Math.max(-1, Math.min(1, inputData[i]));
      pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return pcm16;
  }

  const sampleRatio = inputSampleRate / targetSampleRate;
  const newLength = Math.round(inputData.length / sampleRatio);
  const pcm16 = new Int16Array(newLength);

  let offsetResult = 0;
  let offsetBuffer = 0;

  while (offsetResult < newLength) {
    const nextOffsetBuffer = Math.round((offsetResult + 1) * sampleRatio);
    let accum = 0;
    let count = 0;
    for (let i = offsetBuffer; i < nextOffsetBuffer && i < inputData.length; i++) {
      accum += inputData[i];
      count++;
    }
    const sample = count > 0 ? accum / count : 0;
    let s = Math.max(-1, Math.min(1, sample));
    pcm16[offsetResult] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    offsetResult++;
    offsetBuffer = nextOffsetBuffer;
  }

  return pcm16;
}

async function handleDownstreamEvent(rawData) {
  if (typeof rawData !== "string") return;

  try {
    const event = JSON.parse(rawData);

    // RT-FIX11: Reconnect budget resets strictly after authoritative server handshake.
    // When reconnecting prior progress, session.ready is emitted before session.reconnect is processed;
    // budget MUST NOT reset on session.ready during reconnect (RECONNECT_BUDGET_RESETS_ON_RECONNECT_READY=NO).
    if (event.type === "session.ready") {
      if (isReconnecting || currentSeq > 0 || lastAckSeq > 0) {
        console.log("[TOAN_AAS_OFFSCREEN] In-flight reconnect: withholding budget reset on session.ready; awaiting session.reconnected.");
      } else {
        reconnectAttempts = 0;
        console.log("[TOAN_AAS_OFFSCREEN] Initial session ready. Reconnect budget initialized.");
      }
    } else if (event.type === "session.reconnected") {
      // RECONNECT_BUDGET_RESETS_AFTER_SESSION_RECONNECTED=YES
      isReconnecting = false;
      reconnectAttempts = 0;
      console.log("[TOAN_AAS_OFFSCREEN] Authoritative session.reconnected received: reconnect budget reset.");
    }

    // Stop confirmation from server (session.state ended)
    if (event.type === "session.state" && event.state === "ended") {
      if (typeof stopConfirmationResolver === "function") {
        stopConfirmationResolver(true);
        stopConfirmationResolver = null;
      }
      return;
    }

    // 1. Session Reconnected acknowledgment from server
    if (event.type === "session.reconnected") {
      const serverLastAck = typeof event.server_last_ack_seq === "number" ? event.server_last_ack_seq : lastAckSeq;
      lastAckSeq = Math.max(lastAckSeq, serverLastAck);
      evictAcknowledgedFrames(lastAckSeq);
      replayUnackedFrames();
      return;
    }

    // 2. Cumulative ACK: evict acknowledged frames from unacked buffer
    if (event.type === "ack" && typeof event.seq === "number") {
      const ackSeq = event.seq;
      if (ackSeq > lastAckSeq) {
        lastAckSeq = ackSeq;
      }
      evictAcknowledgedFrames(lastAckSeq);
    }

    // 3. Audio Ducking & TTS playback (consumes canonical Bot audio_b64, fallback audio_base64)
    const rawAudioB64 = event.audio_b64 || event.audio_base64;
    if (event.type === "tts.audio" && rawAudioB64 && originalGainNode && audioContext) {
      originalGainNode.gain.cancelScheduledValues(audioContext.currentTime);
      originalGainNode.gain.setValueAtTime(0.25, audioContext.currentTime);

      const atobFn = typeof atob === "function" ? atob : (b64) => Buffer.from(b64, "base64").toString("binary");
      const binaryString = atobFn(rawAudioB64);
      const len = binaryString.length;
      const bytes = new Uint8Array(len);
      for (let i = 0; i < len; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }

      const audioBuffer = await audioContext.decodeAudioData(bytes.buffer);
      const ttsSource = audioContext.createBufferSource();
      ttsSource.buffer = audioBuffer;
      ttsSource.connect(audioContext.destination);

      ttsSource.onended = () => {
        if (originalGainNode && audioContext) {
          originalGainNode.gain.cancelScheduledValues(audioContext.currentTime);
          originalGainNode.gain.setValueAtTime(1.0, audioContext.currentTime);
        }
      };
      ttsSource.start();
    }

    // Relay to content script for subtitle rendering
    if (typeof chrome !== "undefined" && chrome.runtime?.sendMessage) {
      chrome.runtime.sendMessage({
        target: "CONTENT_SCRIPT",
        type: "SERVER_EVENT",
        data: event,
      });
    }
  } catch (err) {
    console.warn("[TOAN_AAS_OFFSCREEN] Error processing downstream event:", err);
  }
}

/**
 * Authoritative Server Stop Request (RT-FIX11).
 * Attempts WebSocket explicit control stop first;
 * if WS is not open or fails to confirm, falls back to authenticated REST POST /sessions/{id}/stop.
 * Returns structured result: { ok: bool, via: "websocket"|"rest", error?: string, status?: number }
 */
async function requestServerStop() {
  // 1. Try active WebSocket if open
  if (webSocket && webSocket.readyState === (typeof WebSocket !== "undefined" ? WebSocket.OPEN : 1)) {
    try {
      const waitPromise = new Promise((resolve) => {
        const timer = setTimeout(() => {
          stopConfirmationResolver = null;
          resolve({ ok: false, error: "WS_STOP_TIMEOUT", via: "websocket" });
        }, 800);
        stopConfirmationResolver = (val) => {
          clearTimeout(timer);
          resolve(val ? { ok: true, via: "websocket" } : { ok: false, error: "WS_STOP_REJECTED", via: "websocket" });
        };
      });

      webSocket.send(JSON.stringify({
        type: "session.control",
        action: "stop",
      }));

      const wsRes = await waitPromise;
      if (wsRes && wsRes.ok) {
        return wsRes;
      }
    } catch (err) {
      console.warn("[TOAN_AAS_OFFSCREEN] Error during WebSocket stop control:", err);
    }
  }

  // 2. Fallback to authenticated REST stop if WebSocket not open or did not confirm in time
  if (currentConfig?.websocketUrl || currentConfig?.apiBase) {
    try {
      let restStopUrl = null;
      if (currentConfig.apiBase && currentConfig.sessionId) {
        restStopUrl = `${currentConfig.apiBase}/api/v1/live-translate/sessions/${currentConfig.sessionId}/stop`;
      } else if (currentConfig.websocketUrl) {
        const wsUrl = new URL(currentConfig.websocketUrl);
        const protocol = wsUrl.protocol === "wss:" ? "https:" : "http:";
        const stopPath = wsUrl.pathname.replace(/\/stream\/?$/, "/stop");
        restStopUrl = `${protocol}//${wsUrl.host}${stopPath}${wsUrl.search}`;
      }

      if (restStopUrl && typeof fetch === "function") {
        const headers = { "Content-Type": "application/json" };
        if (currentConfig.authToken) {
          headers["Authorization"] = `Bearer ${currentConfig.authToken}`;
        }
        const resp = await fetch(restStopUrl, { method: "POST", headers });
        if (resp && (resp.ok || resp.status === 200)) {
          return { ok: true, via: "rest", status: resp.status };
        }
        if (resp && (resp.status === 401 || resp.status === 403)) {
          return { ok: false, error: "REST_STOP_401", status: resp.status, via: "rest" };
        }
        if (resp && resp.status >= 500) {
          return { ok: false, error: "REST_STOP_5XX", status: resp.status, via: "rest" };
        }
        return { ok: false, error: `REST_STOP_HTTP_${resp?.status || "ERR"}`, status: resp?.status, via: "rest" };
      }
    } catch (err) {
      console.warn("[TOAN_AAS_OFFSCREEN] Error during REST stop fallback:", err);
      return { ok: false, error: "REST_STOP_NETWORK_FAILURE", message: err.message, via: "rest" };
    }
  }

  return { ok: false, error: "NO_STOP_AUTHORITY_AVAILABLE" };
}

async function stopCapture(options = {}) {
  isCapturing = false;
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }

  if (options.force) {
    reconnectAttempts = 0;
    isReplaying = false;
    isReconnecting = false;

    if (webSocket) {
      try { webSocket.close(); } catch (e) {}
      webSocket = null;
    }
    if (scriptProcessor) {
      try { scriptProcessor.disconnect(); } catch (e) {}
      scriptProcessor = null;
    }
    if (originalGainNode) {
      try { originalGainNode.disconnect(); } catch (e) {}
      originalGainNode = null;
    }
    if (mediaStream) {
      try { mediaStream.getTracks().forEach((t) => t.stop()); } catch (e) {}
      mediaStream = null;
    }
    if (audioContext && audioContext.state !== "closed") {
      try { audioContext.close(); } catch (e) {}
      audioContext = null;
    }

    return { ok: true, via: "local_forced" };
  }

  // Await authoritative server stop confirmation before local teardown
  const stopRes = await requestServerStop();
  if (!stopRes || !stopRes.ok) {
    console.error("[TOAN_AAS_OFFSCREEN] Authoritative server stop failed. Preserving local credentials/unacked frames for retry.", stopRes);
    // STOP_AUTHORITY_FAILURE_SILENT_SUCCESS=0
    // STOP_FAILURE_PRESERVES_RETRY_AUTHORITY=PASS
    return {
      ok: false,
      error: stopRes?.error || "STOP_SERVER_FAILED",
      status: stopRes?.status,
      details: stopRes,
    };
  }

  reconnectAttempts = 0;
  isReplaying = false;
  isReconnecting = false;

  unackedFrames.clear();
  currentConfig = null;

  if (webSocket) {
    try { webSocket.close(); } catch (e) {}
    webSocket = null;
  }
  if (scriptProcessor) {
    try { scriptProcessor.disconnect(); } catch (e) {}
    scriptProcessor = null;
  }
  if (originalGainNode) {
    try { originalGainNode.disconnect(); } catch (e) {}
    originalGainNode = null;
  }
  if (mediaStream) {
    try { mediaStream.getTracks().forEach((t) => t.stop()); } catch (e) {}
    mediaStream = null;
  }
  if (audioContext && audioContext.state !== "closed") {
    try { audioContext.close(); } catch (e) {}
    audioContext = null;
  }

  return { ok: true, via: stopRes?.via || "local_forced" };
}

// Module export for unit tests
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    unackedFrames,
    MAX_UNACKED_FRAMES,
    MAX_RECONNECT_ATTEMPTS,
    TERMINAL_CLOSE_CODES,
    recordUnackedFrame,
    evictAcknowledgedFrames,
    replayUnackedFrames,
    scheduleReconnect,
    handleDownstreamEvent,
    startCapture,
    stopCapture,
    initWebSocket,
    attachWebSocketHandlers,
    downsampleAndConvertToPcm16,
    setWebSocket: (ws) => { webSocket = ws; },
    getWebSocket: () => webSocket,
    getCurrentSeq: () => currentSeq,
    setCurrentSeq: (seq) => { currentSeq = seq; },
    getLastAckSeq: () => lastAckSeq,
    setLastAckSeq: (seq) => { lastAckSeq = seq; },
    getIsCapturing: () => isCapturing,
    setIsCapturing: (val) => { isCapturing = val; },
    getIsReconnecting: () => isReconnecting,
    setIsReconnecting: (val) => { isReconnecting = val; },
    getReconnectAttempts: () => reconnectAttempts,
    setReconnectAttempts: (n) => { reconnectAttempts = n; },
    getReconnectTimer: () => reconnectTimer,
    requestServerStop,
    setStopConfirmationResolver: (fn) => { stopConfirmationResolver = fn; },
    getStopConfirmationResolver: () => stopConfirmationResolver,
    setCurrentConfig: (cfg) => { currentConfig = cfg; },
    getCurrentConfig: () => currentConfig,
    setAudioContext: (ctx) => { audioContext = ctx; },
    getAudioContext: () => audioContext,
    setOriginalGainNode: (gain) => { originalGainNode = gain; },
    getOriginalGainNode: () => originalGainNode,
    resetTestState: () => {
      unackedFrames.clear();
      currentSeq = 0;
      lastAckSeq = 0;
      reconnectAttempts = 0;
      isCapturing = false;
      isReplaying = false;
      isReconnecting = false;
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
      webSocket = null;
      stopConfirmationResolver = null;
      currentConfig = null;
      audioContext = null;
      originalGainNode = null;
      scriptProcessor = null;
      mediaStream = null;
    },
  };
}
