"""Property-based tests for gate_handler gating logic.

Feature: ai-levels-lv1-mvp, Property 7: ゲーティングロジックの正当性

Validates: Requirements 6.3
"""

import json
from unittest.mock import MagicMock, patch

from hypothesis import given, settings
from hypothesis import strategies as st

from backend.handlers.gate_handler import _build_levels, handler


def _uuid_v4_strategy():
    """Generate valid UUID v4 strings."""
    hex_chars = "0123456789abcdef"
    return st.tuples(
        st.text(alphabet=hex_chars, min_size=8, max_size=8),
        st.text(alphabet=hex_chars, min_size=4, max_size=4),
        st.text(alphabet=hex_chars, min_size=3, max_size=3),
        st.sampled_from(list("89ab")),
        st.text(alphabet=hex_chars, min_size=3, max_size=3),
        st.text(alphabet=hex_chars, min_size=12, max_size=12),
    ).map(lambda t: f"{t[0]}-{t[1]}-4{t[2]}-{t[3]}{t[4]}-{t[5]}")


@given(lv1_passed=st.booleans())
@settings(max_examples=100)
def test_gating_logic_correctness(lv1_passed):
    """Property 7: ゲーティングロジックの正当性

    任意のセッション状態に対して、Lv1が合格していない場合、
    レベル状態APIはLv2以降のunlockedをfalseで返すこと。
    Lv1が合格している場合のみLv2のunlockedがtrueになること。

    **Validates: Requirements 6.3**
    """
    levels = _build_levels(lv1_passed)

    # Lv1 is always unlocked
    assert levels["lv1"]["unlocked"] is True
    assert levels["lv1"]["passed"] == lv1_passed

    if not lv1_passed:
        # When Lv1 not passed, Lv2-Lv4 must all be locked
        assert levels["lv2"]["unlocked"] is False
        assert levels["lv3"]["unlocked"] is False
        assert levels["lv4"]["unlocked"] is False
    else:
        # When Lv1 passed, only Lv2 unlocks
        assert levels["lv2"]["unlocked"] is True
        assert levels["lv3"]["unlocked"] is False
        assert levels["lv4"]["unlocked"] is False

    # Lv2-Lv4 are never passed in current MVP
    assert levels["lv2"]["passed"] is False
    assert levels["lv3"]["passed"] is False
    assert levels["lv4"]["passed"] is False


@given(session_id=_uuid_v4_strategy(), lv1_passed=st.booleans())
@settings(max_examples=100)
def test_gating_handler_end_to_end(session_id, lv1_passed):
    """Property 7 (handler): ゲーティングロジックの正当性（ハンドラ経由）

    任意のセッション状態に対して、ハンドラ経由でも同じゲーティング
    ルールが適用されることを検証する。

    **Validates: Requirements 6.3**
    """
    event = {"queryStringParameters": {"session_id": session_id}}

    mock_table = MagicMock()
    if lv1_passed:
        mock_table.get_item.return_value = {"Item": {"lv1_passed": True}}
    else:
        mock_table.get_item.return_value = {}

    mock_dynamodb = MagicMock()
    mock_dynamodb.Table.return_value = mock_table

    with patch("backend.handlers.gate_handler._get_dynamodb_resource", return_value=mock_dynamodb):
        resp = handler(event, None)

    assert resp["statusCode"] == 200
    data = json.loads(resp["body"])
    levels = data["levels"]

    if not lv1_passed:
        assert levels["lv2"]["unlocked"] is False
        assert levels["lv3"]["unlocked"] is False
        assert levels["lv4"]["unlocked"] is False
    else:
        assert levels["lv2"]["unlocked"] is True
        assert levels["lv3"]["unlocked"] is False
        assert levels["lv4"]["unlocked"] is False
