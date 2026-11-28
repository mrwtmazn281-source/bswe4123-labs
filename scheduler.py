import asyncio
import os
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI(title="Exam Scheduler Service")


def get_room_booking_url() -> str:
    return os.getenv("ROOM_BOOKING_URL", "http://127.0.0.1:8001").rstrip("/")


def get_request_timeout() -> float:
    return float(os.getenv("REQUEST_TIMEOUT", "2.0"))


def get_max_retries() -> int:
    return int(os.getenv("MAX_RETRIES", "3"))


class ExamScheduleRequest(BaseModel):
    id: str = Field(..., min_length=1)
    course_code: str = Field(..., min_length=1)
    day: str = Field(..., min_length=1)
    start_hour: int = Field(..., ge=0, le=23)
    end_hour: int = Field(..., ge=1, le=24)
    students: int = Field(..., gt=0)


@app.get("/config")
def get_config() -> dict[str, Any]:
    return {
        "room_booking_url": get_room_booking_url(),
        "request_timeout": get_request_timeout(),
        "max_retries": get_max_retries(),
    }


async def request_with_retry(method: str, path: str, **kwargs: Any) -> httpx.Response:
    url = f"{get_room_booking_url()}{path}"
    timeout = get_request_timeout()
    max_retries = get_max_retries()
    backoff_delays = [0.5, 1.0, 2.0]

    attempt = 0
    while True:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(method, url, **kwargs)

            if response.status_code in (404, 409):
                return response

            if response.status_code >= 500:
                if attempt < max_retries:
                    delay = backoff_delays[attempt] if attempt < len(backoff_delays) else backoff_delays[-1]
                    print(f"[RETRY] {method} {path} returned {response.status_code}. Waiting {delay}s before retry {attempt + 1}/{max_retries}...")
                    attempt += 1
                    await asyncio.sleep(delay)
                    continue
                return response

            return response

        except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as exc:
            if attempt < max_retries:
                delay = backoff_delays[attempt] if attempt < len(backoff_delays) else backoff_delays[-1]
                print(f"[RETRY] {method} {path} failed ({type(exc).__name__}). Waiting {delay}s before retry {attempt + 1}/{max_retries}...")
                attempt += 1
                await asyncio.sleep(delay)
                continue
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Room Booking Service unreachable after {max_retries} retries",
            ) from exc


@app.post("/exams", status_code=status.HTTP_201_CREATED)
async def schedule_exam(exam: ExamScheduleRequest) -> dict[str, Any]:
    if exam.end_hour <= exam.start_hour:
        raise HTTPException(status_code=422, detail="end_hour must be greater than start_hour")

    try:
        rooms_resp = await request_with_retry("GET", "/rooms")
    except HTTPException:
        raise

    if rooms_resp.status_code >= 500:
        raise HTTPException(status_code=503, detail="Room Booking Service unavailable")
    if rooms_resp.status_code != 200:
        raise HTTPException(status_code=503, detail="Failed to retrieve rooms")

    rooms: list[dict[str, Any]] = rooms_resp.json()
    candidate_rooms = sorted(
        [r for r in rooms if int(r.get("capacity", 0)) >= exam.students],
        key=lambda r: int(r.get("capacity", 0)),
    )

    if not candidate_rooms:
        raise HTTPException(status_code=409, detail="No free room large enough for the exam")

    booking_id = f"exam-{exam.id}"
    booked_any_conflict = False

    for room in candidate_rooms:
        room_id = room["id"]
        payload = {
            "room_id": room_id,
            "day": exam.day,
            "start_hour": exam.start_hour,
            "end_hour": exam.end_hour,
            "purpose": f"Exam {exam.id} ({exam.course_code})",
        }
        try:
            book_resp = await request_with_retry("PUT", f"/bookings/{booking_id}", json=payload)
        except HTTPException:
            raise

        if book_resp.status_code in (200, 201):
            return {
                "exam_id": exam.id,
                "course_code": exam.course_code,
                "day": exam.day,
                "start_hour": exam.start_hour,
                "end_hour": exam.end_hour,
                "students": exam.students,
                "booked_room": room,
                "booking": book_resp.json(),
            }

        if book_resp.status_code == 409:
            booked_any_conflict = True
            continue

        if book_resp.status_code >= 500:
            raise HTTPException(status_code=503, detail="Room Booking Service error during booking")

        raise HTTPException(status_code=503, detail=f"Unexpected booking response: {book_resp.status_code}")

    if booked_any_conflict:
        raise HTTPException(status_code=409, detail="No free room large enough available at the requested time")

    raise HTTPException(status_code=409, detail="Unable to schedule exam")
