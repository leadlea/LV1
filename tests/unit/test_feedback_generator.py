"""ユニットテスト: フィードバック生成"""

import json
from unittest.mock import patch

from backend.lib.feedback_generator import generate_feedback


SAMPLE_ANSWERS = {
    "common_1": 3, "common_2": 2, "common_3": 3,
    "common_4": 2, "common_5": 3, "common_6": 2,
    "biz_1": 3, "biz_2": 2, "biz_3": 3,
    "biz_4": 2, "biz_5": 3, "biz_6": 2,
}
SAMPLE_SCORES = {
    "common_avg": 2.5, "track_avg": 2.5,
    "overall_avg": 2.5, "skill_level": "Lv3",
}


def _mock_response(strengths="強み", improvements="改善", next_actions="アクション"):
    return {
        "content": [{"text": json.dumps({
            "strengths": strengths,
            "improvements": improvements,
            "next_actions": next_actions,
        }, ensure_ascii=False)}],
    }


class TestGenerateFeedback:
    def test_success(self):
        with patch("backend.lib.feedback_generator.invoke_claude") as mock:
            mock.return_value = _mock_response()
            result = generate_feedback("business", SAMPLE_ANSWERS, SAMPLE_SCORES)
        assert result is not None
        assert result["strengths"] == "強み"
        assert result["improvements"] == "改善"
        assert result["next_actions"] == "アクション"

    def test_bedrock_failure_returns_none(self):
        with patch("backend.lib.feedback_generator.invoke_claude") as mock:
            mock.side_effect = Exception("Bedrock error")
            result = generate_feedback("business", SAMPLE_ANSWERS, SAMPLE_SCORES)
        assert result is None

    def test_invalid_json_returns_none(self):
        with patch("backend.lib.feedback_generator.invoke_claude") as mock:
            mock.return_value = {"content": [{"text": "not json"}]}
            result = generate_feedback("business", SAMPLE_ANSWERS, SAMPLE_SCORES)
        assert result is None

    def test_missing_field_returns_none(self):
        with patch("backend.lib.feedback_generator.invoke_claude") as mock:
            mock.return_value = {"content": [{"text": json.dumps({
                "strengths": "ok", "improvements": "ok",
                # missing next_actions
            })}]}
            result = generate_feedback("business", SAMPLE_ANSWERS, SAMPLE_SCORES)
        assert result is None

    def test_code_fence_stripped(self):
        fenced = '```json\n' + json.dumps({
            "strengths": "s", "improvements": "i", "next_actions": "n",
        }) + '\n```'
        with patch("backend.lib.feedback_generator.invoke_claude") as mock:
            mock.return_value = {"content": [{"text": fenced}]}
            result = generate_feedback("business", SAMPLE_ANSWERS, SAMPLE_SCORES)
        assert result is not None
        assert result["strengths"] == "s"
