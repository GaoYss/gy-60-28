from flask import Blueprint, jsonify, request

from ..data import DELIVERIES, SELECTIONS

selections_bp = Blueprint("selections", __name__)


@selections_bp.post("")
def save_selection():
    payload = request.get_json(silent=True) or {}
    code = payload.get("code")
    photo_ids = payload.get("photoIds")

    if not code or not isinstance(photo_ids, list):
        return jsonify({"message": "需要提供交付码和选片列表"}), 400

    delivery = next((item for item in DELIVERIES if item["code"] == code), None)
    if delivery is None:
        return jsonify({"message": "交付链接不存在"}), 404

    valid_ids = {photo["id"] for photo in delivery["photos"]}
    invalid = [photo_id for photo_id in photo_ids if photo_id not in valid_ids]
    if invalid:
        return jsonify({"message": "包含无效照片", "photoIds": invalid}), 400

    unique_ids = list(dict.fromkeys(photo_ids))
    if len(unique_ids) > delivery["retouchLimit"]:
        return jsonify({
            "message": f"选片数量超出精修上限，最多可选 {delivery['retouchLimit']} 张",
            "limit": delivery["retouchLimit"],
            "selected": len(unique_ids),
        }), 400

    for photo in delivery["photos"]:
        photo["selected"] = photo["id"] in unique_ids

    selection = {"code": code, "photoIds": unique_ids, "count": len(unique_ids)}
    SELECTIONS.insert(0, selection)
    return jsonify({"message": "选片已保存", "selection": selection})
