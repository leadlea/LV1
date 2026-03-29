"""
Property tests for track-based item selection.

Feature: sojitz-ai-skill-check
Property 3: トラック別項目選択の正当性
"""

from hypothesis import given, settings, strategies as st

from backend.lib.check_items import (
    get_items_for_track,
    get_item_ids_for_track,
    COMMON_ITEMS,
    BUSINESS_ITEMS,
    ENGINEER_ITEMS,
)

track_st = st.sampled_from(["business", "engineer"])


@settings(max_examples=200)
@given(track=track_st)
def test_track_items_composition(track):
    """Feature: sojitz-ai-skill-check, Property 3: トラック別項目選択の正当性"""
    items = get_items_for_track(track)
    ids = get_item_ids_for_track(track)

    # 合計12項目
    assert len(items) == 12
    assert len(ids) == 12

    # 共通6項目を含む
    common_ids = {item["id"] for item in COMMON_ITEMS}
    assert common_ids.issubset(ids)

    # トラック固有6項目を含む
    if track == "business":
        track_ids = {item["id"] for item in BUSINESS_ITEMS}
        other_ids = {item["id"] for item in ENGINEER_ITEMS}
    else:
        track_ids = {item["id"] for item in ENGINEER_ITEMS}
        other_ids = {item["id"] for item in BUSINESS_ITEMS}

    assert track_ids.issubset(ids)
    # 異なるトラックの項目が混在しない
    assert other_ids.isdisjoint(ids)
