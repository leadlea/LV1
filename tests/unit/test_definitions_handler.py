"""ユニットテスト: スキル定義ハンドラ"""

import json
from backend.handlers.definitions_handler import handler


class TestDefinitionsHandler:
    def test_returns_both_tracks(self):
        resp = handler({}, None)
        assert resp["statusCode"] == 200
        data = json.loads(resp["body"])
        assert "business" in data
        assert "engineer" in data

    def test_business_levels(self):
        resp = handler({}, None)
        data = json.loads(resp["body"])
        biz = data["business"]
        for lv in ("Lv1", "Lv2", "Lv3", "Lv4", "Lv5"):
            assert lv in biz
            assert "name" in biz[lv]
            assert "description" in biz[lv]

    def test_engineer_levels(self):
        resp = handler({}, None)
        data = json.loads(resp["body"])
        eng = data["engineer"]
        for lv in ("Lv1", "Lv2", "Lv3", "Lv4", "Lv5"):
            assert lv in eng
            assert "name" in eng[lv]
            assert "description" in eng[lv]

    def test_cors_headers(self):
        resp = handler({}, None)
        assert resp["headers"]["Access-Control-Allow-Origin"] == "*"
