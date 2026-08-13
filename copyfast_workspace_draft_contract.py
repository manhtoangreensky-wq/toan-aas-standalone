"""Shared, bridge-free feature policy for Web-owned Workspace Drafts.

This leaf module deliberately depends only on the static product registry.
Both the broad Web API and the independent Project Studio boundary use the
same policy, so an upgraded or manually repaired database row cannot turn an
arbitrary feature string into a durable Web document.
"""

from __future__ import annotations

from typing import Any

from copyfast_registry import FEATURE_BY_KEY


FEATURE_TEXT_REQUIRED = frozenset({
    "chat", "prompt_studio", "caption", "hashtag", "hook", "script", "storyboard", "content_pack",
    "image_create", "image_transform", "video_single", "video_product", "video_trend",
    "video_text_to_video", "video_quick", "video_image_to_video", "video_multiscene", "video_long",
    "voice_tts", "voice_saved_tts", "music_background", "music_song", "music_sfx",
})
FEATURE_UPLOAD_REQUIRED = frozenset({
    "image_edit", "image_upscale", "image_transform", "image_remove_background", "video_image_to_video",
    "voice_clone", "music_upload", "subtitle_asr", "subtitle_create", "asr", "subtitle_translate",
    "video_dub", "documents", "documents_pdf", "documents_ocr", "documents_merge", "documents_split",
    "documents_compress", "documents_translate",
})
FEATURE_TARGET_LANGUAGE_REQUIRED = frozenset({"subtitle_translate", "video_dub", "documents_translate"})

# A feature must be a currently registered customer workflow as well as one
# with a Web draft/estimate/confirm contract.  Account, wallet, admin and
# read-only parity routes cannot become draftable because of a malformed row.
FEATURE_EXECUTION_CANDIDATE_KEYS = frozenset(
    FEATURE_TEXT_REQUIRED | FEATURE_UPLOAD_REQUIRED | FEATURE_TARGET_LANGUAGE_REQUIRED
)
WORKSPACE_DRAFT_ALLOWED_FEATURES = FEATURE_EXECUTION_CANDIDATE_KEYS


def is_workspace_draft_feature(value: Any) -> bool:
    """Return whether a value is an exact current Workspace Draft workflow."""
    feature = str(value or "").strip()
    return feature in WORKSPACE_DRAFT_ALLOWED_FEATURES and feature in FEATURE_BY_KEY
