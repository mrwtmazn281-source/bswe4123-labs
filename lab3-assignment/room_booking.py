import os
import time
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

app = FastAPI(title="Campus Room Booking Service")

BOOKING_DELAY_SECONDS = float(os.getenv("BOOKING_DELAY_SECONDS", "0"))

rooms_db: dict[str, dict] = {}
bookings_db: dict[str, dict] = {}


class RoomCreate(BaseModel):
    id: str = Field(..., min_length=1)
    building: str = Field(..., min_length=1)
    capacity: int = Field(..., gt=0)


class BookingUpsert(BaseModel):
    room_id: str = Field(..., min_length=1)
    day: str = Field(..., min_length=1)
    start_hour: int = Field(..., ge=0, le=23)
    end_hour: int = Field(..., ge=1, le=24)
    purpose: str = Field(..., min_length=1)


def apply_delay() -> None:
    if BOOKING_DELAY_SECONDS > 0:
        time.sleep(BOOKING_DELAY_SECONDS)


def has_overlap(
    room_id: str,
    day: str,
    start_hour: int,
    end_hour: int,
    ignore_booking_id: Optional[str] = None,
) -> bool:
    for bid, b in bookings_db.items():
        if ignore_booking_id and bid == ignore_booking_id:
            continue
        if b["room_id"] == room_id and b["day"] == day:
            if start_hour < b["end_hour"] and end_hour > b["start_hour"]:
                return True
    return False


@app.post("/rooms", status_code=status.HTTP_201_CREATED)
def create_room(room: RoomCreate):
    apply_delay()
    if room.id in rooms_db:
        raise HTTPException(status_code=409, detail="Room already exists")
    data = room.model_dump()
    rooms_db[room.id] = data
    return data


@app.get("/rooms")
def list_rooms():
    apply_delay()
    return list(rooms_db.values())


@app.put("/bookings/{booking_id}")
def upsert_booking(booking_id: str, booking: BookingUpsert, response: Response):
    apply_delay()
    if booking.end_hour <= booking.start_hour:
        raise HTTPException(status_code=422, detail="end_hour must be greater than start_hour")
    if booking.room_id not in rooms_db:
        raise HTTPException(status_code=404, detail="Room not found")

    if booking_id in bookings_db:
        existing = bookings_db[booking_id]
        same_payload = (
            existing["room_id"] == booking.room_id
            and existing["day"] == booking.day
            and existing["start_hour"] == booking.start_hour
            and existing["end_hour"] == booking.end_hour
            and existing["purpose"] == booking.purpose
        )
        if same_payload:
            response.status_code = status.HTTP_200_OK
            return {"id": booking_id, **existing}
        if has_overlap(
            booking.room_id,
            booking.day,
            booking.start_hour,
            booking.end_hour,
            ignore_booking_id=booking_id,
        ):
            raise HTTPException(status_code=409, detail="Booking time overlaps with another booking")
        updated = {
            "room_id": booking.room_id,
            "day": booking.day,
            "start_hour": booking.start_hour,
            "end_hour": booking.end_hour,
            "purpose": booking.purpose,
        }
        bookings_db[booking_id] = updated
        response.status_code = status.HTTP_200_OK
        return {"id": booking_id, **updated}

    if has_overlap(booking.room_id, booking.day, booking.start_hour, booking.end_hour):
        raise HTTPException(status_code=409, detail="Room is already booked in this time slot")

    created = {
        "room_id": booking.room_id,
        "day": booking.day,
        "start_hour": booking.start_hour,
        "end_hour": booking.end_hour,
        "purpose": booking.purpose,
    }
    bookings_db[booking_id] = created
    response.status_code = status.HTTP_201_CREATED
    return {"id": booking_id, **created}


@app.get("/bookings")
def list_bookings(
    room_id: Optional[str] = Query(default=None),
    day: Optional[str] = Query(default=None),
):
    apply_delay()
    results = []
    for bid, b in bookings_db.items():
        if room_id and b["room_id"] != room_id:
            continue
        if day and b["day"] != day:
            continue
        results.append({"id": bid, **b})
    return results
