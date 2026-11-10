import { useState } from 'react';
import { Armchair, CheckCircle2 } from 'lucide-react';

export default function SeatSelection({ flight, onSeatSelect }) {
  const [selectedSeat, setSelectedSeat] = useState(null);

  const rows = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
  const seatsLeft = ['A', 'B', 'C'];
  const seatsRight = ['D', 'E', 'F'];

  const handleSeatClick = (seatNo) => {
    if (flight.occupied_seats.includes(seatNo)) return;
    setSelectedSeat(seatNo);
    onSeatSelect(seatNo);
  };

  return (
    <div style={{ background: '#ffffff', padding: '32px', borderRadius: '24px', boxShadow: '0 20px 40px rgba(0,0,0,0.04)', marginTop: '32px', border: '1px solid #e2e8f0' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
        <Armchair color="#2563eb" size={22} />
        <h3 style={{ margin: 0, color: '#0f172a', fontSize: '18px', fontWeight: '700' }}>Koltuk Seçimi</h3>
      </div>
      <p style={{ color: '#64748b', fontSize: '14px', margin: '0 0 24px 0' }}>Uçuş Kodu: <strong>{flight.flight_number}</strong> — Tercih ettiğiniz koltuğu işaretleyin.</p>
      
      {/* Koltuk Durum Açıklamaları */}
      <div style={{ display: 'flex', gap: '24px', marginBottom: '32px', background: '#f8fafc', padding: '14px 24px', borderRadius: '12px', width: 'fit-content', border: '1px solid #f1f5f9' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: '#475569', fontWeight: '500' }}>
          <div style={{ width: '16px', height: '16px', background: '#10b981', borderRadius: '4px' }}></div> Müsait
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: '#475569', fontWeight: '500' }}>
          <div style={{ width: '16px', height: '16px', background: '#ef4444', borderRadius: '4px' }}></div> Dolu
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: '#475569', fontWeight: '500' }}>
          <div style={{ width: '16px', height: '16px', background: '#2563eb', borderRadius: '4px' }}></div> Seçtiğiniz
        </div>
      </div>

      {/* Uçak Gövdesi Tasarımı */}
      <div style={{ display: 'flex', justifyContent: 'center' }}>
        <div style={{ background: '#f8fafc', padding: '36px 24px 24px 24px', borderRadius: '80px 80px 24px 24px', border: '2px solid #e2e8f0' }}>
          <div style={{ textAlign: 'center', fontSize: '11px', fontWeight: '700', color: '#94a3b8', marginBottom: '20px', letterSpacing: '2px' }}>KABİN ÖN BÖLÜMÜ</div>
          
          {rows.map(row => (
            <div key={row} style={{ display: 'flex', gap: '10px', marginBottom: '10px', alignItems: 'center' }}>
              <span style={{ width: '24px', textAlign: 'center', fontWeight: '600', fontSize: '12px', color: '#94a3b8' }}>{row}</span>
              
              {/* Sol Taraf */}
              {seatsLeft.map(letter => {
                const seatNo = `${row}${letter}`;
                const isOccupied = flight.occupied_seats.includes(seatNo);
                const isSelected = selectedSeat === seatNo;

                let bg = '#10b981';
                if (isOccupied) bg = '#cbd5e1'; // Dolu koltuklar daha yumuşak gri yapıldı
                if (isSelected) bg = '#2563eb';

                return (
                  <button
                    key={seatNo}
                    disabled={isOccupied}
                    onClick={() => handleSeatClick(seatNo)}
                    style={{
                      width: '40px',
                      height: '40px',
                      background: bg,
                      color: 'white',
                      border: 'none',
                      borderRadius: '10px',
                      cursor: isOccupied ? 'not-allowed' : 'pointer',
                      fontWeight: '600',
                      fontSize: '13px',
                      transition: 'all 0.2s ease'
                    }}
                  >
                    {letter}
                  </button>
                );
              })}

              <div style={{ width: '32px', textAlign: 'center', fontSize: '10px', color: '#cbd5e1' }}>│ │</div>

              {/* Sağ Taraf */}
              {seatsRight.map(letter => {
                const seatNo = `${row}${letter}`;
                const isOccupied = flight.occupied_seats.includes(seatNo);
                const isSelected = selectedSeat === seatNo;

                let bg = '#10b981';
                if (isOccupied) bg = '#cbd5e1';
                if (isSelected) bg = '#2563eb';

                return (
                  <button
                    key={seatNo}
                    disabled={isOccupied}
                    onClick={() => handleSeatClick(seatNo)}
                    style={{
                      width: '40px',
                      height: '40px',
                      background: bg,
                      color: 'white',
                      border: 'none',
                      borderRadius: '10px',
                      cursor: isOccupied ? 'not-allowed' : 'pointer',
                      fontWeight: '600',
                      fontSize: '13px',
                      transition: 'all 0.2s ease'
                    }}
                  >
                    {letter}
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      </div>

      {selectedSeat && (
        <div style={{ marginTop: '24px', padding: '14px 20px', background: '#eff6ff', borderRadius: '12px', border: '1px solid #bfdbfe', display: 'flex', alignItems: 'center', gap: '10px', color: '#1e40af', width: 'fit-content' }}>
          <CheckCircle2 size={18} />
          <span style={{ fontSize: '14px' }}>Seçilen Koltuk: <strong>{selectedSeat}</strong></span>
        </div>
      )}
    </div>
  );
}