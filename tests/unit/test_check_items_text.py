"""
エンジニア項目テキスト変更のユニットテスト

施策4: エンジニア項目の文言調整
- eng_1, eng_2, eng_5 が新テキストに更新されていることを検証
- eng_3, eng_4, eng_6 が変更されていないことを検証
- 項目ID（eng_1〜eng_6）が全て保持されていることを検証

Requirements: 4.1, 4.2, 4.3, 4.5, 4.6, 4.7
"""

from backend.lib.check_items import ENGINEER_ITEMS


def _items_by_id() -> dict[str, str]:
    return {item["id"]: item["text"] for item in ENGINEER_ITEMS}


class TestEngineerItemTextUpdates:
    """eng_1, eng_2, eng_5 が新テキストに更新されていること"""

    def test_eng_1_updated(self):
        items = _items_by_id()
        assert items["eng_1"] == "AIによる開発・運用支援ツールを日常的に活用している"

    def test_eng_2_updated(self):
        items = _items_by_id()
        assert items["eng_2"] == "AIを活用したレビュー・テスト・品質管理を実践している"

    def test_eng_5_updated(self):
        items = _items_by_id()
        assert items["eng_5"] == "AIを活用した開発・運用プロセスの標準化・自動化を推進している"


class TestEngineerItemTextUnchanged:
    """eng_3, eng_4, eng_6 が変更されていないこと"""

    def test_eng_3_unchanged(self):
        items = _items_by_id()
        assert items["eng_3"] == "AIを活用したアーキテクチャ設計・技術選定を行っている"

    def test_eng_4_unchanged(self):
        items = _items_by_id()
        assert items["eng_4"] == "AI/MLモデルの評価・選定・統合ができる"

    def test_eng_6_unchanged(self):
        items = _items_by_id()
        assert items["eng_6"] == "AI技術の社内導入・技術支援をリードしている"


class TestEngineerItemIdsPreserved:
    """項目ID（eng_1〜eng_6）が全て保持されていること"""

    def test_all_ids_present(self):
        ids = {item["id"] for item in ENGINEER_ITEMS}
        expected = {"eng_1", "eng_2", "eng_3", "eng_4", "eng_5", "eng_6"}
        assert ids == expected

    def test_item_count(self):
        assert len(ENGINEER_ITEMS) == 6
