-- Test verileri (schema.sql'den sonra çalıştırılır)

SET client_encoding = 'UTF8';

-- Havalimanları
INSERT INTO airports (iata_code, name, city, country, latitude, longitude) VALUES
('IST', 'İstanbul Havalimanı',        'İstanbul',  'Türkiye', 41.275278, 28.751944),
('SAW', 'Sabiha Gökçen Havalimanı',   'İstanbul',  'Türkiye', 40.898611, 29.309167),
('ESB', 'Esenboğa Havalimanı',        'Ankara',    'Türkiye', 40.128056, 32.995000),
('ADB', 'Adnan Menderes Havalimanı',  'İzmir',     'Türkiye', 38.292500, 27.156944),
('AYT', 'Antalya Havalimanı',         'Antalya',   'Türkiye', 36.898611, 30.800556),
('TZX', 'Trabzon Havalimanı',         'Trabzon',   'Türkiye', 40.995278, 39.789722),
('DLM', 'Dalaman Havalimanı',         'Muğla',     'Türkiye', 36.713056, 28.792500),
('GZT', 'Gaziantep Havalimanı',       'Gaziantep', 'Türkiye', 36.947222, 37.478889),
('ADA', 'Adana Şakirpaşa Havalimanı', 'Adana',     'Türkiye', 36.982222, 35.280278);

-- Uçuşlar
INSERT INTO flights (flight_number, departure_airport_id, arrival_airport_id,
                     departure_time, arrival_time, base_price, total_seats)
SELECT v.flight_number, da.id, aa.id, v.dep::TIMESTAMP, v.arr::TIMESTAMP, v.price, 36
FROM (VALUES
    ('TK-2101', 'IST', 'ESB', '2026-11-15 08:30', '2026-11-15 09:45', 1450.00),
    ('TK-2105', 'IST', 'ESB', '2026-11-15 18:00', '2026-11-15 19:15', 1650.00),
    ('TK-2102', 'ESB', 'IST', '2026-11-17 10:00', '2026-11-17 11:15', 1500.00),
    ('PC-1820', 'SAW', 'ADB', '2026-11-15 10:00', '2026-11-15 11:10', 1200.00),
    ('TK-2410', 'IST', 'AYT', '2026-11-15 12:15', '2026-11-15 13:40', 1800.00),
    ('TK-2830', 'ESB', 'TZX', '2026-11-16 09:00', '2026-11-16 10:25', 1550.00),
    ('PC-2012', 'ADB', 'AYT', '2026-11-16 14:30', '2026-11-16 15:35', 1350.00),
    ('TK-2470', 'IST', 'ADA', '2026-11-16 07:45', '2026-11-16 09:25', 1700.00),
    ('PC-2471', 'SAW', 'GZT', '2026-11-16 16:20', '2026-11-16 18:05', 1600.00),
    ('TK-2560', 'IST', 'DLM', '2026-11-17 13:10', '2026-11-17 14:25', 1400.00)
) AS v(flight_number, dep_code, arr_code, dep, arr, price)
JOIN airports da ON da.iata_code = v.dep_code
JOIN airports aa ON aa.iata_code = v.arr_code
ORDER BY v.dep::TIMESTAMP, v.flight_number;

-- Her uçuş için 6x6 koltuk, ilk 2 sıra business
INSERT INTO flight_seats (flight_id, seat_number, seat_class, price_multiplier, status)
SELECT
    f.id,
    r.row_num || s.seat_letter,
    CASE WHEN r.row_num <= 2 THEN 'BUSINESS' ELSE 'ECONOMY' END,
    CASE WHEN r.row_num <= 2 THEN 1.50 ELSE 1.00 END,
    'AVAILABLE'
FROM flights f
CROSS JOIN generate_series(1, 6) AS r(row_num)
CROSS JOIN (VALUES ('A'), ('B'), ('C'), ('D'), ('E'), ('F')) AS s(seat_letter)
ORDER BY f.id, r.row_num, s.seat_letter;

-- Test kullanıcıları
-- ahmet.yilmaz@example.com / Test1234!
-- admin@team19.com / Admin1234!
INSERT INTO users (first_name, last_name, email, password_hash, phone, role) VALUES
('Ahmet', 'Yılmaz', 'ahmet.yilmaz@example.com',
 '$2a$10$/r74B23fWnhBNX3dky0NHuDvdJ6HmaXKd6Etf0003Xihfg4ovJoBa', '+905551112233', 'USER'),
('Admin', 'Team19', 'admin@team19.com',
 '$2a$10$/0287sqSzfIacI6lFHJvveFoNoFzxy.d4QhbYdrKok5ZmM0xWgrX2', NULL, 'ADMIN');

-- Örnek bilet: TK19AB, TK-2101 1A
UPDATE flight_seats fs
SET status = 'BOOKED', version = version + 1
FROM flights f
WHERE fs.flight_id = f.id AND f.flight_number = 'TK-2101'
  AND f.departure_time = '2026-11-15 08:30' AND fs.seat_number = '1A';

INSERT INTO bookings (pnr_code, user_id, flight_id, seat_id,
                      passenger_first_name, passenger_last_name, passenger_identity_number,
                      passenger_email, passenger_phone, total_price, booking_status)
SELECT 'TK19AB', u.id, f.id, fs.id,
       'Ahmet', 'Yılmaz', '12345678901',
       'ahmet.yilmaz@example.com', '+905551112233',
       f.base_price * fs.price_multiplier, 'CONFIRMED'
FROM flights f
JOIN flight_seats fs ON fs.flight_id = f.id
JOIN users u ON u.email = 'ahmet.yilmaz@example.com'
WHERE f.flight_number = 'TK-2101' AND f.departure_time = '2026-11-15 08:30'
  AND fs.seat_number = '1A';
