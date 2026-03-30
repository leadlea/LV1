"""セルフチェック項目定義"""

COMMON_ITEMS = [
    {"id": "common_1", "text": "生成AIの基本的な仕組みと限界を理解している"},
    {"id": "common_2", "text": "生成AIを業務で安全に利用するためのルールを理解している"},
    {"id": "common_3", "text": "プロンプトを工夫して目的に合った出力を得られる"},
    {"id": "common_4", "text": "生成AIの出力を批判的に評価し、正確性を検証できる"},
    {"id": "common_5", "text": "生成AIを使って業務の効率化を実践している"},
    {"id": "common_6", "text": "生成AIの活用事例を他者に説明・共有できる"},
]

BUSINESS_ITEMS = [
    {"id": "biz_1", "text": "AIを活用した情報収集・要約で業務判断を効率化している"},
    {"id": "biz_2", "text": "AIを活用して提案資料・報告書の品質を向上させている"},
    {"id": "biz_3", "text": "AIを活用してプロジェクト計画・タスク分解を行っている"},
    {"id": "biz_4", "text": "AIを活用した業務改善の提案・実行ができる"},
    {"id": "biz_5", "text": "AIを活用してコミュニケーション品質を向上させている"},
    {"id": "biz_6", "text": "AI活用のベストプラクティスをチームに展開している"},
]

ENGINEER_ITEMS = [
    {"id": "eng_1", "text": "AIによる開発・運用支援ツールを日常的に活用している"},
    {"id": "eng_2", "text": "AIを活用したレビュー・テスト・品質管理を実践している"},
    {"id": "eng_3", "text": "AIを活用したアーキテクチャ設計・技術選定を行っている"},
    {"id": "eng_4", "text": "AI/MLモデルの評価・選定・統合ができる"},
    {"id": "eng_5", "text": "AIを活用した開発・運用プロセスの標準化・自動化を推進している"},
    {"id": "eng_6", "text": "AI技術の社内導入・技術支援をリードしている"},
]


def get_items_for_track(track: str) -> list[dict]:
    """指定トラックの全チェック項目（共通6 + トラック別6 = 12項目）を返す。"""
    if track == "business":
        return COMMON_ITEMS + BUSINESS_ITEMS
    elif track == "engineer":
        return COMMON_ITEMS + ENGINEER_ITEMS
    else:
        raise ValueError(f"Invalid track: {track}")


def get_item_ids_for_track(track: str) -> set[str]:
    """指定トラックの全項目IDセットを返す。"""
    return {item["id"] for item in get_items_for_track(track)}
