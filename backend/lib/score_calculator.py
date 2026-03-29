"""スコア集計・レベル判定モジュール"""

from backend.lib.check_items import get_item_ids_for_track

COMMON_IDS = ["common_1", "common_2", "common_3", "common_4", "common_5", "common_6"]
BUSINESS_IDS = ["biz_1", "biz_2", "biz_3", "biz_4", "biz_5", "biz_6"]
ENGINEER_IDS = ["eng_1", "eng_2", "eng_3", "eng_4", "eng_5", "eng_6"]

LEVEL_THRESHOLDS = [
    (0.0, 1.0, "Lv1"),
    (1.0, 2.0, "Lv2"),
    (2.0, 3.0, "Lv3"),
    (3.0, 3.5, "Lv4"),
    (3.5, 4.0, "Lv5"),
]


def validate_answers(track: str, answers: dict) -> str | None:
    """回答データのバリデーション。エラーメッセージまたはNoneを返す。"""
    if track not in ("business", "engineer"):
        return "track must be 'business' or 'engineer'"

    expected_ids = get_item_ids_for_track(track)
    if set(answers.keys()) != expected_ids:
        if len(answers) != 12:
            return "answers must contain exactly 12 items"
        return "answer keys do not match the selected track"

    for key, value in answers.items():
        if not isinstance(value, int) or isinstance(value, bool):
            return "each answer must be an integer between 0 and 4"
        if value < 0 or value > 4:
            return "each answer must be an integer between 0 and 4"

    return None


def determine_level(overall_avg: float) -> str:
    """overall_avgからSkill_Levelを判定する。"""
    if overall_avg >= 3.5:
        return "Lv5"
    if overall_avg >= 3.0:
        return "Lv4"
    if overall_avg >= 2.0:
        return "Lv3"
    if overall_avg >= 1.0:
        return "Lv2"
    return "Lv1"


def calculate_scores(track: str, answers: dict) -> dict:
    """
    スコア集計・レベル判定。
    戻り値: {"common_avg", "track_avg", "overall_avg", "skill_level"}
    """
    common_scores = [answers[k] for k in COMMON_IDS]
    track_ids = BUSINESS_IDS if track == "business" else ENGINEER_IDS
    track_scores = [answers[k] for k in track_ids]

    common_avg = sum(common_scores) / len(common_scores)
    track_avg = sum(track_scores) / len(track_scores)
    overall_avg = (common_avg + track_avg) / 2

    return {
        "common_avg": round(common_avg, 4),
        "track_avg": round(track_avg, 4),
        "overall_avg": round(overall_avg, 4),
        "skill_level": determine_level(overall_avg),
    }
