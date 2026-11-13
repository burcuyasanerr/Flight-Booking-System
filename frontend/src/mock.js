export const mockAirports = [
  { id: 1, iata_code: 'IST', name: 'İstanbul Havalimanı', city: 'İstanbul', latitude: 41.275278, longitude: 28.751944 },
  { id: 2, iata_code: 'SAW', name: 'Sabiha Gökçen Havalimanı', city: 'İstanbul', latitude: 40.898611, longitude: 29.309167 },
  { id: 3, iata_code: 'ESB', name: 'Esenboğa Havalimanı', city: 'Ankara', latitude: 40.128056, longitude: 32.995000 },
  { id: 4, iata_code: 'ADB', name: 'Adnan Menderes Havalimanı', city: 'İzmir', latitude: 38.292500, longitude: 27.156944 },
  { id: 5, iata_code: 'AYT', name: 'Antalya Havalimanı', city: 'Antalya', latitude: 36.898611, longitude: 30.800556 },
  { id: 6, iata_code: 'TZX', name: 'Trabzon Havalimanı', city: 'Trabzon', latitude: 40.995278, longitude: 39.789722 },
  { id: 7, iata_code: 'DLM', name: 'Dalaman Havalimanı', city: 'Muğla', latitude: 36.713056, longitude: 28.792500 },
  { id: 8, iata_code: 'GZT', name: 'Gaziantep Havalimanı', city: 'Gaziantep', latitude: 36.947222, longitude: 37.478889 },
  { id: 9, iata_code: 'ADA', name: 'Adana Şakirpaşa Havalimanı', city: 'Adana', latitude: 36.982222, longitude: 35.280278 }
];

// Her uçuş için 36 koltuk (1A-6F) üretir: 1-2. sıra BUSINESS (1.5x), 3-6. sıra ECONOMY (1.0x)
const createSeatsForFlight = (bookedSeats = [], lockedSeats = []) => {
  const rows = [1, 2, 3, 4, 5, 6];
  const letters = ['A', 'B', 'C', 'D', 'E', 'F'];
  const seats = [];
  let id = 1;

  for (const row of rows) {
    for (const letter of letters) {
      const seat_number = `${row}${letter}`;
      const isBusiness = row <= 2;
      let status = 'AVAILABLE';
      if (bookedSeats.includes(seat_number)) status = 'BOOKED';
      else if (lockedSeats.includes(seat_number)) status = 'LOCKED';

      seats.push({
        id: id++,
        seat_number,
        seat_class: isBusiness ? 'BUSINESS' : 'ECONOMY',
        price_multiplier: isBusiness ? 1.5 : 1.0,
        status
      });
    }
  }
  return seats;
};

export const mockFlights = [
  {
    flight_id: 1,
    flight_number: 'TK-2101',
    departure_time: '2026-11-15T08:30:00',
    arrival_time: '2026-11-15T09:45:00',
    base_price: 1450.00,
    status: 'SCHEDULED',
    departure_code: 'IST',
    departure_city: 'İstanbul',
    departure_airport: 'İstanbul Havalimanı',
    departure_lat: 41.275278,
    departure_lng: 28.751944,
    arrival_code: 'ESB',
    arrival_city: 'Ankara',
    arrival_airport: 'Esenboğa Havalimanı',
    arrival_lat: 40.128056,
    arrival_lng: 32.995000,
    available_seats: 35,
    seats: createSeatsForFlight(['1A'], [])
  },
  {
    flight_id: 2,
    flight_number: 'PC-1820',
    departure_time: '2026-11-15T10:00:00',
    arrival_time: '2026-11-15T11:10:00',
    base_price: 1200.00,
    status: 'SCHEDULED',
    departure_code: 'SAW',
    departure_city: 'İstanbul',
    departure_airport: 'Sabiha Gökçen Havalimanı',
    departure_lat: 40.898611,
    departure_lng: 29.309167,
    arrival_code: 'ADB',
    arrival_city: 'İzmir',
    arrival_airport: 'Adnan Menderes Havalimanı',
    arrival_lat: 38.292500,
    arrival_lng: 27.156944,
    available_seats: 36,
    seats: createSeatsForFlight([], [])
  },
  {
    flight_id: 3,
    flight_number: 'TK-2410',
    departure_time: '2026-11-15T12:15:00',
    arrival_time: '2026-11-15T13:40:00',
    base_price: 1800.00,
    status: 'SCHEDULED',
    departure_code: 'IST',
    departure_city: 'İstanbul',
    departure_airport: 'İstanbul Havalimanı',
    departure_lat: 41.275278,
    departure_lng: 28.751944,
    arrival_code: 'AYT',
    arrival_city: 'Antalya',
    arrival_airport: 'Antalya Havalimanı',
    arrival_lat: 36.898611,
    arrival_lng: 30.800556,
    available_seats: 36,
    seats: createSeatsForFlight([], [])
  },
  {
    flight_id: 4,
    flight_number: 'TK-2105',
    departure_time: '2026-11-15T18:00:00',
    arrival_time: '2026-11-15T19:15:00',
    base_price: 1650.00,
    status: 'SCHEDULED',
    departure_code: 'IST',
    departure_city: 'İstanbul',
    departure_airport: 'İstanbul Havalimanı',
    departure_lat: 41.275278,
    departure_lng: 28.751944,
    arrival_code: 'ESB',
    arrival_city: 'Ankara',
    arrival_airport: 'Esenboğa Havalimanı',
    arrival_lat: 40.128056,
    arrival_lng: 32.995000,
    available_seats: 36,
    seats: createSeatsForFlight([], [])
  },
  {
    flight_id: 5,
    flight_number: 'TK-2470',
    departure_time: '2026-11-16T07:45:00',
    arrival_time: '2026-11-16T09:25:00',
    base_price: 1700.00,
    status: 'SCHEDULED',
    departure_code: 'IST',
    departure_city: 'İstanbul',
    departure_airport: 'İstanbul Havalimanı',
    departure_lat: 41.275278,
    departure_lng: 28.751944,
    arrival_code: 'ADA',
    arrival_city: 'Adana',
    arrival_airport: 'Adana Şakirpaşa Havalimanı',
    arrival_lat: 36.982222,
    arrival_lng: 35.280278,
    available_seats: 36,
    seats: createSeatsForFlight([], [])
  },
  {
    flight_id: 6,
    flight_number: 'TK-2830',
    departure_time: '2026-11-16T09:00:00',
    arrival_time: '2026-11-16T10:25:00',
    base_price: 1550.00,
    status: 'SCHEDULED',
    departure_code: 'ESB',
    departure_city: 'Ankara',
    departure_airport: 'Esenboğa Havalimanı',
    departure_lat: 40.128056,
    departure_lng: 32.995000,
    arrival_code: 'TZX',
    arrival_city: 'Trabzon',
    arrival_airport: 'Trabzon Havalimanı',
    arrival_lat: 40.995278,
    arrival_lng: 39.789722,
    available_seats: 36,
    seats: createSeatsForFlight([], [])
  },
  {
    flight_id: 7,
    flight_number: 'PC-2012',
    departure_time: '2026-11-16T14:30:00',
    arrival_time: '2026-11-16T15:35:00',
    base_price: 1350.00,
    status: 'SCHEDULED',
    departure_code: 'ADB',
    departure_city: 'İzmir',
    departure_airport: 'Adnan Menderes Havalimanı',
    departure_lat: 38.292500,
    departure_lng: 27.156944,
    arrival_code: 'AYT',
    arrival_city: 'Antalya',
    arrival_airport: 'Antalya Havalimanı',
    arrival_lat: 36.898611,
    arrival_lng: 30.800556,
    available_seats: 36,
    seats: createSeatsForFlight([], [])
  },
  {
    flight_id: 8,
    flight_number: 'PC-2471',
    departure_time: '2026-11-16T16:20:00',
    arrival_time: '2026-11-16T18:05:00',
    base_price: 1600.00,
    status: 'SCHEDULED',
    departure_code: 'SAW',
    departure_city: 'İstanbul',
    departure_airport: 'Sabiha Gökçen Havalimanı',
    departure_lat: 40.898611,
    departure_lng: 29.309167,
    arrival_code: 'GZT',
    arrival_city: 'Gaziantep',
    arrival_airport: 'Gaziantep Havalimanı',
    arrival_lat: 36.947222,
    arrival_lng: 37.478889,
    available_seats: 36,
    seats: createSeatsForFlight([], [])
  },
  {
    flight_id: 9,
    flight_number: 'TK-2102',
    departure_time: '2026-11-17T10:00:00',
    arrival_time: '2026-11-17T11:15:00',
    base_price: 1500.00,
    status: 'SCHEDULED',
    departure_code: 'ESB',
    departure_city: 'Ankara',
    departure_airport: 'Esenboğa Havalimanı',
    departure_lat: 40.128056,
    departure_lng: 32.995000,
    arrival_code: 'IST',
    arrival_city: 'İstanbul',
    arrival_airport: 'İstanbul Havalimanı',
    arrival_lat: 41.275278,
    arrival_lng: 28.751944,
    available_seats: 36,
    seats: createSeatsForFlight([], [])
  },
  {
    flight_id: 10,
    flight_number: 'TK-2560',
    departure_time: '2026-11-17T13:10:00',
    arrival_time: '2026-11-17T14:25:00',
    base_price: 1400.00,
    status: 'SCHEDULED',
    departure_code: 'IST',
    departure_city: 'İstanbul',
    departure_airport: 'İstanbul Havalimanı',
    departure_lat: 41.275278,
    departure_lng: 28.751944,
    arrival_code: 'DLM',
    arrival_city: 'Muğla',
    arrival_airport: 'Dalaman Havalimanı',
    arrival_lat: 36.713056,
    arrival_lng: 28.792500,
    available_seats: 36,
    seats: createSeatsForFlight([], [])
  }
];