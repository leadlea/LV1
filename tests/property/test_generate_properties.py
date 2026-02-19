"""Property-based tests for generate_handler.

Feature: ai-levels-lv1-mvp, Property 1: 生成結果の構造的正当性
Feature: ai-levels-lv1-mvp, Property 2: 生成結果のランダム性

Validates: Requirements 1.1, 1.2, 1.4
"""

import json
from unittest.mock import patch

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from backend.handlers.generate_handler import handler

VALID_TYPES = ["multiple_choice", "free_text", "scenario"]


def _question_strategy():
    """Generate a valid question dict as Bedrock would return."""
    return st.fixed_dictionaries({
        "step": st.integers(min_value=1, max_value=20),
        "type": st.sampled_from(VALID_TYPES),
        "prompt": st.text(min_size=1, max_size=200).filter(lambda s: s.strip()),
        "options": st.just(None),
        "context": st.one_of(st.none(), st.text(min_size=1, max_size=100)),
    })


def _bedrock_response(questions):
    """Build a mock Bedrock response wrapping the given questions."""
    return {
        "content": [{"text": json.dumps({"questions": questions}, ensure_ascii=False)}]
    }


@given(
    session_id=st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),
    questions=st.lists(_question_strategy(), min_size=1, max_size=10),
)
@settings(max_examples=100)
def test_generate_response_structure(session_id, questions):
    """Property 1: 生成結果の構造的正当性

    任意のセッションIDに対して、Test_Generatorが返す生成結果は、
    questions配列を含み、各要素がstep（1からの連番）、
    type（"multiple_choice" | "free_text" | "scenario"のいずれか）、
    prompt（空でない文字列）を持つ正しいJSON構造であること。

    **Validates: Requirements 1.1, 1.4**
    """
    event = {"body": json.dumps({"session_id": session_id})}

    with patch("backend.handlers.generate_handler.invoke_claude") as mock_invoke:
        mock_invoke.return_value = _bedrock_response(questions)
        resp = handler(event, None)

    assert resp["statusCode"] == 200

    body = json.loads(resp["body"])

    # session_id is echoed back
    assert body["session_id"] == session_id

    # questions array exists and is non-empty
    assert isinstance(body["questions"], list)
    assert len(body["questions"]) >= 1

    for q in body["questions"]:
        # step is a positive integer
        assert isinstance(q["step"], int)
        assert q["step"] >= 1

        # type is one of the valid values
        assert q["type"] in {"multiple_choice", "free_text", "scenario"}

        # prompt is a non-empty string
        assert isinstance(q["prompt"], str)
        assert q["prompt"].strip() != ""


@given(
    session_id=st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),
    questions_a=st.lists(_question_strategy(), min_size=1, max_size=6),
    questions_b=st.lists(_question_strategy(), min_size=1, max_size=6),
)
@settings(max_examples=100)
def test_generate_randomness(session_id, questions_a, questions_b):
    """Property 2: 生成結果のランダム性

    同一セッションIDで2回呼び出した場合、Bedrockが異なる内容を返せば
    生成されるテスト・ドリルの内容（promptフィールド）が完全一致しないこと。

    **Validates: Requirements 1.2**
    """
    # Ensure the two question sets actually differ in prompts
    prompts_a = [q["prompt"] for q in questions_a]
    prompts_b = [q["prompt"] for q in questions_b]
    assume(prompts_a != prompts_b)

    event = {"body": json.dumps({"session_id": session_id})}

    with patch("backend.handlers.generate_handler.invoke_claude") as mock_invoke:
        mock_invoke.side_effect = [
            _bedrock_response(questions_a),
            _bedrock_response(questions_b),
        ]
        resp1 = handler(event, None)
        resp2 = handler(event, None)

    assert resp1["statusCode"] == 200
    assert resp2["statusCode"] == 200

    body1 = json.loads(resp1["body"])
    body2 = json.loads(resp2["body"])

    # Both use the same session_id
    assert body1["session_id"] == body2["session_id"] == session_id

    # The prompt content should differ between the two calls
    result_prompts_a = [q["prompt"] for q in body1["questions"]]
    result_prompts_b = [q["prompt"] for q in body2["questions"]]
    assert result_prompts_a != result_prompts_b
