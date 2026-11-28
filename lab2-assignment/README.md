# Lab Assignment 2: Campus Room Booking Service

## 1. API Design

| Operation | Method | URI | Request Body | Success Code | Error Codes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Create a room | `POST` | `/rooms` | `{"id": "B205", "building": "Engineering", "capacity": 30}` | `201 Created` | `409 Conflict`, `422 Unprocessable Entity` |
| List all rooms | `GET` | `/rooms` | None | `200 OK` | None |
| Create/upsert booking by client ID | `PUT` | `/bookings/{booking_id}` | `{"room_id": "B205", "day": "2026-12-01", "start_hour": 10, "end_hour": 12, "purpose": "Study group"}` | `201 Created` (new) / `200 OK` (retry) | `404 Not Found`, `409 Conflict`, `422 Unprocessable Entity` |
| List bookings | `GET` | `/bookings` | None (optional query: `room_id`, `day`) | `200 OK` | `422 Unprocessable Entity` |
| Get booking by ID | `GET` | `/bookings/{booking_id}` | None | `200 OK` | `404 Not Found` |
| Cancel booking | `DELETE` | `/bookings/{booking_id}` | None | `200 OK` | `404 Not Found` |

## 2. Safe-to-Retry Booking Creation Design

Booking creation uses `PUT /bookings/{booking_id}` where the client generates and supplies a unique `booking_id` (such as `bk-101`).

- If the first request succeeds on the server but the HTTP response is lost due to a network drop, the client can safely retry the exact same `PUT /bookings/bk-101` request with the same payload.
- The server checks whether `bk-101` already exists with identical booking fields. If it matches, no second booking is created and no false conflict error is raised; instead, the existing booking is returned with `200 OK`.
- If a different payload is sent for an already-used `booking_id`, the server returns `409 Conflict`.
- Overlap prevention checks bookings for the same `room_id` and `day` using `start_hour < existing.end_hour and end_hour > existing.start_hour`, so back-to-back slots like `10` to `12` and `12` to `13` are allowed while overlapping intervals return `409 Conflict`.

## 3. Client Script Output (`test_bookings.py`)

```text
[Create room B205] -> Status: 201 | Body: {'id': 'B205', 'building': 'Engineering', 'capacity': 30}
[Duplicate room B205] -> Status: 409 | Body: {'detail': "Room 'B205' already exists"}
[Invalid hours (end < start)] -> Status: 422 | Body: {'detail': [{'type': 'value_error', 'loc': ['body'], 'msg': 'Value error, end_hour must be greater than start_hour', 'input': {'room_id': 'B205', 'day': '2026-12-01', 'start_hour': 14, 'end_hour': 12, 'purpose': 'Invalid time range'}, 'ctx': {'error': {}}}]}
[Out of operating hours (7 to 9)] -> Status: 422 | Body: {'detail': [{'type': 'greater_than_equal', 'loc': ['body', 'start_hour'], 'msg': 'Input should be greater than or equal to 8', 'input': 7, 'ctx': {'ge': 8}}]}
[Booking unknown room X999] -> Status: 404 | Body: {'detail': "Room 'X999' not found"}
[Create booking bk-101 (1st attempt)] -> Status: 201 | Body: {'room_id': 'B205', 'day': '2026-12-01', 'start_hour': 10, 'end_hour': 12, 'purpose': 'Algorithms study group', 'id': 'bk-101'}
[Retry same booking bk-101 (2nd attempt)] -> Status: 200 | Body: {'room_id': 'B205', 'day': '2026-12-01', 'start_hour': 10, 'end_hour': 12, 'purpose': 'Algorithms study group', 'id': 'bk-101'}
[Adjacent non-overlapping booking bk-102 (12 to 13)] -> Status: 201 | Body: {'room_id': 'B205', 'day': '2026-12-01', 'start_hour': 12, 'end_hour': 13, 'purpose': 'Follow-up session', 'id': 'bk-102'}
[Overlapping booking bk-103 (11 to 13)] -> Status: 409 | Body: {'detail': "Booking overlaps with existing booking 'bk-101' (10:00-12:00)"}
[Get booking bk-101] -> Status: 200 | Body: {'room_id': 'B205', 'day': '2026-12-01', 'start_hour': 10, 'end_hour': 12, 'purpose': 'Algorithms study group', 'id': 'bk-101'}
[List bookings for B205 on 2026-12-01] -> Status: 200 | Body: [{'room_id': 'B205', 'day': '2026-12-01', 'start_hour': 10, 'end_hour': 12, 'purpose': 'Algorithms study group', 'id': 'bk-101'}, {'room_id': 'B205', 'day': '2026-12-01', 'start_hour': 12, 'end_hour': 13, 'purpose': 'Follow-up session', 'id': 'bk-102'}]
[Delete booking bk-102] -> Status: 200 | Body: {'deleted': 'bk-102'}
[Get deleted booking bk-102] -> Status: 404 | Body: {'detail': "Booking 'bk-102' not found"}

```