export const mockAirports = [
  { id: 1, name: 'İstanbul Havalimanı', code: 'IST', city: 'İstanbul', latitude: 41.2753, longitude: 28.7519 },
  { id: 2, name: 'Sabiha Gökçen Havalimanı', code: 'SAW', city: 'İstanbul', latitude: 40.8986, longitude: 29.3092 },
  { id: 3, name: 'Esenboğa Havalimanı', code: 'ESB', city: 'Ankara', latitude: 40.1281, longitude: 32.9951 },
  { id: 4, name: 'Adnan Menderes Havalimanı', code: 'ADB', city: 'İzmir', latitude: 38.2924, longitude: 27.1570 },
  { id: 5, name: 'Antalya Havalimanı', code: 'AYT', city: 'Antalya', latitude: 36.8987, longitude: 30.8005 }
];

export const mockFlights = [
  {
    id: 1,
    flight_number: 'TK101',
    origin_airport_id: 1,
    destination_airport_id: 3,
    departure_time: '2026-11-15T10:00:00',
    arrival_time: '2026-11-15T11:15:00',
    price: 1250.00,
    available_seats: 40,
    occupied_seats: ['1A', '1B', '3C', '4D', '5F']
  },
  {
    id: 2,
    flight_number: 'TK102',
    origin_airport_id: 1,
    destination_airport_id: 4,
    departure_time: '2026-11-15T14:30:00',
    arrival_time: '2026-11-15T15:45:00',
    price: 1400.00,
    available_seats: 38,
    occupied_seats: ['2A', '2B', '2C', '6A']
  },
  {
    id: 3,
    flight_number: 'TK103',
    origin_airport_id: 1,
    destination_airport_id: 5,
    departure_time: '2026-11-16T09:00:00',
    arrival_time: '2026-11-16T10:20:00',
    price: 1650.00,
    available_seats: 45,
    occupied_seats: ['1C', '3A', '7B']
  },
  {
    id: 4,
    flight_number: 'TK104',
    origin_airport_id: 3,
    destination_airport_id: 4,
    departure_time: '2026-11-16T18:00:00',
    arrival_time: '2026-11-16T19:15:00',
    price: 1180.00,
    available_seats: 50,
    occupied_seats: ['4A', '4B']
  },
  {
    id: 5,
    flight_number: 'TK105',
    origin_airport_id: 2,
    destination_airport_id: 5,
    departure_time: '2026-11-17T12:00:00',
    arrival_time: '2026-11-17T13:20:00',
    price: 1350.00,
    available_seats: 42,
    occupied_seats: ['2F', '5D']
  }
];