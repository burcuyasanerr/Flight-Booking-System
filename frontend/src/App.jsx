import { useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import { mockAirports, mockFlights } from './mock';

export default function App() {
  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [hasSearched, setHasSearched] = useState(false);

  // Uçuş Arama Fonksiyonu
  const handleSearch = (e) => {
    e.preventDefault();
    setHasSearched(true);

    const filtered = mockFlights.filter(flight => {
      const originAirport = mockAirports.find(a => a.id === flight.origin_airport_id);
      const destAirport = mockAirports.find(a => a.id === flight.destination_airport_id);

      const matchesOrigin = !origin || originAirport?.code === origin;
      const matchesDest = !destination || destAirport?.code === destination;

      return matchesOrigin && matchesDest;
    });

    setSearchResults(filtered);
  };

  return (
    <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif', maxWidth: '1200px', margin: '0 auto' }}>
      <h1>✈️ Uçuş Rezervasyon Sistemi</h1>
      
      {/* 1. UÇUŞ ARAMA FORMU */}
      <div style={{ background: '#f4f4f9', padding: '20px', borderRadius: '8px', marginBottom: '20px' }}>
        <h3>Uçuş Ara</h3>
        <form onSubmit={handleSearch} style={{ display: 'flex', gap: '15px', alignItems: 'center', flexWrap: 'wrap' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '5px' }}>Kalkış Havalimanı:</label>
            <select value={origin} onChange={(e) => setOrigin(e.target.value)} style={{ padding: '8px', borderRadius: '4px' }}>
              <option value="">Tümü</option>
              {mockAirports.map(a => (
                <option key={a.id} value={a.code}>{a.city} - {a.name} ({a.code})</option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '5px' }}>Varış Havalimanı:</label>
            <select value={destination} onChange={(e) => setDestination(e.target.value)} style={{ padding: '8px', borderRadius: '4px' }}>
              <option value="">Tümü</option>
              {mockAirports.map(a => (
                <option key={a.id} value={a.code}>{a.city} - {a.name} ({a.code})</option>
              ))}
            </select>
          </div>

          <button type="submit" style={{ marginTop: '20px', padding: '10px 20px', background: '#007bff', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
            Uçuş Ara
          </button>
        </form>
      </div>

      {/* 2. UÇUŞ LİSTESİ SONUÇLARI */}
      {hasSearched && (
        <div style={{ marginBottom: '30px' }}>
          <h3>Arama Sonuçları</h3>
          {searchResults.length === 0 ? (
            <p>Uygun uçuş bulunamadı.</p>
          ) : (
            <div style={{ display: 'grid', gap: '10px' }}>
              {searchResults.map(flight => {
                const orig = mockAirports.find(a => a.id === flight.origin_airport_id);
                const dest = mockAirports.find(a => a.id === flight.destination_airport_id);
                return (
                  <div key={flight.id} style={{ border: '1px solid #ddd', padding: '15px', borderRadius: '6px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <strong>Uçuş No: {flight.flight_number}</strong>
                      <p style={{ margin: '5px 0' }}>{orig?.city} ({orig?.code}) ➔ {dest?.city} ({dest?.code})</p>
                      <small>Kalkış: {new Date(flight.departure_time).toLocaleString('tr-TR')}</small>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <span style={{ fontSize: '18px', fontWeight: 'bold', color: '#28a745' }}>{flight.price} TL</span>
                      <br />
                      <button style={{ marginTop: '5px', padding: '6px 12px', background: '#28a745', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
                        Koltuk Seç
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* 3. ETKİLEŞİMLİ HARİTA */}
      <div>
        <h3>Havalimanları Haritası</h3>
        <div style={{ height: '450px', width: '100%', borderRadius: '8px', overflow: 'hidden' }}>
          <MapContainer center={[39.0, 35.0]} zoom={6} style={{ height: '100%', width: '100%' }}>
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            />
            {mockAirports.map((airport) => (
              <Marker key={airport.id} position={[airport.latitude, airport.longitude]}>
                <Popup>
                  <strong>{airport.name} ({airport.code})</strong><br />
                  {airport.city}
                </Popup>
              </Marker>
            ))}
          </MapContainer>
        </div>
      </div>
    </div>
  );
}