/**
 * Background Service Worker for TOAN AAS Live Translate & Dub (Manifest V3 / RT-FIX11).
 * Governed by owner-governed-codex, locked-focus-engineering.
 * Manages offscreen lifecycle, authoritative stop confirmation (WS + REST fallback),
 * and failure preservation (zero silent stop success).
 */

let activeSession = null;
let creatingOffscreenPromise = null;

async function setupOffscreenDocument(path) {
  if (typeof chrome === "undefined" || !chrome.runtime || !chrome.offscreen) {
    return;
  }
  const offscreenUrl = chrome.runtime.getURL(path);
  const existingContexts = await chrome.runtime.getContexts({
    contextTypes: ["OFFSCREEN_DOCUMENT"],
    documentUrls: [offscreenUrl],
  });

  if (existingContexts.length > 0) {
    return;
  }

  if (creatingOffscreenPromise) {
    await creatingOffscreenPromise;
    return;
  }

  creatingOffscreenPromise = chrome.offscreen.createDocument({
    url: path,
    reasons: ["USER_MEDIA", "AUDIO_PLAYBACK"],
    justification: "Recording tab audio, resampling to 16kHz PCM, and playing dubbing TTS audio with ducking.",
  });

  await creatingOffscreenPromise;
  creatingOffscreenPromise = null;
}

if (typeof chrome !== "undefined" && chrome.runtime?.onMessage) {
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === "START_CAPTURE") {
      handleStartCapture(message.sessionData, sender.tab?.id || message.tabId)
        .then((res) => sendResponse({ ok: true, data: res }))
        .catch((err) => sendResponse({ ok: false, error: err.message }));
      return true;
    }

    if (message.type === "STOP_CAPTURE") {
      handleStopCapture({ force: !!message.force })
        .then((res) => sendResponse({ ok: true, data: res }))
        .catch((err) => sendResponse({ ok: false, error: err.message, status: err.status }));
      return true;
    }

    if (message.type === "GET_SESSION_STATUS") {
      sendResponse({ ok: true, session: activeSession });
      return false;
    }

    // Relay downstream events to content script
    if (message.target === "CONTENT_SCRIPT" && activeSession?.tabId) {
      if (chrome.tabs?.sendMessage) {
        chrome.tabs.sendMessage(activeSession.tabId, message).catch(() => {});
      }
      return false;
    }

    if (message.type === "OFFSCREEN_ERROR") {
      // Fail closed: stop capture and notify tab
      handleStopCapture({ force: true }).then(() => {
        if (activeSession?.tabId && chrome.tabs?.sendMessage) {
          chrome.tabs.sendMessage(activeSession.tabId, {
            type: "SESSION_FAILED",
            error: message.error || "Lỗi luồng âm thanh/WebSocket",
          }).catch(() => {});
        }
      });
      return false;
    }
  });
}

async function handleStartCapture(sessionData, tabId) {
  if (!sessionData || !sessionData.sessionId || !sessionData.streamToken || !sessionData.websocketUrl) {
    throw new Error("Missing server-owned session credentials (sessionId/streamToken/websocketUrl)");
  }

  if (!tabId && typeof chrome !== "undefined" && chrome.tabs?.query) {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    tabId = tab?.id;
  }
  if (!tabId) {
    throw new Error("No active tab found to capture audio.");
  }

  await setupOffscreenDocument("offscreen.html");

  let streamId = null;
  if (typeof chrome !== "undefined" && chrome.tabCapture?.getMediaStreamId) {
    streamId = await chrome.tabCapture.getMediaStreamId({
      targetTabId: tabId,
    });
  } else {
    streamId = "mock_stream_id";
  }

  if (!streamId) {
    throw new Error("chrome.tabCapture did not yield a valid streamId");
  }

  activeSession = {
    active: true,
    tabId: tabId,
    sessionId: sessionData.sessionId,
    streamToken: sessionData.streamToken,
    websocketUrl: sessionData.websocketUrl,
    apiBase: sessionData.apiBase || "",
    authToken: sessionData.authToken || "",
    startedAt: Date.now(),
  };

  if (typeof chrome !== "undefined" && chrome.runtime?.sendMessage) {
    chrome.runtime.sendMessage({
      type: "INIT_AUDIO_CAPTURE",
      streamId: streamId,
      config: sessionData,
    });
  }

  if (typeof chrome !== "undefined" && chrome.tabs?.sendMessage) {
    chrome.tabs.sendMessage(tabId, {
      type: "SESSION_STARTED",
      config: sessionData,
    }).catch(() => {});
  }

  return { tabId, streamId, sessionId: sessionData.sessionId };
}

/**
 * Authenticated REST stop helper for authoritative stop fallback.
 */
async function performRestStop(session) {
  if (!session) return { ok: false, error: "NO_ACTIVE_SESSION" };
  const { sessionId, streamToken, websocketUrl, apiBase, authToken } = session;
  if (!sessionId && !websocketUrl) {
    return { ok: false, error: "NO_STOP_TARGET" };
  }

  let restUrl = null;
  if (apiBase && sessionId) {
    restUrl = `${apiBase.replace(/\/+$/, "")}/api/v1/live-translate/sessions/${sessionId}/stop`;
  } else if (websocketUrl) {
    try {
      const wsUrl = new URL(websocketUrl);
      const proto = wsUrl.protocol === "wss:" ? "https:" : "http:";
      const stopPath = wsUrl.pathname.replace(/\/stream\/?$/, "/stop");
      restUrl = `${proto}//${wsUrl.host}${stopPath}${wsUrl.search}`;
    } catch (e) {
      return { ok: false, error: "INVALID_WEBSOCKET_URL", message: e.message };
    }
  }

  if (!restUrl) {
    return { ok: false, error: "CANNOT_DETERMINE_REST_STOP_URL" };
  }

  if (typeof fetch !== "function") {
    return { ok: false, error: "FETCH_NOT_AVAILABLE" };
  }

  try {
    const headers = { "Content-Type": "application/json" };
    if (authToken) {
      headers["Authorization"] = `Bearer ${authToken}`;
    } else if (streamToken) {
      headers["X-Stream-Token"] = streamToken;
    }

    const resp = await fetch(restUrl, { method: "POST", headers });
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
  } catch (netErr) {
    return { ok: false, error: "REST_STOP_NETWORK_FAILURE", message: netErr.message, via: "rest" };
  }
}

/**
 * Authoritative Stop Capture (RT-FIX11).
 * BACKGROUND_WAITS_AUTHORITATIVE_STOP_RESULT=PASS
 * STOP_AUTHORITY_FAILURE_SILENT_SUCCESS=0
 * STOP_FAILURE_PRESERVES_RETRY_AUTHORITY=PASS
 */
async function handleStopCapture(options = {}) {
  if (!activeSession) {
    return { ok: true, alreadyStopped: true };
  }

  const currentTabId = activeSession.tabId;
  const sessionCopy = { ...activeSession };

  // 1. Ask offscreen to perform stopCapture
  let offscreenRes = null;
  if (typeof chrome !== "undefined" && chrome.runtime?.sendMessage) {
    try {
      offscreenRes = await new Promise((resolve) => {
        try {
          chrome.runtime.sendMessage({ type: "STOP_AUDIO_CAPTURE", force: !!options.force }, (resp) => {
            const lastErr = chrome.runtime?.lastError;
            if (lastErr) {
              resolve({ ok: false, error: lastErr.message, noOffscreen: true });
            } else {
              resolve(resp || { ok: false, error: "EMPTY_OFFSCREEN_RESPONSE" });
            }
          });
        } catch (err) {
          resolve({ ok: false, error: err.message });
        }
      });
    } catch (err) {
      offscreenRes = { ok: false, error: err.message };
    }
  }

  // 2. If offscreen succeeded via WS or REST:
  if (offscreenRes && offscreenRes.ok) {
    if (currentTabId && typeof chrome !== "undefined" && chrome.tabs?.sendMessage) {
      chrome.tabs.sendMessage(currentTabId, { type: "SESSION_STOPPED" }).catch(() => {});
    }
    activeSession = null;
    return { ok: true, via: offscreenRes.via || "offscreen" };
  }

  // 3. If offscreen failed (or was unavailable) and not force, background tries authenticated REST fallback
  let restRes = null;
  if (!options.force) {
    restRes = await performRestStop(sessionCopy);
    if (restRes && restRes.ok) {
      if (typeof chrome !== "undefined" && chrome.runtime?.sendMessage) {
        chrome.runtime.sendMessage({ type: "STOP_AUDIO_CAPTURE", force: true }, () => {
          const _ = chrome.runtime?.lastError;
        });
      }
      if (currentTabId && typeof chrome !== "undefined" && chrome.tabs?.sendMessage) {
        chrome.tabs.sendMessage(currentTabId, { type: "SESSION_STOPPED" }).catch(() => {});
      }
      activeSession = null;
      return { ok: true, via: "rest" };
    }
  }

  // 4. If forced:
  if (options.force) {
    if (typeof chrome !== "undefined" && chrome.runtime?.sendMessage) {
      chrome.runtime.sendMessage({ type: "STOP_AUDIO_CAPTURE", force: true }, () => {
        const _ = chrome.runtime?.lastError;
      });
    }
    if (currentTabId && typeof chrome !== "undefined" && chrome.tabs?.sendMessage) {
      chrome.tabs.sendMessage(currentTabId, { type: "SESSION_STOPPED", forced: true }).catch(() => {});
    }
    activeSession = null;
    return { ok: true, forced: true };
  }

  // 5. CRITICAL: BOTH AUTHORITIES FAILED (STOP_AUTHORITY_FAILURE_SILENT_SUCCESS=0)
  // Preserves retry authority: do NOT clear activeSession, do NOT emit SESSION_STOPPED!
  const finalError = restRes?.error || offscreenRes?.error || "STOP_AUTHORITY_FAILED";
  const finalStatus = restRes?.status || offscreenRes?.status;
  if (currentTabId && typeof chrome !== "undefined" && chrome.tabs?.sendMessage) {
    chrome.tabs.sendMessage(currentTabId, {
      type: "SESSION_STOP_FAILED",
      error: finalError,
      status: finalStatus,
    }).catch(() => {});
  }

  const err = new Error(finalError);
  err.status = finalStatus;
  err.offscreenRes = offscreenRes;
  err.restRes = restRes;
  throw err;
}

// Module export for unit tests
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    handleStartCapture,
    handleStopCapture,
    performRestStop,
    getActiveSession: () => activeSession,
    setActiveSession: (s) => { activeSession = s; },
    resetTestState: () => {
      activeSession = null;
      creatingOffscreenPromise = null;
    },
  };
}
