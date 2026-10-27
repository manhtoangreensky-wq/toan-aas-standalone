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

        // Retain frame in unacked buffer (bounded)
        if (unackedFrames.size >= MAX_UNACKED_FRAMES) {
          const oldestSeq = unackedFrames.keys().next().value;
          unackedFrames.delete(oldestSeq);
        }
        unackedFrames.set(currentSeq, frame);

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

function initWebSocket() {
  if (!isCapturing || !currentConfig?.websocketUrl) return;

  try {
    webSocket = new WebSocket(currentConfig.websocketUrl);
  } catch (e) {
    console.error("[TOAN_AAS_OFFSCREEN] Failed to initialize WebSocket:", e);
    scheduleReconnect();
    return;
  }

  webSocket.binaryType = "arraybuffer";

  webSocket.onopen = () => {
    console.log("[TOAN_AAS_OFFSCREEN] WebSocket connected.");
    reconnectAttempts = 0;

    // CLIENT_SESSION_RECONNECT_SENT: If reconnecting existing session with prior sequence progress
    if (currentSeq > 0 || lastAckSeq > 0) {
      console.log(`[TOAN_AAS_OFFSCREEN] Sending session.reconnect with lastAckSeq=${lastAckSeq}`);
      const reconMsg = JSON.stringify({
        type: "session.reconnect",
        last_ack_seq: lastAckSeq,
      });
      webSocket.send(reconMsg);
    }
  };

  webSocket.onerror = (err) => {
    console.error("[TOAN_AAS_OFFSCREEN] WebSocket error:", err);
  };

  webSocket.onclose = (event) => {
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

  webSocket.onmessage = (event) => {
    handleDownstreamEvent(event.data);
  };
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

async function handleDownstreamEvent(rawData) {
  if (typeof rawData !== "string") return;

  try {
    const event = JSON.parse(rawData);

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

    // 3. Audio Ducking & TTS playback
    if (event.type === "tts.audio" && event.audio_base64 && originalGainNode && audioContext) {
      originalGainNode.gain.cancelScheduledValues(audioContext.currentTime);
      originalGainNode.gain.setValueAtTime(0.25, audioContext.currentTime);

      const binaryString = atob(event.audio_base64);
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

function stopCapture() {
  isCapturing = false;
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  reconnectAttempts = 0;
  isReplaying = false;
  unackedFrames.clear();
  currentConfig = null;

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
  if (webSocket) {
    webSocket.close();
    webSocket = null;
  }
}

// Module export for unit tests
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    unackedFrames,
    MAX_UNACKED_FRAMES,
    MAX_RECONNECT_ATTEMPTS,
    TERMINAL_CLOSE_CODES,
    evictAcknowledgedFrames,
    replayUnackedFrames,
    scheduleReconnect,
    handleDownstreamEvent,
    startCapture,
    stopCapture,
    initWebSocket,
    downsampleAndConvertToPcm16,
  };
}
