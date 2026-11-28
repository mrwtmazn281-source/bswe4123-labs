import os
import time
from fastapi import FastAPI

app = FastAPI()
START_TIME = time.monotonic()
DELAY_SECONDS = float(os.getenv("DELAY_SECONDS", "0"))


@app.get("/health")
def health():
    if DELAY_SECONDS > 0:
        time.sleep(DELAY_SECONDS)

    uptime_seconds = round(time.monotonic() - START_TIME, 2)
    return {
        "status": "ok",
        "uptime_seconds": uptime_seconds,
    }