"""Language must survive the real stateless planner receipt before saving."""
import json
from pathlib import Path

import pytest

from copyfast_video_studio import VideoPromptPlannerRequest, _compose_video_prompt_plan


@pytest.mark.parametrize("language", ["vi", "en"])
def test_real_prompt_receipt_echoes_the_validated_source_language(language):
    rows = json.loads((Path(__file__).parent / "fixtures" / "video-inner-composer-samples.json").read_text(encoding="utf-8"))
    payload = {**rows[0]["source"], "language": language}
    request = VideoPromptPlannerRequest.model_validate(payload)
    result = _compose_video_prompt_plan(request)
    assert result.get("language") == language
