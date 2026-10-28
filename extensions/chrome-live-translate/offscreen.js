/**
 * Offscreen Document Worker for TOAN AAS Live Translate & Dub (Manifest V3 / RT-FIX7).
 * Handles tab audio capture, 16kHz PCM downsampling, binary sequence streaming,
 * WebSocket lifecycle with unacked frame buffer and session reconnect/replay,
 * and audio ducking with TTS playback.
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

const MAX_RECONNECT_ATTEMPTS = 5;
const INITIAL_RECONNECT_DELAY_MS = 500;
const MAX_UNACKED_FRAMES = 500;

// Bounded map of sequence -> Uint8Array binary frame [uint32 sequence LE][PCM 16-bit bytes]
const unackedFrames = new Map();

// Terminal closure codes that must fail-closed immediately without reconnect (AUTH_TERMINAL_CLOSE_NO_RETRY)
const TERMINAL_CLOSE_CODES = new Set([4401, 4403, 4404, 4001, 4003, 4004, 1008]);

if (typeof chrome !== "undefined" && chrome.runtime?.onMessage) {
  chrome.runtime.onMessage.addListener((message) => {
    if (message.type === "INIT_AUDIO_CAPTURE") {
      startCapture(message.streamId, message.config).catch((err) => {
        console.error("[TOAN_AAS_OFFSCREEN] Capture initialization failed:", err);
        notifyFailure(err.message);
      });
    } else if (message.type === "STOP_AUDIO_CAPTURE") {
      stopCapture();
    }
  });
}

function notifyFailure(errorMessage) {
  stopCapture();
  if (typeof chrome !== "undefined" && chrome.runtime?.sendMessage) {
    chrome.runtime.sendMessage({
      type: "OFFSCREEN_ERROR",
      error: errorMessage,
    });
  }
}

async function startCapture(streamId, config) {
  stopCapture();
  currentSeq = 0;
  lastAckSeq = 0;
  reconnectAttempts = 0;
  isReplaying = false;
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

        // Retain frame in unacked buffer (lossless: fail-closed if overflow)
        if (!recordUnackedFrame(currentSeq, frame)) {
          return;
        }

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

  reconnectAttempts += 1;
  const delay = INITIAL_RECONNECT_DELAY_MS * Math.pow(2, reconnectAttempts - 1);
  console.log(`[TOAN_AAS_OFFSCREEN] Scheduling reconnect attempt #${reconnectAttempts} in ${delay}ms...`);

  if (reconnectTimer) clearTimeout(reconnectTimer);
  reconnectTimer = setTimeout(() => {
    if (isCapturing) {
      initWebSocket();
    }
  }, delay);
}

function evictAcknowledgedFrames(upToSeq) {
  // CUMULATIVE_ACK_EVICTS_BUFFER: Evict all frames up to and including upToSeq
  for (const seq of Array.from(unackedFrames.keys())) {
    if (seq <= upToSeq) {
      unackedFrames.delete(seq);
    }
  }
}

function replayUnackedFrames() {
  // CLIENT_REPLAY_FROM_LAST_ACK_PLUS_ONE: Replay only unacknowledged frames in sequence order
  if (!webSocket || webSocket.readyState !== (typeof WebSocket !== "undefined" ? WebSocket.OPEN : 1)) return;
  isReplaying = true;
  try {
    const sortedSeqs = Array.from(unackedFrames.keys()).sort((a, b) => a - b);
    for (const seq of sortedSeqs) {
      if (seq > lastAckSeq) {
        const frame = unackedFrames.get(seq);
        if (frame && webSocket.readyState === (typeof WebSocket !== "undefined" ? WebSocket.OPEN : 1)) {
          webSocket.send(frame.buffer);
        }
      }
    }
  } finally {
    isReplaying = false;
  }
}

function downsampleAndConvertToPcm16(inputBuffer, inputSampleRate, targetSampleRate) {
  if (inputSampleRate === targetSampleRate) {
    const pcm = new Int16Array(inputBuffer.length);
    for (let i = 0; i < inputBuffer.length; i++) {
      let s = Math.max(-1, Math.min(1, inputBuffer[i]));
      pcm[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return pcm;
  }

  const sampleRatio = inputSampleRate / targetSampleRate;
  const newLength = Math.round(inputBuffer.length / sampleRatio);
  const pcm16 = new Int16Array(newLength);

  for (let i = 0; i < newLength; i++) {
    const originalIndex = Math.min(Math.round(i * sampleRatio), inputBuffer.length - 1);
    let s = Math.max(-1, Math.min(1, inputBuffer[originalIndex]));
    pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
  }

  return pcm16;
}

let stopConfirmationResolver = null;

async function handleDownstreamEvent(rawData) {
  if (typeof rawData !== "string") return;

  try {
    const event = JSON.parse(rawData);

    // Reset reconnect budget strictly after authoritative server handshake (session.ready or session.reconnected)
    if (event.type === "session.ready" || event.type === "session.reconnected") {
      reconnectAttempts = 0;
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

async function requestServerStop() {
  // 1. Try active WebSocket if open
  if (webSocket && webSocket.readyState === (typeof WebSocket !== "undefined" ? WebSocket.OPEN : 1)) {
    try {
      const waitPromise = new Promise((resolve) => {
        const timer = setTimeout(() => {
          stopConfirmationResolver = null;
          resolve(false);
        }, 800);
        stopConfirmationResolver = (val) => {
          clearTimeout(timer);
          resolve(val);
        };
      });

      webSocket.send(JSON.stringify({
        type: "session.control",
        action: "stop",
      }));

      const confirmed = await waitPromise;
      if (confirmed) {
        return true;
      }
    } catch (err) {
      console.warn("[TOAN_AAS_OFFSCREEN] Error during WebSocket stop control:", err);
    }
  }

  // 2. Fallback to REST stop if WebSocket not open or did not confirm in time
  if (currentConfig?.websocketUrl) {
    try {
      const wsUrl = new URL(currentConfig.websocketUrl);
      const protocol = wsUrl.protocol === "wss:" ? "https:" : "http:";
      const stopPath = wsUrl.pathname.replace(/\/stream\/?$/, "/stop");
      const restStopUrl = `${protocol}//${wsUrl.host}${stopPath}${wsUrl.search}`;

      if (typeof fetch === "function") {
        const resp = await fetch(restStopUrl, { method: "POST" });
        if (resp && (resp.ok || resp.status === 200)) {
          return true;
        }
      }
    } catch (err) {
      console.warn("[TOAN_AAS_OFFSCREEN] Error during REST stop fallback:", err);
    }
  }

  return false;
}

async function stopCapture() {
  isCapturing = false;
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  reconnectAttempts = 0;
  isReplaying = false;

  // Await server stop confirmation before local teardown
  await requestServerStop();

  unackedFrames.clear();
  currentConfig = null;

  if (webSocket) {
    webSocket.close();
    webSocket = null;
  }
  if (scriptProcessor) {
    scriptProcessor.disconnect();
    scriptProcessor = null;
  }
  if (originalGainNode) {
    originalGainNode.disconnect();
    originalGainNode = null;
  }
  if (mediaStream) {
    mediaStream.getTracks().forEach((t) => t.stop());
    mediaStream = null;
  }
  if (audioContext && audioContext.state !== "closed") {
    audioContext.close();
    audioContext = null;
  }
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
