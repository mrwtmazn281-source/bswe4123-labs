import httpx

BASE_URL = "http://127.0.0.1:8000"


def show(label: str, response: httpx.Response) -> None:
    print(f"[{label}] -> Status: {response.status_code} | Body: {response.json()}")


def main() -> None:
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        # 1. إنشاء غرفة بنجاح (201)
        r = client.post(
            "/rooms",
            json={"id": "B205", "building": "Engineering", "capacity": 30},
        )
        show("Create room B205", r)

        # 2. محاولة إنشاء نفس الغرفة مرة ثانية (409)
        r = client.post(
            "/rooms",
            json={"id": "B205", "building": "Engineering", "capacity": 30},
        )
        show("Duplicate room B205", r)

        # 3. بيانات غير صالحة: ساعة النهاية قبل ساعة البداية (422)
        r = client.put(
            "/bookings/bk-invalid-hours",
            json={
                "room_id": "B205",
                "day": "2026-12-01",
                "start_hour": 14,
                "end_hour": 12,
                "purpose": "Invalid time range",
            },
        )
        show("Invalid hours (end < start)", r)

        # 4. بيانات خارج ساعات العمل 8..20 (422)
        r = client.put(
            "/bookings/bk-out-of-range",
            json={
                "room_id": "B205",
                "day": "2026-12-01",
                "start_hour": 7,
                "end_hour": 9,
                "purpose": "Before 8:00",
            },
        )
        show("Out of operating hours (7 to 9)", r)

        # 5. حجز غرفة غير موجودة (404)
        r = client.put(
            "/bookings/bk-unknown-room",
            json={
                "room_id": "X999",
                "day": "2026-12-01",
                "start_hour": 10,
                "end_hour": 12,
                "purpose": "Unknown room",
            },
        )
        show("Booking unknown room X999", r)

        # 6. إنشاء حجز لأول مرة (201)
        payload_1 = {
            "room_id": "B205",
            "day": "2026-12-01",
            "start_hour": 10,
            "end_hour": 12,
            "purpose": "Algorithms study group",
        }
        r1 = client.put("/bookings/bk-101", json=payload_1)
        show("Create booking bk-101 (1st attempt)", r1)

        # 7. إعادة إرسال نفس الطلب بنفس المعرّف والبيانات (200 ولا ينشئ حجزاً ثانياً)
        r2 = client.put("/bookings/bk-101", json=payload_1)
        show("Retry same booking bk-101 (2nd attempt)", r2)

        # 8. حجز متتالٍ غير متداخل من 12 إلى 13 (201)
        r = client.put(
            "/bookings/bk-102",
            json={
                "room_id": "B205",
                "day": "2026-12-01",
                "start_hour": 12,
                "end_hour": 13,
                "purpose": "Follow-up session",
            },
        )
        show("Adjacent non-overlapping booking bk-102 (12 to 13)", r)

        # 9. حجز متداخل من 11 إلى 13 مع 10 إلى 12 (409)
        r = client.put(
            "/bookings/bk-103",
            json={
                "room_id": "B205",
                "day": "2026-12-01",
                "start_hour": 11,
                "end_hour": 13,
                "purpose": "Overlapping booking",
            },
        )
        show("Overlapping booking bk-103 (11 to 13)", r)

        # 10. قراءة حجز وعرض جميع الحجوزات (200)
        r = client.get("/bookings/bk-101")
        show("Get booking bk-101", r)

        r = client.get("/bookings", params={"room_id": "B205", "day": "2026-12-01"})
        show("List bookings for B205 on 2026-12-01", r)

        # 11. حذف حجز (200) ثم محاولة جلبه بعد الحذف (404)
        r = client.delete("/bookings/bk-102")
        show("Delete booking bk-102", r)

        r = client.get("/bookings/bk-102")
        show("Get deleted booking bk-102", r)


if __name__ == "__main__":
    main()
    