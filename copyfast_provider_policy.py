"""Pure policy and read-model synthesis engine for Web Providers (WEB08).

Canonical Authorities:
- PROVIDER_AUTHORITY = "BOT_CORE"
- PROVIDER_RUNTIME_SOURCE = "UBUNTU_VPS_BOT"
- PROVIDER_CAPABILITY_SOURCE = "BOT_CORE_PROVIDER_REGISTRY"
- PROVIDER_CONFIG_SOURCE = "BOT_CORE_ENVIRONMENT_CONFIG"
- PROVIDER_ROUTE_SOURCE = "BOT_CORE_PROVIDER_ROUTER"
- PROVIDER_STORE = "BOT_CORE_SQLITE_AND_MEMORY"
- WEB_ROLE = "READ_MODEL_REDACTED_PROJECTION"

Safety Invariants:
- REAL_PROVIDER_NETWORK_CALLS = 0
- PAID_PROVIDER_CALLS = 0
- SECRET_MUTATIONS = 0
- ENV_MUTATIONS = 0
- RAW_SECRET_EXPOSURE = 0
- RAW_TOKEN_EXPOSURE = 0
- CUSTOMER_PROVIDER_ADMIN_ACCESS = 0
- FAKE_PROVIDER_ROW = 0
- UNKNOWN_PROVIDER_AS_HEALTHY = 0
- STATE_CONFLATION = 0
- CAPABILITY_FAKE_READY = 0
- ROUTING_READY_FAKE = 0
- DEAD_PROVIDER_CTA = 0
- FAKE_PROVIDER_ACTION_SUCCESS = 0
- BACKEND_FAILURE_FAKE_EMPTY = 0
- STALE_HEALTH_AS_CURRENT = 0
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ==============================================================================
# 1. CANONICAL AUTHORITIES
# ==============================================================================
PROVIDER_AUTHORITY = "BOT_CORE"
PROVIDER_RUNTIME_SOURCE = "UBUNTU_VPS_BOT"
PROVIDER_CAPABILITY_SOURCE = "BOT_CORE_PROVIDER_REGISTRY"
PROVIDER_CONFIG_SOURCE = "BOT_CORE_ENVIRONMENT_CONFIG"
PROVIDER_ROUTE_SOURCE = "BOT_CORE_PROVIDER_ROUTER"
PROVIDER_STORE = "BOT_CORE_SQLITE_AND_MEMORY"
WEB_ROLE = "READ_MODEL_REDACTED_PROJECTION"

# Hard safety invariants
REAL_PROVIDER_NETWORK_CALLS = 0
PAID_PROVIDER_CALLS = 0
SECRET_MUTATIONS = 0
ENV_MUTATIONS = 0
RAW_SECRET_EXPOSURE = 0
RAW_TOKEN_EXPOSURE = 0
CUSTOMER_PROVIDER_ADMIN_ACCESS = 0
FAKE_PROVIDER_ROW = 0
UNKNOWN_PROVIDER_AS_HEALTHY = 0
STATE_CONFLATION = 0
CAPABILITY_FAKE_READY = 0
ROUTING_READY_FAKE = 0
DEAD_PROVIDER_CTA = 0
FAKE_PROVIDER_ACTION_SUCCESS = 0
BACKEND_FAILURE_FAKE_EMPTY = 0
STALE_HEALTH_AS_CURRENT = 0

# Semantic state boundaries: CONFIGURED != AVAILABLE != HEALTHY != ELIGIBLE != SELECTED
CONFIGURED_NOT_EQUAL_AVAILABLE = True
CONFIGURED_NOT_EQUAL_HEALTHY = True
AVAILABLE_NOT_EQUAL_HEALTHY = True
HEALTHY_NOT_EQUAL_ELIGIBLE = True
ELIGIBLE_NOT_EQUAL_SELECTED = True

# Freshness policy (observations older than this are considered stale)
# Authority: DOWNGRADE_ONLY (stale => block; fresh => does NOT independently authorize routing)
WEB_HEALTH_FRESHNESS_POLICY_SECONDS = 3600
WEB_HEALTH_FRESHNESS_POLICY_MODE = "DOWNGRADE_ONLY"
PROVIDER_OBSERVATION_FRESHNESS_SECONDS = WEB_HEALTH_FRESHNESS_POLICY_SECONDS

CANONICAL_HEALTH_FRESHNESS_SOURCE = "WEBAPP_EXPLICIT_PROVIDER_POLICY"
CANONICAL_HEALTH_FRESHNESS_SECONDS = WEB_HEALTH_FRESHNESS_POLICY_SECONDS

# Valid taxonomy
VALID_PROVIDER_KINDS = frozenset({
    "commercial_api",
    "cloud_llm",
    "self_hosted_worker",
    "media_tool",
    "auth_oauth",
    "payment_gateway",
})

VALID_HEALTH_STATES = frozenset({
    "HEALTHY",
    "DEGRADED",
    "UNAVAILABLE",
    "UNKNOWN",
    "UNKNOWN_CURRENT_HEALTH",
    "STALE_HEALTHY",
})

VALID_CAPABILITIES = frozenset({
    "text",
    "image",
    "video",
    "voice",
    "tts",
    "music",
    "sfx",
    "audio",
    "stt",
    "media_download",
    "transform",
    "rerank",
    "vision",
})

# ==============================================================================
# 2. CANONICAL PROVIDER CATALOG (From Bot source / runtime contracts)
# ==============================================================================
CANONICAL_PROVIDERS_CATALOG: dict[str, dict[str, Any]] = {
    "shopaikey": {
        "provider_id": "shopaikey",
        "display_name": "ShopAIKey",
        "provider_kind": "commercial_api",
        "capabilities": ["video", "image", "text"],
        "default_routing_priority": 1,
        "notes": "Primary video and generative commercial API adapter on Bot Core.",
    },
    "key4u": {
        "provider_id": "key4u",
        "display_name": "Key4U",
        "provider_kind": "commercial_api",
        "capabilities": ["text", "image", "video", "voice", "music", "stt", "rerank"],
        "default_routing_priority": 2,
        "notes": "Secondary / multi-modal backup candidate adapter.",
    },
    "gemini": {
        "provider_id": "gemini",
        "display_name": "Google Gemini",
        "provider_kind": "cloud_llm",
        "capabilities": ["text", "image", "vision"],
        "default_routing_priority": 1,
        "notes": "Primary LLM chat, prompt expansion, and vision analysis adapter.",
    },
    "groq": {
        "provider_id": "groq",
        "display_name": "Groq",
        "provider_kind": "cloud_llm",
        "capabilities": ["text"],
        "default_routing_priority": 2,
        "notes": "Fast inference LLM fallback adapter.",
    },
    "claude": {
        "provider_id": "claude",
        "display_name": "Anthropic Claude",
        "provider_kind": "cloud_llm",
        "capabilities": ["text"],
        "default_routing_priority": 3,
        "notes": "High-quality text synthesis adapter.",
    },
    "cohere": {
        "provider_id": "cohere",
        "display_name": "Cohere",
        "provider_kind": "cloud_llm",
        "capabilities": ["text", "rerank"],
        "default_routing_priority": 4,
        "notes": "Reranking and text embedding adapter.",
    },
    "kling": {
        "provider_id": "kling",
        "display_name": "Kling AI",
        "provider_kind": "commercial_api",
        "capabilities": ["video"],
        "default_routing_priority": 2,
        "notes": "Cinematic video generation adapter.",
    },
    "heygen": {
        "provider_id": "heygen",
        "display_name": "HeyGen",
        "provider_kind": "commercial_api",
        "capabilities": ["video"],
        "default_routing_priority": 3,
        "notes": "Talking avatar video adapter.",
    },
    "elevenlabs": {
        "provider_id": "elevenlabs",
        "display_name": "ElevenLabs",
        "provider_kind": "commercial_api",
        "capabilities": ["voice", "tts"],
        "default_routing_priority": 1,
        "notes": "High-fidelity voice synthesis and cloning adapter.",
    },
    "fish_audio": {
        "provider_id": "fish_audio",
        "display_name": "Fish Audio",
        "provider_kind": "commercial_api",
        "capabilities": ["voice", "tts"],
        "default_routing_priority": 2,
        "notes": "Voice synthesis and cloning fallback adapter.",
    },
    "auphonic": {
        "provider_id": "auphonic",
        "display_name": "Auphonic",
        "provider_kind": "commercial_api",
        "capabilities": ["audio"],
        "default_routing_priority": 1,
        "notes": "Audio post-production and leveling adapter.",
    },
    "beatoven": {
        "provider_id": "beatoven",
        "display_name": "Beatoven",
        "provider_kind": "commercial_api",
        "capabilities": ["music"],
        "default_routing_priority": 1,
        "notes": "Background music synthesis adapter.",
    },
    "freesound": {
        "provider_id": "freesound",
        "display_name": "Freesound",
        "provider_kind": "commercial_api",
        "capabilities": ["audio", "sfx"],
        "default_routing_priority": 1,
        "notes": "Sound effect catalog and audio lookup adapter.",
    },
    "jamendo": {
        "provider_id": "jamendo",
        "display_name": "Jamendo",
        "provider_kind": "commercial_api",
        "capabilities": ["music"],
        "default_routing_priority": 2,
        "notes": "Royalty-free music library adapter.",
    },
    "clipdrop": {
        "provider_id": "clipdrop",
        "display_name": "Clipdrop",
        "provider_kind": "commercial_api",
        "capabilities": ["image"],
        "default_routing_priority": 1,
        "notes": "Image editing and background manipulation adapter.",
    },
    "cutout": {
        "provider_id": "cutout",
        "display_name": "Cutout.pro",
        "provider_kind": "commercial_api",
        "capabilities": ["image"],
        "default_routing_priority": 2,
        "notes": "Image cutout and enhancement adapter.",
    },
    "cobalt": {
        "provider_id": "cobalt",
        "display_name": "Cobalt",
        "provider_kind": "media_tool",
        "capabilities": ["media_download"],
        "default_routing_priority": 1,
        "notes": "Media downloader service adapter.",
    },
    "local_worker": {
        "provider_id": "local_worker",
        "display_name": "Local Worker / ComfyUI",
        "provider_kind": "self_hosted_worker",
        "capabilities": ["image", "video", "transform"],
        "default_routing_priority": 1,
        "notes": "Self-hosted GPU worker for local generation and transform pipelines.",
    },
    "wokushop": {
        "provider_id": "wokushop",
        "display_name": "WokuShop",
        "provider_kind": "commercial_api",
        "capabilities": ["video"],
        "default_routing_priority": 99,
        "notes": "Parked commercial provider (disabled due to cost policy).",
    },
}

WEB_METADATA_CATALOG_COUNT = len(CANONICAL_PROVIDERS_CATALOG)
WEB_PROVIDER_METADATA_COUNT = WEB_METADATA_CATALOG_COUNT
CANONICAL_PROVIDER_COUNT = WEB_METADATA_CATALOG_COUNT

# ==============================================================================
# 3. REDACTION & SECRET SCRUBBING
# ==============================================================================
SENSITIVE_FIELD_PARTS = frozenset({
    "token", "secret", "apikey", "authorization", "password", "privatekey",
    "bearer", "cookie", "header", "credential", "authheader", "webhooksecret",
    "accesskey", "secretkey", "hmac", "clientsecret",
})

SAFE_PROVIDER_SCALAR_KEYS = frozenset({
    "provider_id", "display_name", "provider_kind", "configured",
    "credential_present", "available", "health_state", "effective_health_state",
    "current_healthy_evidence", "routing_eligible", "source_of_truth",
    "last_observed_at", "error_state", "notes", "selected", "priority",
    "probation", "stale", "status",
})


def is_sensitive_key(key_name: str) -> bool:
    normalized = "".join(character for character in str(key_name).lower() if character.isalnum())
    return any(part in normalized for part in SENSITIVE_FIELD_PARTS)


def redact_provider_secrets(value: Any, depth: int = 0) -> Any:
    """Recursively scrub all secrets, tokens, API keys, and private credentials.

    Ensures RAW_SECRET_EXPOSURE = 0 and RAW_TOKEN_EXPOSURE = 0.
    """
    if depth > 8:
        return None
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for k, v in value.items():
            key_str = str(k)[:100]
            if is_sensitive_key(key_str):
                # Replace with safe boolean if boolean-shaped or strip
                if isinstance(v, bool):
                    clean[key_str] = v
                continue
            clean[key_str] = redact_provider_secrets(v, depth=depth + 1)
        return clean
    if isinstance(value, (list, tuple)):
        return [redact_provider_secrets(item, depth=depth + 1) for item in value[:150]]
    if isinstance(value, str):
        # Truncate strings to prevent giant log injection
        return value[:1000]
    return value


# ==============================================================================
# 4. SYNTHESIS ENGINE
# ==============================================================================
def synthesize_provider_record(
    raw: dict[str, Any],
    canonical_fallback: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Synthesize one truthful provider record enforcing state separation.

    Invariants:
    - CONFIGURED != AVAILABLE != HEALTHY != ELIGIBLE != SELECTED
    - FAKE_PROVIDER_ROW = 0
    - UNKNOWN_PROVIDER_AS_HEALTHY = 0
    - CAPABILITY_FAKE_READY = 0
    - ROUTING_READY_FAKE = 0
    - RAW_SECRET_EXPOSURE = 0
    """
    cleaned = redact_provider_secrets(raw) if isinstance(raw, dict) else {}
    fallback = canonical_fallback or {}

    provider_id = str(cleaned.get("provider_id") or cleaned.get("id") or fallback.get("provider_id") or "").strip().lower()
    if not provider_id:
        return {}

    display_name = str(cleaned.get("display_name") or cleaned.get("name") or fallback.get("display_name") or provider_id.upper())[:100]
    provider_kind = str(cleaned.get("provider_kind") or cleaned.get("kind") or fallback.get("provider_kind") or "commercial_api")[:60]
    if provider_kind not in VALID_PROVIDER_KINDS:
        provider_kind = "commercial_api"

    # 1. CONFIGURED: Are credentials / configurations present?
    configured = bool(cleaned.get("configured", fallback.get("configured", False)))
    credential_present = bool(cleaned.get("credential_present", configured))

    # 2. FRESHNESS & OBSERVATION TIMESTAMP
    last_observed_at_raw = cleaned.get("last_observed_at") or cleaned.get("updated_at")
    last_observed_at = str(last_observed_at_raw).strip() if last_observed_at_raw is not None else ""
    stale = False
    has_valid_timestamp = False

    if last_observed_at:
        try:
            dt = datetime.fromisoformat(last_observed_at.replace("Z", "+00:00"))
            age_seconds = (datetime.now(timezone.utc) - dt).total_seconds()
            if age_seconds > PROVIDER_OBSERVATION_FRESHNESS_SECONDS:
                stale = True
                has_valid_timestamp = True
            else:
                stale = False
                has_valid_timestamp = True
        except (ValueError, TypeError):
            stale = True
            has_valid_timestamp = False
    else:
        # Missing last_observed_at: no observation timestamp exists
        stale = True
        has_valid_timestamp = False

    # 3. HEALTH_STATE (Observed) vs EFFECTIVE_HEALTH_STATE (Current Verification)
    if not configured:
        health_state = "UNAVAILABLE"
        effective_health_state = "UNAVAILABLE"
        healthy = False
        available = False
        current_healthy_evidence = False
    else:
        raw_health = str(cleaned.get("health_state") or cleaned.get("health") or "").strip().upper()
        if raw_health in VALID_HEALTH_STATES:
            health_state = raw_health
        else:
            health_state = "UNKNOWN"

        healthy = (health_state == "HEALTHY")

        # Determine effective current health:
        # Claimed HEALTHY requires a valid, fresh observation timestamp to be effective.
        if health_state == "HEALTHY":
            if not has_valid_timestamp:
                effective_health_state = "UNKNOWN_CURRENT_HEALTH"
                current_healthy_evidence = False
            elif stale:
                effective_health_state = "STALE_HEALTHY"
                current_healthy_evidence = False
            else:
                effective_health_state = "HEALTHY"
                current_healthy_evidence = True
        else:
            effective_health_state = health_state
            current_healthy_evidence = False

        # Availability:
        # Cannot be available if unconfigured or UNAVAILABLE
        raw_available = cleaned.get("available")
        if raw_available is not None:
            available = bool(raw_available) and (health_state in {"HEALTHY", "DEGRADED"})
        else:
            available = (health_state in {"HEALTHY", "DEGRADED"})

    # 4. CAPABILITIES: declared vs executable vs healthy vs ready
    # Rule (FAIL-CLOSED):
    # - declared: True if cap name is known / declared.
    # - executable: True ONLY when Bot/provider payload explicitly proves executable=True.
    #   Missing or plain string -> executable=False, ready=False.
    #   Fallback metadata catalog NEVER supplies executable=True or ready=True.
    # - healthy: current_healthy_evidence AND (cap.get("healthy", True) if isinstance(cap, dict) else True)
    # - ready: declared AND executable AND configured AND available AND current_healthy_evidence AND ready!=False
    raw_caps = cleaned.get("capabilities") or fallback.get("capabilities") or []
    capabilities: list[dict[str, Any]] = []
    if isinstance(raw_caps, list):
        for cap in raw_caps:
            cap_name = str(cap.get("name") if isinstance(cap, dict) else cap).strip().lower()
            if not cap_name:
                continue
            cap_declared = True

            # Canonical execution evidence:
            # Fallback catalog cannot supply executable. Only cleaned (Bot payload) dict with executable=True qualifies.
            cap_executable = False
            if isinstance(cap, dict) and cap.get("executable") is True:
                cap_executable = bool(configured)

            cap_healthy = bool(
                current_healthy_evidence
                and (cap.get("healthy", True) if isinstance(cap, dict) else True)
            )

            # CAPABILITY_FAKE_READY = 0:
            # ready requires declared + executable + configured + available + current healthy evidence
            cap_ready = bool(
                cap_declared
                and cap_executable
                and configured
                and available
                and current_healthy_evidence
                and (cap.get("ready", True) if isinstance(cap, dict) else True)
            )
            capabilities.append({
                "name": cap_name,
                "declared": cap_declared,
                "executable": cap_executable,
                "healthy": cap_healthy,
                "ready": cap_ready,
            })

    # 5. ROUTING_ELIGIBILITY (FAIL-CLOSED):
    # Rule:
    # - Web MAY DOWNGRADE canonical provider state.
    # - Web MUST NEVER PROMOTE absent/unknown Bot evidence into routing_eligible=True.
    # - raw routing_eligible MUST be explicitly True from canonical Bot evidence.
    # - If raw routing_eligible is missing, False, or non-boolean: routing_eligible = False.
    # - Local Web health policy may only veto eligibility (DOWNGRADE_ONLY). It may never grant eligibility.
    raw_eligible = cleaned.get("routing_eligible")
    has_canonical_routing_evidence = (raw_eligible is True)
    probation = bool(cleaned.get("probation", False))

    if not has_canonical_routing_evidence or not configured or not available or probation or not current_healthy_evidence:
        routing_eligible = False
    else:
        routing_eligible = True

    # 6. SELECTED (FAIL-CLOSED):
    # selected=True only when BOTH raw selected=True AND canonical routing_eligible=True.
    raw_selected = cleaned.get("selected")
    has_canonical_selected_evidence = (raw_selected is True)
    selected = bool(has_canonical_selected_evidence and routing_eligible)

    # 7. ERROR STATE: Categorized error string or None
    error_state = str(cleaned.get("error_state") or cleaned.get("error") or "").strip() or None

    return {
        "provider_id": provider_id,
        "display_name": display_name,
        "provider_kind": provider_kind,
        "capabilities": capabilities,
        "configured": configured,
        "credential_present": credential_present,
        "available": available,
        "health_state": health_state,
        "effective_health_state": effective_health_state,
        "current_healthy_evidence": current_healthy_evidence,
        "routing_eligible": routing_eligible,
        "selected": selected,
        "probation": probation,
        "stale": stale,
        "source_of_truth": PROVIDER_AUTHORITY,
        "runtime_source": PROVIDER_RUNTIME_SOURCE,
        "last_observed_at": last_observed_at or None,
        "error_state": error_state,
        "notes": str(cleaned.get("notes") or fallback.get("notes") or "")[:255],
    }


def synthesize_providers_read_model(
    data: Any,
    *,
    bridge_status: str = "completed",
    bridge_error_code: str | None = None,
) -> dict[str, Any]:
    """Synthesize complete Admin Provider read-model payload.

    Prevents BACKEND_FAILURE_FAKE_EMPTY:
    - Distinguishes:
      - NO_PROVIDERS_CONFIGURED: valid items, but 0 configured
      - READ_MODEL_UNAVAILABLE: bridge down or not configured
      - SOURCE_ERROR: bridge 5xx / malformed response
      - EMPTY_VALID_REGISTRY: valid response from source with 0 items
    """
    if bridge_status in {"guarded", "unavailable"} or bridge_error_code in {"CORE_BRIDGE_NOT_CONFIGURED", "CORE_BRIDGE_UNAVAILABLE"}:
        return {
            "module": "providers",
            "read_only": True,
            "items": [],
            "summary": {
                "total_providers": 0,
                "configured_count": 0,
                "available_count": 0,
                "healthy_count": 0,
                "routing_eligible_count": 0,
            },
            "authority": PROVIDER_AUTHORITY,
            "runtime_source": PROVIDER_RUNTIME_SOURCE,
            "read_model_state": "READ_MODEL_UNAVAILABLE",
        }

    if bridge_status in {"error", "failed"} or bridge_error_code in {"CORE_BRIDGE_INVALID_RESPONSE"}:
        return {
            "module": "providers",
            "read_only": True,
            "items": [],
            "summary": {
                "total_providers": 0,
                "configured_count": 0,
                "available_count": 0,
                "healthy_count": 0,
                "routing_eligible_count": 0,
            },
            "authority": PROVIDER_AUTHORITY,
            "runtime_source": PROVIDER_RUNTIME_SOURCE,
            "read_model_state": "SOURCE_ERROR",
        }

    if not isinstance(data, dict):
        return {
            "module": "providers",
            "read_only": True,
            "items": [],
            "summary": {
                "total_providers": 0,
                "configured_count": 0,
                "available_count": 0,
                "healthy_count": 0,
                "routing_eligible_count": 0,
            },
            "authority": PROVIDER_AUTHORITY,
            "runtime_source": PROVIDER_RUNTIME_SOURCE,
            "read_model_state": "EMPTY_VALID_REGISTRY",
        }

    raw_items = data.get("items")
    if not isinstance(raw_items, list):
        if isinstance(data.get("providers"), dict):
            raw_items = list(data["providers"].values())
        elif isinstance(data.get("providers"), list):
            raw_items = data["providers"]
        else:
            raw_items = []

    items: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for entry in raw_items:
        if not isinstance(entry, dict):
            continue
        pid = str(entry.get("provider_id") or entry.get("id") or "").strip().lower()
        if not pid or pid in seen_ids:
            continue
        fallback = CANONICAL_PROVIDERS_CATALOG.get(pid)
        record = synthesize_provider_record(entry, canonical_fallback=fallback)
        if record:
            items.append(record)
            seen_ids.add(pid)

    # Summary statistics
    total = len(items)
    configured_count = sum(1 for item in items if item.get("configured"))
    available_count = sum(1 for item in items if item.get("available"))
    healthy_count = sum(1 for item in items if item.get("health_state") == "HEALTHY")
    eligible_count = sum(1 for item in items if item.get("routing_eligible"))

    if total == 0:
        read_model_state = "EMPTY_VALID_REGISTRY"
    elif configured_count == 0:
        read_model_state = "NO_PROVIDERS_CONFIGURED"
    else:
        read_model_state = "VALID_REGISTRY"

    return {
        "module": "providers",
        "read_only": True,
        "items": items,
        "summary": {
            "total_providers": total,
            "configured_count": configured_count,
            "available_count": available_count,
            "healthy_count": healthy_count,
            "routing_eligible_count": eligible_count,
        },
        "authority": PROVIDER_AUTHORITY,
        "runtime_source": PROVIDER_RUNTIME_SOURCE,
        "read_model_state": read_model_state,
    }


# ==============================================================================
# 5. CONTROL BUTTONS & ACTIONS AUDITOR (DEAD_PROVIDER_CTA = 0)
# ==============================================================================
ACTION_CLASSIFICATIONS: dict[str, dict[str, Any]] = {
    "refresh": {
        "classification": "LOCAL_SOURCE_ONLY",
        "executable_on_web": True,
        "title": "Làm mới dữ liệu quản trị từ Core Bridge canonical",
        "requires_admin": True,
    },
    "test": {
        "classification": "EXTERNAL_NETWORK",
        "executable_on_web": False,
        "title": "Thao tác test provider trực tiếp bị khóa trên Web để bảo vệ mạng và ngân sách",
        "requires_admin": True,
    },
    "health_check": {
        "classification": "EXTERNAL_NETWORK",
        "executable_on_web": False,
        "title": "Kiểm tra sức khỏe provider thuộc quyền Bot Core canonical",
        "requires_admin": True,
    },
    "enable": {
        "classification": "MUTATING",
        "executable_on_web": False,
        "title": "Bật provider thuộc quyền cấu hình Bot Core trên VPS",
        "requires_admin": True,
    },
    "disable": {
        "classification": "MUTATING",
        "executable_on_web": False,
        "title": "Tắt provider thuộc quyền cấu hình Bot Core trên VPS",
        "requires_admin": True,
    },
    "freeze": {
        "classification": "MUTATING",
        "executable_on_web": False,
        "title": "Đóng băng provider thuộc quyền Bot Core",
        "requires_admin": True,
    },
    "unfreeze": {
        "classification": "MUTATING",
        "executable_on_web": False,
        "title": "Bỏ đóng băng provider thuộc quyền Bot Core",
        "requires_admin": True,
    },
    "rotate_credential": {
        "classification": "MUTATING",
        "executable_on_web": False,
        "title": "Web App không quản lý hoặc thay đổi secret/API keys",
        "requires_admin": True,
    },
    "save": {
        "classification": "MUTATING",
        "executable_on_web": False,
        "title": "Ghi cấu hình provider bị khóa trên Web (Read-Model Only)",
        "requires_admin": True,
    },
}


def classify_provider_action(action_name: str) -> dict[str, Any]:
    """Classify any provider control or button action.

    Guarantees DEAD_PROVIDER_CTA = 0 and FAKE_PROVIDER_ACTION_SUCCESS = 0.
    """
    normalized = str(action_name or "").strip().lower()
    if normalized in ACTION_CLASSIFICATIONS:
        return dict(ACTION_CLASSIFICATIONS[normalized])
    return {
        "classification": "NOT_IMPLEMENTED",
        "executable_on_web": False,
        "title": f"Thao tác '{action_name}' không được hỗ trợ trên Web App",
        "requires_admin": True,
    }
