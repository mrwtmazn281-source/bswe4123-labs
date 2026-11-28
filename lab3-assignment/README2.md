# Lab Assignment 3: The Exam Scheduler Service (`bswe4123`)

This project implements the **Exam Scheduler Service** using FastAPI and `httpx`, integrated with a **Room Booking Service** running on a separate port.

## Architecture & Services
- `room_booking.py`: Room Booking Service running on `http://127.0.0.1:8001` (supports `BOOKING_DELAY_SECONDS`).
- `scheduler.py`: Exam Scheduler Service running on `http://127.0.0.1:8002` with `GET /config` and `POST /exams`.

## Environment Variables
- `ROOM_BOOKING_URL` (default: `http://127.0.0.1:8001`)
- `REQUEST_TIMEOUT` (default: `2.0`)
- `MAX_RETRIES` (default: `3`)
- `BOOKING_DELAY_SECONDS` (default: `0`)

## Running the Services

### 1. Install dependencies
```bash
pip install fastapi uvicorn httpx
