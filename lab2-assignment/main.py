from datetime import date
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field, model_validator

app = FastAPI(title="Campus Room Booking Service")


class RoomCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1, max_length=32, examples=["B205"])
    building: str = Field(..., min_length=1, max_length=100, examples=["Engineering Building"])
    capacity: int = Field(..., gt=0, le=1000, examples=[30])


class Room(RoomCreate):
    pass


class BookingPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    room_id: str = Field(..., min_length=1, max_length=32, examples=["B205"])
    day: date = Field(..., examples=["2026-12-01"])
    start_hour: int = Field(..., ge=8, le=20, examples=[10])
    end_hour: int = Field(..., ge=8, le=20, examples=[12])
    purpose: str = Field(..., min_length=1, max_length=200, examples=["Study group"])

    @model_validator(mode="after")
    def validate_hours(self) -> "BookingPayload":
        if self.end_hour <= self.start_hour:
            raise ValueError("end_hour must be greater than start_hour")
        return self


class Booking(BookingPayload):
    id: str


rooms_db: Dict[str, Room] = {}
bookings_db: Dict[str, Booking] = {}


def _overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return a_start < b_end and a_end > b_start


@app.post("/rooms", response_model=Room, status_code=status.HTTP_201_CREATED)
def create_room(room: RoomCreate) -> Room:
    if room.id in rooms_db:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Room '{room.id}' already exists",
        )
    created = Room(**room.model_dump())
    rooms_db[created.id] = created
    return created


@app.get("/rooms", response_model=List[Room], status_code=status.HTTP_200_OK)
def list_rooms() -> List[Room]:
    return list(rooms_db.values())


@app.put("/bookings/{booking_id}", response_model=Booking)
def upsert_booking(
    booking_id: str,
    payload: BookingPayload,
    response: Response,
) -> Booking:
    if payload.room_id not in rooms_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room '{payload.room_id}' not found",
        )

    existing_same_id = bookings_db.get(booking_id)
    if existing_same_id is not None:
        if (
            existing_same_id.room_id == payload.room_id
            and existing_same_id.day == payload.day
            and existing_same_id.start_hour == payload.start_hour
            and existing_same_id.end_hour == payload.end_hour
            and existing_same_id.purpose == payload.purpose
        ):
            response.status_code = status.HTTP_200_OK
            return existing_same_id
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Booking ID '{booking_id}' already exists with different details",
        )

    for existing in bookings_db.values():
        if existing.room_id == payload.room_id and existing.day == payload.day:
            if _overlaps(
                payload.start_hour,
                payload.end_hour,
                existing.start_hour,
                existing.end_hour,
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Booking overlaps with existing booking '{existing.id}' "
                        f"({existing.start_hour}:00-{existing.end_hour}:00)"
                    ),
                )

    created = Booking(id=booking_id, **payload.model_dump())
    bookings_db[booking_id] = created
    response.status_code = status.HTTP_201_CREATED
    return created


@app.get("/bookings", response_model=List[Booking], status_code=status.HTTP_200_OK)
def list_bookings(
    room_id: Optional[str] = Query(default=None),
    day: Optional[date] = Query(default=None),
) -> List[Booking]:
    results = list(bookings_db.values())
    if room_id is not None:
        results = [b for b in results if b.room_id == room_id]
    if day is not None:
        results = [b for b in results if b.day == day]
    return results


@app.get("/bookings/{booking_id}", response_model=Booking, status_code=status.HTTP_200_OK)
def get_booking(booking_id: str) -> Booking:
    booking = bookings_db.get(booking_id)
    if booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking '{booking_id}' not found",
        )
    return booking


@app.delete("/bookings/{booking_id}", status_code=status.HTTP_200_OK)
def delete_booking(booking_id: str) -> dict:
    if booking_id not in bookings_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking '{booking_id}' not found",
        )
    del bookings_db[booking_id]
    return {"deleted": booking_id}