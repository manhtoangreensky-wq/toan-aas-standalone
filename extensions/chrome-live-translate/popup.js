/**
 * Popup Script for TOAN AAS Live Translate & Dub (Manifest V3 / RT-FIX12).
 * Governed by owner-governed-codex, locked-focus-engineering.
 * Enforces:
 * 1. EXTENSION_CREATE_SESSION: Authenticated session creation before tabCapture.
 * 2. SESSION_ID_SERVER_OWNED and STREAM_TOKEN_SERVER_OWNED.
 * 3. Exact WebSocket URL dispatch.
 * 4. Fails closed with UI_STATE=FAILED if session creation or capture fails.
 * 5. Authoritative Stop verification: never calls updateUiStopped unconditionally on stop failure.
 */

const DEFAULT_API_BASE = "https://tg.toanaas.vn";

function updateUiRunningElements(elements) {
  const { btnToggle, statusMsg, selectMode, selectLang, selectVoice } = elements;
  if (btnToggle) {
    btnToggle.textContent = "■ Dừng dịch trực tiếp";
    btnToggle.className = "btn-primary btn-stop";
    btnToggle.disabled = false;
  }
  if (statusMsg) {
    statusMsg.style.display = "block";
    statusMsg.style.color = "#10b981";
    statusMsg.textContent = "🟢 Đang dịch & lồng tiếng thời gian thực";
  }
  if (selectMode) selectMode.disabled = true;
  if (selectLang) selectLang.disabled = true;
  if (selectVoice) selectVoice.disabled = true;
}

function updateUiStoppedElements(elements) {
  const { btnToggle, statusMsg, selectMode, selectLang, selectVoice } = elements;
  if (btnToggle) {
    btnToggle.textContent = "▶ Bắt đầu dịch tab này";
    btnToggle.className = "btn-primary";
    btnToggle.disabled = false;
  }
  if (statusMsg) {
    statusMsg.style.display = "none";
  }
  if (selectMode) selectMode.disabled = false;
  if (selectLang) selectLang.disabled = false;
  if (selectVoice) selectVoice.disabled = false;
}

function updateUiStopFailedElements(elements, errorMsg) {
  const { btnToggle, statusMsg, selectMode, selectLang, selectVoice } = elements;
  if (btnToggle) {
    btnToggle.textContent = "■ Thử dừng lại";
    btnToggle.className = "btn-primary btn-stop";
    btnToggle.disabled = false;
  }
  if (statusMsg) {
    statusMsg.style.display = "block";
    statusMsg.style.color = "#ef4444";
    statusMsg.textContent = `❌ Dừng thất bại (${errorMsg}). Phiên vẫn đang hoạt động.`;
  }
  if (selectMode) selectMode.disabled = true;
  if (selectLang) selectLang.disabled = true;
  if (selectVoice) selectVoice.disabled = true;
}

function updateUiFailedElements(elements, errorMsg) {
  const { btnToggle, statusMsg, selectMode, selectLang, selectVoice } = elements;
  if (btnToggle) {
    btnToggle.textContent = "Thử lại";
    btnToggle.className = "btn-primary btn-stop";
    btnToggle.disabled = false;
  }
  if (statusMsg) {
    statusMsg.style.display = "block";
    statusMsg.style.color = "#ef4444";
    statusMsg.textContent = `❌ ${errorMsg}`;
  }
  if (selectMode) selectMode.disabled = false;
  if (selectLang) selectLang.disabled = false;
  if (selectVoice) selectVoice.disabled = false;
}

/**
 * Handles STOP_CAPTURE response from background service worker (RT-FIX12).
 * POPUP_STOP_INSPECTS_RESPONSE=PASS
 * POPUP_STOP_FAILURE_RETAINS_ACTIVE_STATE_OR_SHOWS_ERROR=PASS
 */
function handleStopResponse(stopRes, elements) {
  if (elements.btnToggle) {
    elements.btnToggle.disabled = false;
  }
  if (stopRes && stopRes.ok) {
    updateUiStoppedElements(elements);
    return { ok: true, state: "stopped" };
  } else {
    const errMsg = stopRes?.error || "Không thể xác nhận dừng phiên trên máy chủ";
    updateUiStopFailedElements(elements, errMsg);
    return { ok: false, state: "stop_failed", error: errMsg };
  }
}

if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", async () => {
    const selectMode = document.getElementById("select-mode");
    const selectLang = document.getElementById("select-lang");
    const selectVoice = document.getElementById("select-voice");
    const btnToggle = document.getElementById("btn-toggle");
    const statusMsg = document.getElementById("status-msg");

    const elements = { selectMode, selectLang, selectVoice, btnToggle, statusMsg };

    // Check current session state
    if (typeof chrome !== "undefined" && chrome.runtime?.sendMessage) {
      chrome.runtime.sendMessage({ type: "GET_SESSION_STATUS" }, (response) => {
        if (response?.session?.active) {
          updateUiRunningElements(elements);
        }
      });
    }

    if (btnToggle) {
      btnToggle.addEventListener("click", async () => {
        if (typeof chrome === "undefined" || !chrome.runtime?.sendMessage) return;

        chrome.runtime.sendMessage({ type: "GET_SESSION_STATUS" }, async (statusRes) => {
          if (statusRes?.session?.active) {
            // Active -> Stop: Must await authoritative stop confirmation
            btnToggle.disabled = true;
            btnToggle.textContent = "⏳ Đang dừng phiên...";
            statusMsg.style.display = "block";
            statusMsg.style.color = "#f59e0b";
            statusMsg.textContent = "Đang xác nhận kết thúc phiên trên máy chủ...";

            chrome.runtime.sendMessage({ type: "STOP_CAPTURE" }, (stopRes) => {
              handleStopResponse(stopRes, elements);
            });
          } else {
            // Stopped -> Start: Handshake with authenticated backend FIRST
            btnToggle.disabled = true;
            btnToggle.textContent = "⏳ Đang khởi tạo phiên...";
            statusMsg.style.display = "block";
            statusMsg.textContent = "Đang xác thực tài khoản và cấp quyền phiên...";

            try {
              const apiBase = DEFAULT_API_BASE;
              const sessionPayload = {
                mode: selectMode?.value || "LIVE_DUB",
                target_language: selectLang?.value || "vi",
                gender_preference: selectVoice?.value === "female" ? "female" : "male",
                voice_profile_id: selectVoice?.value?.startsWith("vp_") ? selectVoice.value : null,
              };

              const createRes = await fetch(`${apiBase}/api/v1/live-translate/sessions`, {
                method: "POST",
                headers: {
                  "Content-Type": "application/json",
                },
                credentials: "include",
                body: JSON.stringify(sessionPayload),
              });

              if (!createRes.ok) {
                const errJson = await createRes.json().catch(() => ({}));
                throw new Error(errJson.detail || `Lỗi máy chủ (${createRes.status}): Vui lòng đăng nhập Web TOAN AAS`);
              }

              const sessionData = await createRes.json();
              if (!sessionData.ok || !sessionData.session_id || !sessionData.stream_token || !sessionData.websocket_url) {
                throw new Error("Dữ liệu phiên từ máy chủ không hợp lệ (Missing token/URL)");
              }

              // Full WebSocket URL
              let wsUrl = sessionData.websocket_url;
              if (wsUrl.startsWith("/")) {
                const wsProtocol = apiBase.startsWith("https") ? "wss:" : "ws:";
                const host = apiBase.replace(/^https?:\/\//, "");
                wsUrl = `${wsProtocol}//${host}${wsUrl}`;
              }

              // Handshake succeeded: Start capture with server-owned credentials
              chrome.runtime.sendMessage({
                type: "START_CAPTURE",
                sessionData: {
                  sessionId: sessionData.session_id,
                  streamToken: sessionData.stream_token,
                  websocketUrl: wsUrl,
                  mode: sessionData.mode,
                  targetLanguage: sessionData.target_language,
                },
              }, (captureRes) => {
                btnToggle.disabled = false;
                if (captureRes?.ok) {
                  updateUiRunningElements(elements);
                } else {
                  updateUiFailedElements(elements, captureRes?.error || "Không thể bắt luồng âm thanh tab");
                }
              });

            } catch (err) {
              btnToggle.disabled = false;
              updateUiFailedElements(elements, err.message);
            }
          }
        });
      });
    }
  });
}

// Module export for unit tests
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    handleStopResponse,
    updateUiRunningElements,
    updateUiStoppedElements,
    updateUiStopFailedElements,
    updateUiFailedElements,
  };
}
