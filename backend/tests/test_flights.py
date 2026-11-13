FLIGHT_KEYS = {
    "flight_id", "flight_number", "departure_time", "arrival_time", "base_price", "status",
    "departure_code", "departure_city", "departure_airport", "departure_lat", "departure_lng",
    "arrival_code", "arrival_city", "arrival_airport", "arrival_lat", "arrival_lng", "available_seats",
}


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": True}


def test_airports(client):
    response = client.get("/api/airports")
    assert response.status_code == 200
    airports = response.json()
    assert len(airports) == 9
    assert set(airports[0]) == {"id", "iata_code", "name", "city", "latitude", "longitude"}
    ist = next(a for a in airports if a["iata_code"] == "IST")
    assert ist["city"] == "İstanbul"
    assert ist["latitude"] == 41.275278 and ist["longitude"] == 28.751944


def test_search_flights_by_route_and_date(client):
    response = client.get("/api/flights", params={"from": "IST", "to": "ESB", "date": "2026-11-15"})
    assert response.status_code == 200
    flights = response.json()
    assert [f["flight_number"] for f in flights] == ["TK-2101", "TK-2105"]  # kalkış saatine göre sıralı
    assert set(flights[0]) == FLIGHT_KEYS
    assert flights[0]["departure_time"] == "2026-11-15T08:30:00"
    assert flights[0]["base_price"] == 1450.0
    assert flights[0]["available_seats"] == 35  # 1A satılmış


def test_search_is_case_insensitive_and_filters_optional(client):
    assert len(client.get("/api/flights", params={"from": "ist", "to": "esb"}).json()) == 2
    assert len(client.get("/api/flights").json()) == 10
    assert client.get("/api/flights", params={"date": "2026-12-01"}).json() == []


def test_search_validation(client):
    assert client.get("/api/flights", params={"from": "ISTX"}).status_code == 422
    assert client.get("/api/flights", params={"date": "15-11-2026"}).status_code == 422
    same = client.get("/api/flights", params={"from": "IST", "to": "ist"})
    assert same.status_code == 422
    assert same.json()["detail"]["code"] == "SAME_AIRPORT"


def test_get_flight(client):
    response = client.get("/api/flights/1")
    assert response.status_code == 200
    assert response.json()["flight_number"] == "TK-2101"

    missing = client.get("/api/flights/9999")
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "FLIGHT_NOT_FOUND"


def test_flight_seats(client):
    response = client.get("/api/flights/1/seats")
    assert response.status_code == 200
    seats = response.json()
    assert len(seats) == 36
    assert [s["seat_number"] for s in seats[:7]] == ["1A", "1B", "1C", "1D", "1E", "1F", "2A"]
    assert set(seats[0]) == {"id", "seat_number", "seat_class", "price_multiplier", "status", "version"}

    by_number = {s["seat_number"]: s for s in seats}
    assert by_number["1A"]["status"] == "BOOKED"
    assert by_number["2F"]["seat_class"] == "BUSINESS" and by_number["2F"]["price_multiplier"] == 1.5
    assert by_number["3A"]["seat_class"] == "ECONOMY" and by_number["3A"]["price_multiplier"] == 1.0
    assert "locked_by_session" not in seats[0]

    assert client.get("/api/flights/9999/seats").status_code == 404


def test_validation_errors_use_common_format(client):
    response = client.get("/api/flights", params={"from": "ISTX"})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "VALIDATION_ERROR"
    assert "from" in detail["message"]
    assert detail["errors"][0]["field"] == "from"

    missing_body = client.post("/api/seats/1/lock", json={}).json()["detail"]
    assert missing_body["code"] == "VALIDATION_ERROR"
    assert missing_body["errors"][0]["field"] == "session_id"


def test_cancelled_flights_are_listed_with_status(client, fresh_db):
    """İptal edilen uçuşlar aramada 'CANCELLED' durumuyla gelir; arayüz 'İptal' rozetiyle gösterir."""
    from backend.services import db_manager

    with db_manager.get_cursor() as cursor:
        cursor.execute("UPDATE flights SET status = 'CANCELLED' WHERE flight_number = 'TK-2105';")

    flights = client.get("/api/flights", params={"from": "IST", "to": "ESB", "date": "2026-11-15"}).json()
    assert {f["flight_number"]: f["status"] for f in flights} == {"TK-2101": "SCHEDULED", "TK-2105": "CANCELLED"}
