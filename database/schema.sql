-- Flight Ticket Purchasing System - veritabanı şeması
-- Önce schema.sql, sonra seed.sql çalıştırılır.

-- Windows'ta Türkçe karakter sorunu olmaması için
SET client_encoding = 'UTF8';

-- Script tekrar çalıştırılabilsin diye önce eski nesneler silinir
DROP VIEW  IF EXISTS v_flight_search CASCADE;
DROP TABLE IF EXISTS bookings CASCADE;
DROP TABLE IF EXISTS flight_seats CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS flights CASCADE;
DROP TABLE IF EXISTS airports CASCADE;
DROP FUNCTION IF EXISTS set_updated_at() CASCADE;

-- Havalimanları (koordinatlar harita için)
CREATE TABLE airports (
    id          SERIAL PRIMARY KEY,
    iata_code   VARCHAR(3)   UNIQUE NOT NULL CHECK (iata_code ~ '^[A-Z]{3}$'), -- IST, ESB
    name        VARCHAR(150) NOT NULL,
    city        VARCHAR(100) NOT NULL,
    country     VARCHAR(100) NOT NULL DEFAULT 'Türkiye',
    latitude    DECIMAL(9, 6) NOT NULL CHECK (latitude  BETWEEN -90  AND 90),
    longitude   DECIMAL(9, 6) NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    created_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Uçuşlar
CREATE TABLE flights (
    id                    SERIAL PRIMARY KEY,
    flight_number         VARCHAR(15) NOT NULL,                 -- TK-2124
    departure_airport_id  INT NOT NULL REFERENCES airports(id) ON DELETE RESTRICT,
    arrival_airport_id    INT NOT NULL REFERENCES airports(id) ON DELETE RESTRICT,
    departure_time        TIMESTAMP NOT NULL,                   -- havalimanı yerel saati
    arrival_time          TIMESTAMP NOT NULL,
    base_price            DECIMAL(10, 2) NOT NULL CHECK (base_price >= 0),
    total_seats           INT NOT NULL DEFAULT 36 CHECK (total_seats > 0),
    status                VARCHAR(20) NOT NULL DEFAULT 'SCHEDULED'
        CHECK (status IN ('SCHEDULED', 'DELAYED', 'CANCELLED', 'COMPLETED')),
    created_at            TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_different_airports CHECK (departure_airport_id <> arrival_airport_id),
    CONSTRAINT chk_valid_flight_times CHECK (arrival_time > departure_time),
    CONSTRAINT uq_flight_number_time  UNIQUE (flight_number, departure_time)
);

-- Kalkış + varış + tarih aramaları için
CREATE INDEX idx_flights_search
    ON flights (departure_airport_id, arrival_airport_id, departure_time);

-- Uçuş koltukları
-- Seçilen koltuk ödeme bitene kadar LOCKED tutulur.
-- Aynı anda seçimlerde version kolonu ile optimistic locking yapılır.
CREATE TABLE flight_seats (
    id                 SERIAL PRIMARY KEY,
    flight_id          INT NOT NULL REFERENCES flights(id) ON DELETE CASCADE,
    seat_number        VARCHAR(5) NOT NULL,                     -- 1A, 10F
    seat_class         VARCHAR(20) NOT NULL DEFAULT 'ECONOMY'
        CHECK (seat_class IN ('BUSINESS', 'ECONOMY')),
    price_multiplier   DECIMAL(4, 2) NOT NULL DEFAULT 1.00 CHECK (price_multiplier > 0),
    status             VARCHAR(15) NOT NULL DEFAULT 'AVAILABLE'
        CHECK (status IN ('AVAILABLE', 'LOCKED', 'BOOKED')),
    locked_by_session  VARCHAR(100) NULL,                       -- koltuğu tutan oturum
    locked_until       TIMESTAMPTZ NULL,                        -- bu saatten sonra kilit geçersiz
    version            INT NOT NULL DEFAULT 1,                  -- her güncellemede artırılır
    updated_at         TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_flight_seat UNIQUE (flight_id, seat_number),
    -- bookings'teki (seat_id, flight_id) FK'si için
    CONSTRAINT uq_seat_flight UNIQUE (id, flight_id),
    -- LOCKED ise kilit bilgileri dolu, diğer durumlarda boş olmalı
    CONSTRAINT chk_lock_fields CHECK (
        (status = 'LOCKED' AND locked_by_session IS NOT NULL AND locked_until IS NOT NULL)
        OR
        (status IN ('AVAILABLE', 'BOOKED') AND locked_by_session IS NULL AND locked_until IS NULL)
    )
);

CREATE INDEX idx_flight_seats_flight_status ON flight_seats (flight_id, status);

-- Kullanıcılar
-- Şifre düz tutulmaz, backend bcrypt hash'ini yazar.
CREATE TABLE users (
    id             SERIAL PRIMARY KEY,
    first_name     VARCHAR(100) NOT NULL,
    last_name      VARCHAR(100) NOT NULL,
    email          VARCHAR(150) NOT NULL CHECK (email ~ '^[^@\s]+@[^@\s]+\.[^@\s]+$'),
    password_hash  VARCHAR(255) NOT NULL,                       -- bcrypt
    phone          VARCHAR(30)  NULL,
    role           VARCHAR(10)  NOT NULL DEFAULT 'USER'
        CHECK (role IN ('USER', 'ADMIN')),
    created_at     TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- E-posta büyük/küçük harf fark etmeksizin tekil
CREATE UNIQUE INDEX uq_users_email ON users (LOWER(email));

-- Biletler
-- user_id bileti alan hesap, passenger_* alanları uçacak kişi.
CREATE TABLE bookings (
    id                         SERIAL PRIMARY KEY,
    pnr_code                   VARCHAR(6) UNIQUE NOT NULL CHECK (pnr_code ~ '^[A-Z0-9]{6}$'),
    user_id                    INT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    flight_id                  INT NOT NULL,
    seat_id                    INT NOT NULL,
    passenger_first_name       VARCHAR(100) NOT NULL,
    passenger_last_name        VARCHAR(100) NOT NULL,
    passenger_identity_number  VARCHAR(20)  NOT NULL,           -- TC kimlik veya pasaport no
    passenger_email            VARCHAR(150) NOT NULL,
    passenger_phone            VARCHAR(30)  NOT NULL,
    total_price                DECIMAL(10, 2) NOT NULL CHECK (total_price >= 0),
    booking_status             VARCHAR(20) NOT NULL DEFAULT 'CONFIRMED'
        CHECK (booking_status IN ('CONFIRMED', 'CANCELLED')),
    created_at                 TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    -- koltuk, biletteki uçuşa ait olmak zorunda
    CONSTRAINT fk_booking_seat_flight FOREIGN KEY (seat_id, flight_id)
        REFERENCES flight_seats (id, flight_id) ON DELETE RESTRICT
);

-- Bir koltukta tek aktif bilet olabilir; iptal edilen koltuk tekrar satılabilir
CREATE UNIQUE INDEX uq_active_booking_per_seat
    ON bookings (seat_id) WHERE booking_status = 'CONFIRMED';

CREATE INDEX idx_bookings_flight ON bookings (flight_id);
CREATE INDEX idx_bookings_user   ON bookings (user_id);

-- updated_at'i otomatik günceller
CREATE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_flight_seats_updated_at
    BEFORE UPDATE ON flight_seats
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Uçuş arama view'ı: havalimanı bilgileri ve boş koltuk sayısıyla birlikte.
-- Süresi geçmiş kilitler boş sayılır.
CREATE VIEW v_flight_search AS
SELECT
    f.id                AS flight_id,
    f.flight_number,
    f.departure_time,
    f.arrival_time,
    f.base_price,
    f.status,
    da.iata_code        AS departure_code,
    da.city             AS departure_city,
    da.name             AS departure_airport,
    da.latitude         AS departure_lat,
    da.longitude        AS departure_lng,
    aa.iata_code        AS arrival_code,
    aa.city             AS arrival_city,
    aa.name             AS arrival_airport,
    aa.latitude         AS arrival_lat,
    aa.longitude        AS arrival_lng,
    (SELECT COUNT(*) FROM flight_seats s
      WHERE s.flight_id = f.id
        AND (s.status = 'AVAILABLE'
             OR (s.status = 'LOCKED' AND s.locked_until < CURRENT_TIMESTAMP))
    )::INT              AS available_seats
FROM flights f
JOIN airports da ON da.id = f.departure_airport_id
JOIN airports aa ON aa.id = f.arrival_airport_id;
