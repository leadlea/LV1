"""
Property tests for backend/frontend engineer item text synchronization.

Feature: aoki-feedback-improvements
Property 4: エンジニア項目テキストのバックエンド/フロントエンド同期

Validates: Requirements 4.4
"""

import re
from pathlib import Path

from hypothesis import given, settings, strategies as st

from backend.lib.check_items import ENGINEER_ITEMS

# フロントエンドJSからENGINEER_ITEMSをパースする
_JS_PATH = Path(__file__).resolve().parents[2] / "frontend" / "js" / "selfcheck-app.js"


def _parse_frontend_engineer_items() -> dict[str, str]:
    """selfcheck-app.js の ENGINEER_ITEMS を解析し {id: text} を返す。"""
    js_content = _JS_PATH.read_text(encoding="utf-8")

    # ENGINEER_ITEMS = [ ... ]; ブロックを抽出
    match = re.search(
        r"const\s+ENGINEER_ITEMS\s*=\s*\[(.*?)\];",
        js_content,
        re.DOTALL,
    )
    assert match, "ENGINEER_ITEMS not found in selfcheck-app.js"

    block = match.group(1)
    items: dict[str, str] = {}
    for m in re.finditer(r'id:\s*"([^"]+)".*?text:\s*"([^"]+)"', block):
        items[m.group(1)] = m.group(2)
    return items


FRONTEND_ENGINEER_MAP = _parse_frontend_engineer_items()
BACKEND_ENGINEER_MAP = {item["id"]: item["text"] for item in ENGINEER_ITEMS}

engineer_id_st = st.sampled_from(list(BACKEND_ENGINEER_MAP.keys()))


@settings(max_examples=100)
@given(item_id=engineer_id_st)
def test_engineer_item_text_sync(item_id):
    """
    Feature: aoki-feedback-improvements, Property 4: エンジニア項目テキストのバックエンド/フロントエンド同期

    任意のエンジニア項目IDに対して、バックエンド(check_items.py)と
    フロントエンド(selfcheck-app.js)のテキストが同一であることを検証する。

    **Validates: Requirements 4.4**
    """
    assert item_id in FRONTEND_ENGINEER_MAP, (
        f"Item {item_id} not found in frontend ENGINEER_ITEMS"
    )
    assert BACKEND_ENGINEER_MAP[item_id] == FRONTEND_ENGINEER_MAP[item_id], (
        f"Text mismatch for {item_id}: "
        f"backend={BACKEND_ENGINEER_MAP[item_id]!r}, "
        f"frontend={FRONTEND_ENGINEER_MAP[item_id]!r}"
    )
