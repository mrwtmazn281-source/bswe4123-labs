import time
from datetime import datetime
import httpx

SERVICES = {
    "svc-8001": "http://127.0.0.1:8001/health",
    "svc-8002": "http://127.0.0.1:8002/health",
    "svc-8003": "http://127.0.0.1:8003/health",
}

INTERVAL_SECONDS = 2.0
TIMEOUT_SECONDS = 1.0
SLOW_THRESHOLD_MS = 500.0
DOWN_AFTER_FAILURES = 3


def check_service(client: httpx.Client, url: str) -> tuple[str, float | None]:
    start = time.perf_counter()
    try:
        response = client.get(url, timeout=TIMEOUT_SECONDS)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        if response.status_code == 200:
            if elapsed_ms > SLOW_THRESHOLD_MS:
                return "SLOW", elapsed_ms
            return "UP", elapsed_ms

        return "FAIL", elapsed_ms
    except httpx.RequestError:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return "FAIL", elapsed_ms


def main() -> None:
    consecutive_failures = {name: 0 for name in SERVICES}

    print(
        f"Starting monitor | interval={INTERVAL_SECONDS}s | "
        f"timeout={TIMEOUT_SECONDS}s | slow>{SLOW_THRESHOLD_MS}ms | "
        f"down_after={DOWN_AFTER_FAILURES} consecutive failures"
    )

    with httpx.Client() as client:
        while True:
            round_start = time.monotonic()
            timestamp = datetime.now().strftime("%H:%M:%S")
            parts = []

            for name, url in SERVICES.items():
                raw_state, elapsed_ms = check_service(client, url)

                if raw_state in ("UP", "SLOW"):
                    consecutive_failures[name] = 0
                    parts.append(f"{name}: {raw_state} ({elapsed_ms:.1f}ms)")
                else:
                    consecutive_failures[name] += 1
                    if consecutive_failures[name] >= DOWN_AFTER_FAILURES:
                        parts.append(f"{name}: DOWN (fails={consecutive_failures[name]})")
                    else:
                        parts.append(f"{name}: RETRY ({consecutive_failures[name]}/{DOWN_AFTER_FAILURES})")

            print(f"[{timestamp}] " + " | ".join(parts))

            elapsed_round = time.monotonic() - round_start
            time.sleep(max(0.0, INTERVAL_SECONDS - elapsed_round))


if __name__ == "__main__":
    main()