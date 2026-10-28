/**
 * Executable Extension Unit Test for TOAN AAS Live Translate Offscreen Worker
 * Verifies real code execution in extensions/chrome-live-translate/offscreen.js
 * Governed by owner-governed-codex, locked-focus-engineering (RT-FIX10).
 */

const assert = require("assert");
const path = require("path");

const offscreen = require(path.join(__dirname, "../extensions/chrome-live-translate/offscreen.js"));

function createMockWebSocket() {
  const sentMessages = [];
  const ws = {
    readyState: 1, // OPEN
    binaryType: "arraybuffer",
    send: (data) => {
      sentMessages.push(data);
      try {
        if (typeof data === "string") {
          const parsed = JSON.parse(data);
          if (parsed.type === "session.control" && parsed.action === "stop") {
            // Emulate server immediate stop confirmation via handleDownstreamEvent
            offscreen.handleDownstreamEvent(JSON.stringify({ type: "session.state", state: "ended" }));
          }
        }
      } catch (e) {}
    },
    close: (code, reason) => {
      ws.readyState = 3; // CLOSED
      if (ws.onclose) {
        ws.onclose({ code: code || 1000, reason: reason || "" });
      }
    },
    sentMessages,
  };
  return ws;
}

async function runSuite() {
  console.log("=== RUNNING EXECUTABLE OFFSCREEN RECONNECT TEST SUITE (RT-FIX10) ===");

  // TEST 1: Unacked frame buffer retention (CLIENT_UNACKED_FRAME_BUFFER_ACTUAL_CODE)
  {
    offscreen.resetTestState();
    const frame1 = new Uint8Array([1, 0, 0, 0, 10, 20]);
    const frame2 = new Uint8Array([2, 0, 0, 0, 30, 40]);
    offscreen.recordUnackedFrame(1, frame1);
    offscreen.recordUnackedFrame(2, frame2);

    assert.strictEqual(offscreen.unackedFrames.size, 2);
    assert.deepStrictEqual(offscreen.unackedFrames.get(1), frame1);
    assert.deepStrictEqual(offscreen.unackedFrames.get(2), frame2);
    console.log("PASS: CLIENT_UNACKED_FRAME_BUFFER_ACTUAL_CODE");
  }

  // TEST 2: Lossless unacked buffer - fail-closed on overflow without silent drop
  // (UNACKED_FRAME_SILENT_DROP=0, UNACKED_OVERFLOW_FAIL_CLOSED_OR_BACKPRESSURE=PASS)
  {
    offscreen.resetTestState();
    // Fill buffer completely up to MAX_UNACKED_FRAMES (500 frames)
    for (let i = 1; i <= offscreen.MAX_UNACKED_FRAMES; i++) {
      const frame = new Uint8Array([i & 0xff, (i >> 8) & 0xff, 0, 0]);
      const recorded = offscreen.recordUnackedFrame(i, frame);
      assert.strictEqual(recorded, true, `Frame ${i} must be accepted`);
    }

    assert.strictEqual(offscreen.unackedFrames.size, offscreen.MAX_UNACKED_FRAMES);

    // Attempting to record frame 501 MUST FAIL-CLOSED (return false, NOT drop frame 1!)
    const frameOverflow = new Uint8Array([0x01, 0x02, 0, 0]);
    const accepted = offscreen.recordUnackedFrame(offscreen.MAX_UNACKED_FRAMES + 1, frameOverflow);
    assert.strictEqual(accepted, false, "Overflow frame must be rejected fail-closed");

    // CRITICAL: Oldest frame 1 MUST NOT have been silently dropped!
    assert.strictEqual(offscreen.unackedFrames.has(1), true, "Frame 1 must NOT be silently dropped");
    assert.strictEqual(offscreen.unackedFrames.has(offscreen.MAX_UNACKED_FRAMES), true, "Frame 500 must exist");
    assert.strictEqual(offscreen.unackedFrames.has(offscreen.MAX_UNACKED_FRAMES + 1), false, "Frame 501 must not be inserted");
    assert.strictEqual(offscreen.unackedFrames.size, offscreen.MAX_UNACKED_FRAMES);

    // Verify contiguous sequence range 1..500 without gaps
    let missingCount = 0;
    for (let i = 1; i <= offscreen.MAX_UNACKED_FRAMES; i++) {
      if (!offscreen.unackedFrames.has(i)) {
        missingCount++;
      }
    }
    assert.strictEqual(missingCount, 0, "No sequences should be missing in unacked buffer");

    console.log("PASS: UNACKED_FRAME_SILENT_DROP=0");
    console.log("PASS: UNACKED_OVERFLOW_FAIL_CLOSED_OR_BACKPRESSURE=PASS");
    console.log("PASS: REPLAY_RANGE_CONTIGUOUS=PASS");
    console.log("PASS: MISSING_UNACKED_SEQUENCE_COUNT=0");
  }

  // TEST 3: Cumulative ACK evicts buffer (CUMULATIVE_ACK_EVICTS_BUFFER)
  {
    offscreen.resetTestState();
    for (let i = 101; i <= 115; i++) {
      offscreen.recordUnackedFrame(i, new Uint8Array([i & 0xff, 0, 0, 0]));
    }
    assert.strictEqual(offscreen.unackedFrames.size, 15);

    // Downstream event with cumulative ACK for seq 110
    offscreen.handleDownstreamEvent(JSON.stringify({ type: "ack", seq: 110 }));

    assert.strictEqual(offscreen.getLastAckSeq(), 110);
    // Seqs 101..110 must be evicted
    for (let i = 101; i <= 110; i++) {
      assert.strictEqual(offscreen.unackedFrames.has(i), false, `Seq ${i} should be evicted`);
    }
    // Seqs 111..115 must be retained
    for (let i = 111; i <= 115; i++) {
      assert.strictEqual(offscreen.unackedFrames.has(i), true, `Seq ${i} should be retained`);
    }
    assert.strictEqual(offscreen.unackedFrames.size, 5);
    console.log("PASS: CUMULATIVE_ACK_EVICTS_BUFFER");
  }

  // TEST 4: Reconnect budget resets strictly after server handshake, NOT TCP open
  // (RECONNECT_BUDGET_RESETS_ON_TCP_OPEN=NO, RECONNECT_BUDGET_RESETS_AFTER_HANDSHAKE=YES,
  //  FLAPPING_OPEN_CLOSE_MAX_ATTEMPTS=5, FLAPPING_OPEN_CLOSE_FAILS_CLOSED=PASS)
  {
    offscreen.resetTestState();
    const ws = createMockWebSocket();
    offscreen.attachWebSocketHandlers(ws);
    offscreen.setWebSocket(ws);

    offscreen.setCurrentSeq(115);
    offscreen.setLastAckSeq(110);
    offscreen.setReconnectAttempts(2);

    // Trigger onopen on reconnected socket
    ws.onopen();

    // STRICT CHECK: reconnectAttempts must NOT reset to 0 on TCP onopen!
    assert.strictEqual(offscreen.getReconnectAttempts(), 2, "reconnectAttempts MUST NOT reset on TCP ws.onopen");
    console.log("PASS: RECONNECT_BUDGET_RESETS_ON_TCP_OPEN=NO");

    // Verify session.reconnect frame was sent
    assert.strictEqual(ws.sentMessages.length, 1);
    const sent = JSON.parse(ws.sentMessages[0]);
    assert.strictEqual(sent.type, "session.reconnect");
    assert.strictEqual(sent.last_ack_seq, 110);
    console.log("PASS: CLIENT_SESSION_RECONNECT_SENT");

    // Now server handshake arrives (session.reconnected)
    await offscreen.handleDownstreamEvent(JSON.stringify({
      type: "session.reconnected",
      reconnected: true,
      server_last_ack_seq: 110,
    }));

    // STRICT CHECK: reconnectAttempts resets to 0 ONLY after server handshake!
    assert.strictEqual(offscreen.getReconnectAttempts(), 0, "reconnectAttempts MUST reset after server handshake");
    console.log("PASS: RECONNECT_BUDGET_RESETS_AFTER_HANDSHAKE=YES");

    // Flapping open/close without handshake fails closed after 5 attempts
    offscreen.resetTestState();
    offscreen.setIsCapturing(true);

    for (let flap = 1; flap <= 5; flap++) {
      const flapWs = createMockWebSocket();
      offscreen.attachWebSocketHandlers(flapWs);
      offscreen.setWebSocket(flapWs);
      flapWs.onopen(); // Opens TCP socket, but no server handshake!
      assert.strictEqual(offscreen.getReconnectAttempts(), flap - 1);
      flapWs.onclose({ code: 1006, reason: "Abnormal TCP disconnect before handshake" });
      assert.strictEqual(offscreen.getReconnectAttempts(), flap);
      if (flap < 5) {
        assert.notStrictEqual(offscreen.getReconnectTimer(), null);
        clearTimeout(offscreen.getReconnectTimer());
      }
    }

    assert.strictEqual(offscreen.getReconnectAttempts(), 5);
    console.log("PASS: FLAPPING_OPEN_CLOSE_MAX_ATTEMPTS=5");

    // 6th attempt fails closed
    offscreen.scheduleReconnect();
    assert.strictEqual(offscreen.getIsCapturing(), false);
    assert.strictEqual(offscreen.getReconnectTimer(), null);
    console.log("PASS: FLAPPING_OPEN_CLOSE_FAILS_CLOSED=PASS");
  }

  // TEST 5: Client replay of unacked frames on session.reconnected (CLIENT_REPLAY_ACTUAL_CODE)
  {
    offscreen.resetTestState();
    const ws = createMockWebSocket();
    offscreen.attachWebSocketHandlers(ws);
    offscreen.setWebSocket(ws);

    // Store unacked frames 111..115
    for (let i = 111; i <= 115; i++) {
      offscreen.recordUnackedFrame(i, new Uint8Array([i & 0xff, 0, 0, 0, 0xaa, 0xbb]));
    }
    offscreen.setLastAckSeq(110);

    // Server acknowledges reconnection with server_last_ack_seq = 112
    await offscreen.handleDownstreamEvent(JSON.stringify({
      type: "session.reconnected",
      reconnected: true,
      server_last_ack_seq: 112,
    }));

    // Server acknowledged up to 112 cumulatively:
    assert.strictEqual(offscreen.getLastAckSeq(), 112);
    assert.strictEqual(offscreen.unackedFrames.has(111), false);
    assert.strictEqual(offscreen.unackedFrames.has(112), false);
    assert.strictEqual(offscreen.unackedFrames.has(113), true);
    assert.strictEqual(offscreen.unackedFrames.has(114), true);
    assert.strictEqual(offscreen.unackedFrames.has(115), true);

    // Replay should have sent frames 113, 114, 115 across the WebSocket!
    assert.strictEqual(ws.sentMessages.length, 3);
    const replayedSeqs = ws.sentMessages.map((buf) => new DataView(buf).getUint32(0, true));
    assert.deepStrictEqual(replayedSeqs, [113, 114, 115]);
    console.log("PASS: CLIENT_REPLAY_ACTUAL_CODE");
  }

  // TEST 6: Terminal closure codes fail-closed without retry (AUTH_TERMINAL_CLOSE_NO_RETRY)
  {
    for (const code of [4401, 4403, 4404, 4001, 4003, 4004, 1008]) {
      offscreen.resetTestState();
      offscreen.setIsCapturing(true);
      const ws = createMockWebSocket();
      offscreen.attachWebSocketHandlers(ws);
      offscreen.setWebSocket(ws);

      ws.onclose({ code, reason: `Terminal close ${code}` });

      assert.strictEqual(offscreen.getReconnectTimer(), null, `Terminal code ${code} must NOT schedule reconnect`);
      assert.strictEqual(offscreen.getReconnectAttempts(), 0);
    }
    console.log("PASS: AUTH_TERMINAL_CLOSE_ACTUAL_CODE");
  }

  // TEST 7: Bounded reconnect retry (RECONNECT_BOUND_ACTUAL_CODE)
  {
    offscreen.resetTestState();
    offscreen.setIsCapturing(true);
    const ws = createMockWebSocket();
    offscreen.attachWebSocketHandlers(ws);
    offscreen.setWebSocket(ws);

    // Non-terminal close triggers reconnect
    ws.onclose({ code: 1006, reason: "Abnormal closure" });
    assert.strictEqual(offscreen.getReconnectAttempts(), 1);
    assert.notStrictEqual(offscreen.getReconnectTimer(), null);

    // Set attempts to MAX (5)
    offscreen.setReconnectAttempts(offscreen.MAX_RECONNECT_ATTEMPTS);
    if (offscreen.getReconnectTimer()) {
      clearTimeout(offscreen.getReconnectTimer());
    }

    // Attempting another reconnect when max attempts reached should abort, notify failure, and stop capture
    offscreen.scheduleReconnect();
    assert.strictEqual(offscreen.getIsCapturing(), false, "isCapturing should be false after attempts exhausted");
    assert.strictEqual(offscreen.getReconnectTimer(), null, "reconnectTimer should be cleared");
    console.log("PASS: RECONNECT_BOUND_ACTUAL_CODE");
  }

  // TEST 8: Explicit Stop confirmation and Fallback
  // (EXTENSION_USER_STOP_SENDS_SERVER_STOP=PASS, LOCAL_TEARDOWN_AFTER_SERVER_STOP_CONFIRMATION=PASS, STOP_WHEN_WS_NOT_OPEN_FAILS_CLOSED=PASS)
  {
    // Case 8a: WebSocket OPEN -> sends session.control stop, awaits server confirmation, then tears down
    offscreen.resetTestState();
    offscreen.setIsCapturing(true);
    const ws = createMockWebSocket();
    offscreen.attachWebSocketHandlers(ws);
    offscreen.setWebSocket(ws);
    offscreen.setCurrentConfig({ websocketUrl: "ws://localhost:8000/api/v1/live-translate/sessions/s1/stream?token=tok1" });

    await offscreen.stopCapture();

    assert.strictEqual(offscreen.getIsCapturing(), false);
    assert.strictEqual(offscreen.getReconnectTimer(), null);
    assert.strictEqual(ws.sentMessages.length, 1);
    const stopMsg = JSON.parse(ws.sentMessages[0]);
    assert.strictEqual(stopMsg.type, "session.control");
    assert.strictEqual(stopMsg.action, "stop");
    assert.strictEqual(ws.readyState, 3); // CLOSED
    assert.strictEqual(offscreen.getWebSocket(), null);
    assert.strictEqual(offscreen.getCurrentConfig(), null);
    console.log("PASS: EXTENSION_USER_STOP_SENDS_SERVER_STOP");
    console.log("PASS: LOCAL_TEARDOWN_AFTER_SERVER_STOP_CONFIRMATION");

    // Case 8b: WebSocket NOT OPEN (closed or null) -> fallback to REST stop POST /api/v1/live-translate/sessions/{session_id}/stop
    offscreen.resetTestState();
    offscreen.setIsCapturing(true);
    offscreen.setCurrentConfig({ websocketUrl: "ws://localhost:8000/api/v1/live-translate/sessions/s_rest/stream?token=tok_rest" });

    let restFetchUrl = null;
    let restFetchMethod = null;
    global.fetch = async (url, opts) => {
      restFetchUrl = url;
      restFetchMethod = opts?.method;
      return { ok: true, status: 200, json: async () => ({ ok: true, state: "ended" }) };
    };

    // WebSocket is null (not open)
    assert.strictEqual(offscreen.getWebSocket(), null);
    await offscreen.stopCapture();

    assert.strictEqual(offscreen.getIsCapturing(), false);
    assert.strictEqual(restFetchUrl, "http://localhost:8000/api/v1/live-translate/sessions/s_rest/stop?token=tok_rest");
    assert.strictEqual(restFetchMethod, "POST");
    console.log("PASS: STOP_WHEN_WS_NOT_OPEN_FAILS_CLOSED");
  }

  // TEST 9: Canonical Bot TTS event audio_b64 playback with ducking and restore (EXTENSION_CANONICAL_TTS_PLAYBACK)
  {
    offscreen.resetTestState();
    let decodeAudioDataCalled = false;
    let playbackStarted = false;
    let duckingGain = null;
    let restoredGain = null;

    const mockGainNode = {
      gain: {
        setValueAtTime: (val, time) => {
          if (val < 1.0) duckingGain = val;
          else restoredGain = val;
        },
        cancelScheduledValues: (time) => {},
      },
      disconnect: () => {},
    };

    let onEndedCallback = null;
    const mockAudioBuffer = { duration: 1.5 };
    const mockAudioContext = {
      currentTime: 10.0,
      destination: {},
      decodeAudioData: async (buffer) => {
        decodeAudioDataCalled = true;
        return mockAudioBuffer;
      },
      createBufferSource: () => {
        const src = {
          buffer: null,
          connect: (dest) => {},
          start: () => {
            playbackStarted = true;
          },
          set onended(fn) {
            onEndedCallback = fn;
          },
          get onended() {
            return onEndedCallback;
          },
        };
        return src;
      },
      close: () => {},
    };

    offscreen.setOriginalGainNode(mockGainNode);
    offscreen.setAudioContext(mockAudioContext);

    // Canonical Bot event: {"type":"tts.audio","audio_b64":"..."}
    const dummyAudioB64 = Buffer.from("WAV_OR_PCM_DATA").toString("base64");
    const canonicalBotEvent = {
      type: "tts.audio",
      audio_b64: dummyAudioB64,
    };

    await offscreen.handleDownstreamEvent(JSON.stringify(canonicalBotEvent));

    assert.strictEqual(decodeAudioDataCalled, true, "TTS audio decode must be called");
    console.log("PASS: TTS_AUDIO_DECODE_CALLED");

    assert.strictEqual(playbackStarted, true, "TTS playback must be started");
    console.log("PASS: TTS_AUDIO_PLAYBACK_STARTED");

    assert.strictEqual(duckingGain, 0.25, "Audio ducking must reduce gain to 0.25 during TTS");
    console.log("PASS: AUDIO_DUCKING_ACTIVE");

    assert.strictEqual(typeof onEndedCallback, "function", "onended callback must be set on audio source");
    onEndedCallback();
    assert.strictEqual(restoredGain, 1.0, "Audio ducking must restore gain to 1.0 when TTS ends");
    console.log("PASS: AUDIO_DUCKING_RESTORE");

    console.log("PASS: CANONICAL_BOT_TTS_FIELD=audio_b64");
    console.log("PASS: EXTENSION_CANONICAL_TTS_PLAYBACK");
  }

  // TEST 10: Backward-compatible audio_base64 playback
  {
    offscreen.resetTestState();
    let decodeCalled = false;
    const mockGainNode = {
      gain: { setValueAtTime: () => {}, cancelScheduledValues: () => {} },
      disconnect: () => {},
    };
    const mockAudioContext = {
      currentTime: 1.0,
      destination: {},
      decodeAudioData: async () => { decodeCalled = true; return {}; },
      createBufferSource: () => ({ buffer: null, connect: () => {}, start: () => {}, set onended(fn) {} }),
      close: () => {},
    };
    offscreen.setOriginalGainNode(mockGainNode);
    offscreen.setAudioContext(mockAudioContext);

    await offscreen.handleDownstreamEvent(JSON.stringify({
      type: "tts.audio",
      audio_base64: Buffer.from("LEGACY_DATA").toString("base64"),
    }));
    assert.strictEqual(decodeCalled, true);
    console.log("PASS: BACKWARD_COMPATIBLE_AUDIO_BASE64_PLAYBACK");
  }

  offscreen.resetTestState();
  console.log("=== ALL EXECUTABLE OFFSCREEN RECONNECT TESTS PASSED (EXECUTABLE_OFFSCREEN_RECONNECT_TEST=PASS) ===");
}

runSuite().catch((err) => {
  console.error("TEST FAILED:", err);
  process.exit(1);
});
