def test_booking_by_pnr(client):
    response = client.get("/api/bookings/pnr/TK19AB")
    assert response.status_code == 200
    booking = response.json()
    assert booking["pnr_code"] == "TK19AB"
    assert booking["booking_status"] == "CONFIRMED"
    assert booking["passenger_last_name"] == "Yılmaz"
    assert booking["flight_number"] == "TK-2101"
    assert booking["seat_number"] == "1A" and booking["seat_class"] == "BUSINESS"
    assert booking["total_price"] == 2175.0
    # Kişisel bilgiler cevapta olmamalı
    assert not {"passenger_identity_number", "passenger_email", "passenger_phone"} & set(booking)


def test_booking_lookup_variants(client):
    assert client.get("/api/bookings/pnr/tk19ab").status_code == 200
    for last_name in ("Yılmaz", "YILMAZ", "yılmaz", " Yılmaz "):
        assert client.get("/api/bookings/pnr/TK19AB", params={"last_name": last_name}).status_code == 200, last_name

    wrong_name = client.get("/api/bookings/pnr/TK19AB", params={"last_name": "Kaya"})
    assert wrong_name.status_code == 404
    assert wrong_name.json()["detail"]["code"] == "BOOKING_NOT_FOUND"
    assert client.get("/api/bookings/pnr/ZZZZZZ").status_code == 404
    assert client.get("/api/bookings/pnr/ABC").status_code == 422


def test_ticket_pdf(client):
    response = client.get("/api/bookings/pnr/TK19AB/pdf", params={"last_name": "Yılmaz"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == 'attachment; filename="bilet_TK19AB.pdf"'
    assert response.content.startswith(b"%PDF")

    assert client.get("/api/bookings/pnr/TK19AB/pdf", params={"last_name": "Kaya"}).status_code == 404
    assert client.get("/api/bookings/pnr/ZZZZZZ/pdf").status_code == 404


def test_cors_allows_vite_dev_server(client):
    response = client.options(
        "/api/airports",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
