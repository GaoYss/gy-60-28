from flask import Blueprint, jsonify, request

from ..data import BOOKINGS, PACKAGES, PHOTOGRAPHERS, RESCHEDULE_REQUESTS, create_booking, create_reschedule_request

bookings_bp = Blueprint("bookings", __name__)

REQUIRED_FIELDS = ["clientName", "phone", "packageId", "photographerId", "date", "time"]
RESCHEDULE_REQUIRED_FIELDS = ["newDate", "newTime"]


@bookings_bp.get("")
def list_bookings():
    return jsonify(BOOKINGS)


@bookings_bp.post("")
def submit_booking():
    payload = request.get_json(silent=True) or {}
    missing = [field for field in REQUIRED_FIELDS if not payload.get(field)]
    if missing:
        return jsonify({"message": "缺少必填字段", "fields": missing}), 400

    if not any(item["id"] == payload["packageId"] for item in PACKAGES):
        return jsonify({"message": "套餐不存在"}), 404

    photographer = next((item for item in PHOTOGRAPHERS if item["id"] == payload["photographerId"]), None)
    if photographer is None:
        return jsonify({"message": "摄影师不存在"}), 404

    available_slots = photographer["slots"].get(payload["date"], [])
    if payload["time"] not in available_slots:
        return jsonify({"message": "该时间不可预约，请重新选择档期"}), 409

    booking = create_booking(payload)
    return jsonify(booking), 201


@bookings_bp.post("/<booking_id>/reschedule")
def submit_reschedule(booking_id):
    payload = request.get_json(silent=True) or {}
    missing = [field for field in RESCHEDULE_REQUIRED_FIELDS if not payload.get(field)]
    if missing:
        return jsonify({"message": "缺少必填字段", "fields": missing}), 400

    booking = next((b for b in BOOKINGS if b["id"] == booking_id), None)
    if not booking:
        return jsonify({"message": "预约不存在"}), 404

    if booking["status"] == "已取消":
        return jsonify({"message": "已取消的预约无法改期"}), 400

    photographer = next((item for item in PHOTOGRAPHERS if item["id"] == booking["photographerId"]), None)
    if photographer is None:
        return jsonify({"message": "摄影师不存在"}), 404

    available_slots = photographer["slots"].get(payload["newDate"], [])
    if payload["newTime"] not in available_slots:
        return jsonify({"message": "新档期时间不可预约，请重新选择"}), 409

    pending_request = next(
        (r for r in RESCHEDULE_REQUESTS if r["bookingId"] == booking_id and r["status"] == "待确认"),
        None,
    )
    if pending_request:
        return jsonify({"message": "已有待确认的改期申请，请等待处理"}), 409

    request_data, error = create_reschedule_request(booking_id, payload)
    if error:
        return jsonify({"message": error}), 400

    booking["status"] = "改期中"
    return jsonify({"request": request_data, "booking": booking}), 201


@bookings_bp.get("/reschedules")
def list_reschedules():
    return jsonify(RESCHEDULE_REQUESTS)


@bookings_bp.put("/reschedules/<request_id>/confirm")
def confirm_reschedule(request_id):
    reschedule_req = next((r for r in RESCHEDULE_REQUESTS if r["id"] == request_id), None)
    if not reschedule_req:
        return jsonify({"message": "改期申请不存在"}), 404

    if reschedule_req["status"] != "待确认":
        return jsonify({"message": "该改期申请已处理"}), 400

    booking = next((b for b in BOOKINGS if b["id"] == reschedule_req["bookingId"]), None)
    if not booking:
        return jsonify({"message": "关联预约不存在"}), 404

    photographer = next((item for item in PHOTOGRAPHERS if item["id"] == booking["photographerId"]), None)
    if photographer is None:
        return jsonify({"message": "摄影师不存在"}), 404

    available_slots = photographer["slots"].get(reschedule_req["newDate"], [])
    if reschedule_req["newTime"] not in available_slots:
        return jsonify({"message": "新档期已被占用，请重新申请改期"}), 409

    booking["rescheduleHistory"].append({
        "fromDate": reschedule_req["oldDate"],
        "fromTime": reschedule_req["oldTime"],
        "toDate": reschedule_req["newDate"],
        "toTime": reschedule_req["newTime"],
        "confirmedAt": __import__("datetime").date.today().isoformat(),
    })
    booking["date"] = reschedule_req["newDate"]
    booking["time"] = reschedule_req["newTime"]
    booking["status"] = "待确认"

    reschedule_req["status"] = "已确认"
    return jsonify({"request": reschedule_req, "booking": booking})


@bookings_bp.put("/reschedules/<request_id>/reject")
def reject_reschedule(request_id):
    payload = request.get_json(silent=True) or {}
    reschedule_req = next((r for r in RESCHEDULE_REQUESTS if r["id"] == request_id), None)
    if not reschedule_req:
        return jsonify({"message": "改期申请不存在"}), 404

    if reschedule_req["status"] != "待确认":
        return jsonify({"message": "该改期申请已处理"}), 400

    booking = next((b for b in BOOKINGS if b["id"] == reschedule_req["bookingId"]), None)
    if not booking:
        return jsonify({"message": "关联预约不存在"}), 404

    reschedule_req["status"] = "已拒绝"
    reschedule_req["rejectReason"] = payload.get("reason", "")
    booking["status"] = "待确认"

    return jsonify({"request": reschedule_req, "booking": booking})
