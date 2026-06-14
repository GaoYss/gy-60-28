import pytest

from app import create_app
from app.data import BOOKINGS, DELIVERIES, SELECTIONS


@pytest.fixture
def app():
    app = create_app()
    app.config.update({"TESTING": True})
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def reset_state():
    original_bookings = list(BOOKINGS)
    original_deliveries = []
    for d in DELIVERIES:
        photos_copy = []
        for p in d["photos"]:
            photos_copy.append(dict(p))
        d_copy = dict(d)
        d_copy["photos"] = photos_copy
        original_deliveries.append(d_copy)
    original_selections = list(SELECTIONS)

    yield

    BOOKINGS.clear()
    BOOKINGS.extend(original_bookings)

    DELIVERIES.clear()
    for d in original_deliveries:
        DELIVERIES.append(d)

    SELECTIONS.clear()
    SELECTIONS.extend(original_selections)


class TestBookingSlotOccupancy:
    def test_booking_same_slot_should_be_rejected(self, client):
        payload = {
            "clientName": "张三",
            "phone": "13800138000",
            "packageId": "portrait-classic",
            "photographerId": "lin",
            "date": "2026-06-03",
            "time": "10:00",
            "notes": "第一次预约",
        }
        response = client.post("/api/bookings", json=payload)
        assert response.status_code == 201
        assert len(BOOKINGS) == 1

        payload2 = dict(payload)
        payload2["clientName"] = "李四"
        payload2["phone"] = "13900139000"
        payload2["notes"] = "重复档期测试"
        response2 = client.post("/api/bookings", json=payload2)
        assert response2.status_code == 409
        data = response2.get_json()
        assert "档期已被占用" in data["message"]
        assert len(BOOKINGS) == 1

    def test_booking_different_time_same_day_should_succeed(self, client):
        payload = {
            "clientName": "张三",
            "phone": "13800138000",
            "packageId": "portrait-classic",
            "photographerId": "lin",
            "date": "2026-06-03",
            "time": "10:00",
        }
        response = client.post("/api/bookings", json=payload)
        assert response.status_code == 201

        payload2 = dict(payload)
        payload2["clientName"] = "李四"
        payload2["phone"] = "13900139000"
        payload2["time"] = "14:00"
        response2 = client.post("/api/bookings", json=payload2)
        assert response2.status_code == 201
        assert len(BOOKINGS) == 2

    def test_cancelled_booking_slot_can_be_reused(self, client):
        payload = {
            "clientName": "张三",
            "phone": "13800138000",
            "packageId": "portrait-classic",
            "photographerId": "lin",
            "date": "2026-06-03",
            "time": "10:00",
        }
        response = client.post("/api/bookings", json=payload)
        booking_id = response.get_json()["id"]

        for b in BOOKINGS:
            if b["id"] == booking_id:
                b["status"] = "已取消"
                break

        payload2 = dict(payload)
        payload2["clientName"] = "李四"
        payload2["phone"] = "13900139000"
        response2 = client.post("/api/bookings", json=payload2)
        assert response2.status_code == 201
        assert len(BOOKINGS) == 2


class TestInvalidDeliveryCode:
    def test_get_delivery_with_invalid_code_returns_404(self, client):
        response = client.get("/api/deliveries/INVALID-CODE-123")
        assert response.status_code == 404
        data = response.get_json()
        assert "交付链接不存在" in data["message"]

    def test_save_selection_with_invalid_code_returns_404(self, client):
        response = client.post(
            "/api/selections",
            json={"code": "INVALID-CODE-123", "photoIds": ["p01", "p02"]},
        )
        assert response.status_code == 404
        data = response.get_json()
        assert "交付链接不存在" in data["message"]

    def test_get_delivery_with_valid_code_returns_data(self, client):
        response = client.get("/api/deliveries/STUDIO-2026-0618")
        assert response.status_code == 200
        data = response.get_json()
        assert data["code"] == "STUDIO-2026-0618"
        assert "photos" in data


class TestExceedSelectionLimit:
    def test_selecting_within_limit_succeeds(self, client):
        response = client.post(
            "/api/selections",
            json={"code": "STUDIO-2026-0618", "photoIds": ["p01", "p02", "p03"]},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["selection"]["count"] == 3
        assert data["selection"]["code"] == "STUDIO-2026-0618"

    def test_selecting_exactly_at_limit_succeeds(self, client):
        response = client.post(
            "/api/selections",
            json={"code": "STUDIO-2026-0618", "photoIds": ["p01", "p02", "p03", "p04", "p05", "p06"]},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["selection"]["count"] == 6

    def test_selecting_different_photos_over_limit_should_be_rejected(self, client):
        response = client.post(
            "/api/selections",
            json={
                "code": "STUDIO-2026-0618",
                "photoIds": ["p01", "p02", "p03", "p04", "p05", "p06", "p07"],
            },
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "超出精修上限" in data["message"]
        assert data["limit"] == 6
        assert data["selected"] == 7

    def test_duplicate_photo_ids_are_deduplicated(self, client):
        response = client.post(
            "/api/selections",
            json={
                "code": "STUDIO-2026-0618",
                "photoIds": ["p01", "p01", "p02", "p02", "p03"],
            },
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["selection"]["count"] == 3
        assert data["selection"]["photoIds"] == ["p01", "p02", "p03"]

    def test_duplicates_within_limit_do_not_trigger_overflow(self, client):
        response = client.post(
            "/api/selections",
            json={
                "code": "STUDIO-2026-0618",
                "photoIds": ["p01", "p02", "p03", "p04", "p05", "p06", "p01", "p02"],
            },
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["selection"]["count"] == 6

    def test_empty_selection_succeeds(self, client):
        response = client.post(
            "/api/selections",
            json={"code": "STUDIO-2026-0618", "photoIds": []},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["selection"]["count"] == 0


class TestSelectionSummaryUpdate:
    def test_delivery_list_summary_reflects_selected_count(self, client):
        list_before = client.get("/api/deliveries")
        summary_before = list_before.get_json()[0]
        initial_selected = summary_before["selectedCount"]

        client.post(
            "/api/selections",
            json={"code": "STUDIO-2026-0618", "photoIds": ["p01", "p03", "p04", "p05"]},
        )

        list_after = client.get("/api/deliveries")
        summary_after = list_after.get_json()[0]
        assert summary_after["selectedCount"] == 4
        assert summary_after["selectedCount"] != initial_selected
        assert summary_after["photoCount"] == 8

    def test_saving_selection_updates_photo_selected_flags(self, client):
        client.post(
            "/api/selections",
            json={"code": "STUDIO-2026-0618", "photoIds": ["p01", "p05"]},
        )

        response = client.get("/api/deliveries/STUDIO-2026-0618")
        delivery = response.get_json()
        selected_map = {p["id"]: p["selected"] for p in delivery["photos"]}
        assert selected_map["p01"] is True
        assert selected_map["p05"] is True
        assert selected_map["p02"] is False
        assert selected_map["p03"] is False

    def test_re_saving_with_different_photos_updates_summary(self, client):
        client.post(
            "/api/selections",
            json={"code": "STUDIO-2026-0618", "photoIds": ["p01", "p02", "p03"]},
        )
        list_mid = client.get("/api/deliveries")
        assert list_mid.get_json()[0]["selectedCount"] == 3

        client.post(
            "/api/selections",
            json={"code": "STUDIO-2026-0618", "photoIds": ["p04", "p05", "p06", "p07"]},
        )
        list_after = client.get("/api/deliveries")
        assert list_after.get_json()[0]["selectedCount"] == 4

    def test_re_saving_with_different_photos_updates_each_photo_state(self, client):
        client.post(
            "/api/selections",
            json={"code": "STUDIO-2026-0618", "photoIds": ["p01", "p02", "p03"]},
        )
        delivery_mid = client.get("/api/deliveries/STUDIO-2026-0618").get_json()
        selected_mid = {p["id"]: p["selected"] for p in delivery_mid["photos"]}
        assert selected_mid["p01"] is True
        assert selected_mid["p02"] is True
        assert selected_mid["p03"] is True
        assert selected_mid["p04"] is False
        assert selected_mid["p07"] is False

        client.post(
            "/api/selections",
            json={"code": "STUDIO-2026-0618", "photoIds": ["p04", "p05", "p07", "p08"]},
        )
        delivery_after = client.get("/api/deliveries/STUDIO-2026-0618").get_json()
        selected_after = {p["id"]: p["selected"] for p in delivery_after["photos"]}
        assert selected_after["p01"] is False
        assert selected_after["p02"] is False
        assert selected_after["p03"] is False
        assert selected_after["p04"] is True
        assert selected_after["p05"] is True
        assert selected_after["p07"] is True
        assert selected_after["p08"] is True

    def test_selection_record_is_persisted(self, client):
        before_count = len(SELECTIONS)
        client.post(
            "/api/selections",
            json={"code": "STUDIO-2026-0618", "photoIds": ["p02", "p06"]},
        )
        assert len(SELECTIONS) == before_count + 1
        assert SELECTIONS[0]["code"] == "STUDIO-2026-0618"
        assert SELECTIONS[0]["count"] == 2
