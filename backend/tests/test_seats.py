from concurrent.futures import ThreadPoolExecutor
import threading

import pytest


def seat_id(client, flight_id: int, seat_number: str) -> int:
    seats = client.get(f"/api/flights/{flight_id}/seats").json()
    return next(s["id"] for s in seats if s["seat_number"] == seat_number)


def seat_status(client, flight_id: int, seat_number: str) -> str:
    seats = client.get(f"/api/flights/{flight_id}/seats").json()
    return next(s["status"] for s in seats if s["seat_number"] == seat_number)


@pytest.mark.usefixtures("fresh_db")
def test_lock_and_release_flow(client):
    sid = seat_id(client, 1, "3C")

    locked = client.post(f"/api/seats/{sid}/lock", json={"session_id": "user-a"})
    assert locked.status_code == 200
    assert locked.json()["seat_id"] == sid and locked.json()["locked_until"]
    assert seat_status(client, 1, "3C") == "LOCKED"
    available_after_lock = client.get("/api/flights/1").json()["available_seats"]
    assert available_after_lock == 34

    other = client.post(f"/api/seats/{sid}/lock", json={"session_id": "user-b"})
    assert other.status_code == 409
    assert other.json()["detail"]["code"] == "LOCKED_BY_ANOTHER_USER"

    again = client.post(f"/api/seats/{sid}/lock", json={"session_id": "user-a"})
    assert again.status_code == 200, "aynı oturum kendi kilidini uzatabilmeli"

    not_owner = client.delete(f"/api/seats/{sid}/lock", params={"session_id": "user-b"})
    assert not_owner.status_code == 409
    assert not_owner.json()["detail"]["code"] == "LOCK_NOT_OWNED"

    released = client.delete(f"/api/seats/{sid}/lock", params={"session_id": "user-a"})
    assert released.status_code == 200
    assert seat_status(client, 1, "3C") == "AVAILABLE"


@pytest.mark.usefixtures("fresh_db")
def test_optimistic_lock_rejects_stale_version(client):
    seats = client.get("/api/flights/2/seats").json()
    seat = next(s for s in seats if s["seat_number"] == "4D")

    first = client.post(f"/api/seats/{seat['id']}/lock", json={"session_id": "user-a", "expected_version": seat["version"]})
    assert first.status_code == 200
    assert first.json()["version"] == seat["version"] + 1

    client.delete(f"/api/seats/{seat['id']}/lock", params={"session_id": "user-a"})
    stale = client.post(f"/api/seats/{seat['id']}/lock", json={"session_id": "user-b", "expected_version": seat["version"]})
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "VERSION_MISMATCH_RACE_CONDITION"


@pytest.mark.usefixtures("fresh_db")
def test_lock_errors(client):
    booked = client.post(f"/api/seats/{seat_id(client, 1, '1A')}/lock", json={"session_id": "user-a"})
    assert booked.status_code == 409
    assert booked.json()["detail"]["code"] == "ALREADY_BOOKED"

    missing = client.post("/api/seats/999999/lock", json={"session_id": "user-a"})
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "SEAT_NOT_FOUND"
    assert client.delete("/api/seats/999999/lock", params={"session_id": "user-a"}).status_code == 404

    assert client.post("/api/seats/1/lock", json={"session_id": ""}).status_code == 422
    assert client.post("/api/seats/1/lock", json={}).status_code == 422


@pytest.mark.usefixtures("fresh_db")
@pytest.mark.parametrize("use_version", [False, True], ids=["pessimistic", "optimistic"])
def test_only_one_of_concurrent_requests_wins(client, use_version):
    """10 kullanıcı aynı koltuğa aynı anda istek atar; yalnızca biri kazanmalı."""
    users = 10
    seat = next(s for s in client.get("/api/flights/3/seats").json() if s["seat_number"] == "5B")
    barrier = threading.Barrier(users)

    def attempt(i: int) -> int:
        body = {"session_id": f"user-{i}"}
        if use_version:
            body["expected_version"] = seat["version"]
        barrier.wait()
        return client.post(f"/api/seats/{seat['id']}/lock", json=body).status_code

    with ThreadPoolExecutor(max_workers=users) as pool:
        codes = list(pool.map(attempt, range(users)))

    assert codes.count(200) == 1
    assert codes.count(409) == users - 1
