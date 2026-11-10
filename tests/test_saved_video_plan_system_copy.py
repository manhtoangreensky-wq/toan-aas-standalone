"""Real pure save converters: content language, useful defaults and no data loss."""
import importlib
import itertools
import re
import sys

import pytest


@pytest.fixture
def video(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "saved-copy.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "owned-saved-copy-child-only")
    import socket

    def denied(*args, **kwargs):
        raise AssertionError("Pure saved-copy checks must not use network")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    sys.modules.pop("copyfast_video_studio", None)
    return importlib.import_module("copyfast_video_studio")


IDENTIFIER = "11111111-1111-4111-8111-111111111111"
CUSTOMER = "CUSTOMER_LITERAL_{p0}_{p1}_UNCHANGED"
AUDIENCE = "CUSTOMER_AUDIENCE_{p0}"
IMAGE_REF = {"direction_id": IDENTIFIER, "direction_title": CUSTOMER,
             "artboard_id": IDENTIFIER, "artboard_title": "CUSTOMER_ARTBOARD",
             "language": "vi", "aspect_ratio": "9:16", "source_image_attached": True}
REFERENCE = {"asset_id": IDENTIFIER, "display_name": "CUSTOMER_VIDEO_{p1}.mp4",
             "extension": "mp4", "content_type": "video/mp4", "source_video_attached": True}
BRANDS = re.compile(r"TikTok|Facebook|Instagram|Reels|YouTube|Shorts|Telegram|PayOS")
FOREIGN = {
    "vi": re.compile(r"[\u3400-\u9fff]|\b(?:private|web|editor|image|motion|studio|editorial|plan|planner|timing|source|direction|style|music|camera|audio|note|scene|media|render|queue|deliver|format|platform|tone|reference|selected|asset|vault|CTA)\b", re.I),
    "en": re.compile(r"[À-ỹ\u3400-\u9fff]"),
    "zh": re.compile(r"[À-ỹ]|\b(?:private|web|editor|image|motion|studio|editorial|plan|planner|timing|source|direction|style|music|camera|audio|note|scene|media|render|queue|deliver|format|platform|tone|reference|selected|asset|vault|CTA)\b", re.I),
}


def saved(video, kind, language, **choices):
    if kind == "image":
        ref = {**IMAGE_REF, "language": language}
        payload = video.ImageMotionPlannerPlanSaveRequest(
            direction_id=IDENTIFIER, style=choices.get("style", "cinematic"),
            motion=choices.get("motion", "hero_hold"), music=choices.get("music", "none"),
            duration_seconds=10, destination="video_plan", idempotency_key="owned-saved-copy-0001")
        planner = video._compose_image_motion_planner(payload, ref)
        plan, scenes = video._image_motion_planner_to_video_plan(payload, planner)
    else:
        ref = REFERENCE
        payload = video.ReferenceFormatPlannerPlanSaveRequest(
            asset_id=IDENTIFIER, direction=choices.get("direction", "product_ad"),
            platform=choices.get("platform", "tiktok"), goal=choices.get("goal", "educate"),
            tone=choices.get("tone", "clear"), topic=CUSTOMER, audience=AUDIENCE,
            language=language, duration_seconds=30, destination="video_plan",
            idempotency_key="owned-saved-copy-0001")
        planner = video._compose_reference_format_planner(payload, ref)
        plan, scenes = video._reference_format_planner_to_video_plan(payload, planner)
    return payload, planner, plan, scenes


def prose(plan, scenes):
    return [plan.title, plan.objective, plan.brief,
            *(text for scene in scenes for text in
              (scene.title, scene.visual_direction, scene.shot_notes, scene.transition))]


def without_customer(text):
    for value in (CUSTOMER, AUDIENCE, REFERENCE["display_name"]):
        text = text.replace(value, " ")
    return BRANDS.sub(" ", text)


def test_saved_system_prose_follows_content_language_for_every_existing_choice(video):
    """Catches a converter reintroducing fixed English or Vietnamese goal prose."""
    violations, counts = [], {"image": 0, "reference": 0}
    image_choices = itertools.product(
        ("cinematic", "product_reveal", "social", "editorial"),
        ("slow_push_in", "orbit_reveal", "handheld_detail", "hero_hold"),
        ("none", "cinematic_light", "modern_electronic", "natural_ambience"), ("vi", "en", "zh"))
    reference_choices = itertools.product(
        ("product_ad", "viral", "cinematic", "education"),
        ("tiktok", "reels", "shorts", "youtube", "facebook", "custom"),
        ("follow", "sales", "lead", "website", "educate"),
        ("clear", "warm", "confident", "premium", "educational"), ("vi", "en"))
    cases = (("image", row[-1], dict(zip(("style", "motion", "music"), row[:-1]))) for row in image_choices)
    refs = (("reference", row[-1], dict(zip(("direction", "platform", "goal", "tone"), row[:-1]))) for row in reference_choices)
    for kind, language, choices in itertools.chain(cases, refs):
        _, _, plan, scenes = saved(video, kind, language, **choices)
        counts[kind] += 1
        for text in prose(plan, scenes):
            found = FOREIGN[language].search(without_customer(text))
            if found and len(violations) < 12:
                violations.append((kind, language, found.group(), text[:250]))
    assert counts == {"image": 192, "reference": 1200}
    assert violations == [], violations


@pytest.mark.parametrize("kind,language", [("image", "vi"), ("image", "en"), ("image", "zh"), ("reference", "vi"), ("reference", "en")])
def test_saved_copy_has_no_invented_audience_and_no_repeated_execution_paragraphs(video, kind, language):
    """Catches default audience fabrication or per-scene disclaimer clutter."""
    _, _, plan, scenes = saved(video, kind, language)
    assert plan.audience == ("" if kind == "image" else AUDIENCE)
    assert len(plan.brief.splitlines()) == 3
    assert all(len(scene.shot_notes.splitlines()) == 4 for scene in scenes)


@pytest.mark.parametrize("kind,language", [("image", "vi"), ("image", "en"), ("image", "zh"), ("reference", "vi"), ("reference", "en")])
def test_saved_values_retain_customer_data_and_all_noncopy_fields(video, kind, language):
    """Catches interpolation rescans, customer translation and structural drift."""
    payload, planner, plan, scenes = saved(video, kind, language)
    assert plan.title == planner["title"] and CUSTOMER in plan.title
    assert plan.language == language and plan.format == "short_form"
    assert plan.target_duration_seconds == planner["duration_seconds"]
    assert plan.project_id is None and len(scenes) == 3
    if kind == "image":
        assert CUSTOMER in plan.brief and plan.aspect_ratio == "9:16"
        assert plan.tags == ["image-motion-planner", "style-cinematic", "motion-hero_hold", "music-none"]
    else:
        assert REFERENCE["display_name"] in plan.brief
        assert plan.audience == AUDIENCE
        assert plan.aspect_ratio == "9:16"
        assert plan.tags == ["reference-format-planner", "direction-product_ad", "platform-tiktok", "goal-educate", "tone-clear"]
    for index, (scene, original) in enumerate(zip(scenes, planner["scenes"]), 1):
        assert scene.title.endswith(original["title"])
        assert scene.scene_type == ("hook" if index == 1 else "cta" if index == 3 else "problem")
        assert scene.duration_seconds == original["end_seconds"] - original["start_seconds"]
        assert scene.visual_direction == original["visual_direction"]
        assert scene.transition == original["transition"]
        assert scene.narration == scene.on_screen_text == ""
        for field in ("camera", "audio_direction", "editorial_note"):
            assert original[field] in scene.shot_notes
        expected_tags = (["image-motion-planner", f"scene-{index}", "motion-hero_hold"] if kind == "image"
                         else ["reference-format-planner", f"scene-{index}", "direction-product_ad"])
        assert scene.tags == expected_tags
        assert len(scene.title) <= 180 and len(scene.shot_notes) <= 4800
    assert len(plan.title) <= 180 and len(plan.brief) <= 11900
    assert len(plan.objective) <= 1200


def test_unknown_image_language_keeps_raw_language_but_only_system_copy_falls_back(video):
    """Catches silently rewriting stored customer metadata as a locale fix."""
    _, _, plan, scenes = saved(video, "image", "fr")
    assert plan.language == "fr" and CUSTOMER in plan.title
    assert plan.audience == ""
    assert all(not FOREIGN["vi"].search(without_customer(text)) for text in prose(plan, scenes))
