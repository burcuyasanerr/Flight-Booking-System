import { useState, useEffect } from 'react';
import { Armchair, CheckCircle2, Crown, Lock } from 'lucide-react';

export default function SeatSelection({ flight, onSeatSelect }) {
  const [selectedSeat, setSelectedSeat] = useState(null);

  // Uçuş değiştiğinde seçili koltuğu sıfırla
  useEffect(() => {
    setSelectedSeat(null);
  }, [flight?.flight_id]);

  const rows = [1, 2, 3, 4, 5, 6];
  const seatsLeft = ['A', 'B', 'C'];
  const seatsRight = ['D', 'E', 'F'];

  const seatsList = flight?.seats || [];

  const getSeatObj = (seatNo) => {
    return (
      seatsList.find((s) => s.seat_number === seatNo) || {
        id: 0,
        seat_number: seatNo,
        seat_class: Number(seatNo[0]) <= 2 ? 'BUSINESS' : 'ECONOMY',
        price_multiplier: Number(seatNo[0]) <= 2 ? 1.5 : 1.0,
        status: 'AVAILABLE'
      }
    );
  };

  const handleSeatClick = (seatObj) => {
    if (seatObj.status !== 'AVAILABLE') return;
    const calculatedPrice = Number((flight.base_price * seatObj.price_multiplier).toFixed(2));
    const enrichedSeat = { ...seatObj, calculatedPrice };
    setSelectedSeat(enrichedSeat);
    onSeatSelect(enrichedSeat);
  };

  const renderSeatButton = (row, letter) => {
    const seatNo = `${row}${letter}`;
    const seatObj = getSeatObj(seatNo);
    const isBooked = seatObj.status === 'BOOKED';
    const isLocked = seatObj.status === 'LOCKED';
    const isUnavailable = isBooked || isLocked;
    const isSelected = selectedSeat?.seat_number === seatNo;
    const isBusiness = seatObj.seat_class === 'BUSINESS';
    const seatPrice = (flight.base_price * seatObj.price_multiplier).toFixed(0);

    let bg = isBusiness ? '#f59e0b' : '#10b981';
    if (isBooked) bg = '#cbd5e1';
    if (isLocked) bg = '#fb923c';
    if (isSelected) bg = '#2563eb';

    return (
      <button
        key={seatNo}
        type="button"
        disabled={isUnavailable}
        onClick={() => handleSeatClick(seatObj)}
        title={`${seatNo} • ${isBusiness ? 'Business' : 'Economy'} (${seatPrice} TL) - ${seatObj.status}`}
        style={{
          width: '42px',
          height: '42px',
          background: bg,
          color: isBooked ? '#64748b' : 'white',
          border: isSelected ? '2px solid #1d4ed8' : 'none',
          borderRadius: '10px',
          cursor: isUnavailable ? 'not-allowed' : 'pointer',
          fontWeight: '700',
          fontSize: '13px',
          transition: 'all 0.2s ease',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          position: 'relative',
          opacity: isLocked ? 0.85 : 1
        }}
      >
        {isLocked ? <Lock size={14} /> : letter}
      </button>
    );
  };

  return (
    <div style={{ background: '#ffffff', padding: '32px', borderRadius: '24px', boxShadow: '0 20px 40px rgba(0,0,0,0.04)', marginTop: '32px', border: '1px solid #e2e8f0' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
        <Armchair color="#2563eb" size={22} />
        <h3 style={{ margin: 0, color: '#0f172a', fontSize: '18px', fontWeight: '700' }}>Koltuk Seçimi (36 Koltuk)</h3>
      </div>
      <p style={{ color: '#64748b', fontSize: '14px', margin: '0 0 24px 0' }}>
        Uçuş Kodu: <strong>{flight.flight_number}</strong> • Baz Fiyat: <strong>{flight.base_price} TL</strong> (Business 1.5x / Economy 1.0x)
      </p>
      
      {/* Koltuk Durum ve Sınıf Açıklamaları */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '20px', marginBottom: '32px', background: '#f8fafc', padding: '14px 24px', borderRadius: '12px', width: 'fit-content', border: '1px solid #f1f5f9' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: '#475569', fontWeight: '600' }}>
          <div style={{ width: '16px', height: '16px', background: '#f59e0b', borderRadius: '4px' }}></div> Business (1.5x)
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: '#475569', fontWeight: '600' }}>
          <div style={{ width: '16px', height: '16px', background: '#10b981', borderRadius: '4px' }}></div> Economy (1.0x)
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: '#475569', fontWeight: '600' }}>
          <div style={{ width: '16px', height: '16px', background: '#fb923c', borderRadius: '4px' }}></div> Kilitli (LOCKED)
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: '#475569', fontWeight: '600' }}>
          <div style={{ width: '16px', height: '16px', background: '#cbd5e1', borderRadius: '4px' }}></div> Dolu (BOOKED)
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: '#475569', fontWeight: '600' }}>
          <div style={{ width: '16px', height: '16px', background: '#2563eb', borderRadius: '4px' }}></div> Seçilen
        </div>
      </div>

      {/* Uçak Gövdesi Tasarımı (1A - 6F) */}
      <div style={{ display: 'flex', justifyContent: 'center' }}>
        <div style={{ background: '#f8fafc', padding: '36px 28px 28px 28px', borderRadius: '80px 80px 24px 24px', border: '2px solid #e2e8f0' }}>
          <div style={{ textAlign: 'center', fontSize: '11px', fontWeight: '700', color: '#94a3b8', marginBottom: '16px', letterSpacing: '2px' }}>KABİN ÖN BÖLÜMÜ</div>
          
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', fontSize: '11px', fontWeight: '800', color: '#d97706', marginBottom: '10px', backgroundColor: '#fef3c7', padding: '4px 10px', borderRadius: '8px' }}>
            <Crown size={13} /> BUSINESS CLASS (1.5x)
          </div>

          {rows.map(row => (
            <div key={row}>
              {row === 3 && (
                <div style={{ textAlign: 'center', fontSize: '11px', fontWeight: '800', color: '#059669', margin: '14px 0 10px 0', backgroundColor: '#d1fae5', padding: '4px 10px', borderRadius: '8px' }}>
                  ECONOMY CLASS (1.0x)
                </div>
              )}
              <div style={{ display: 'flex', gap: '10px', marginBottom: '10px', alignItems: 'center' }}>
                <span style={{ width: '24px', textAlign: 'center', fontWeight: '700', fontSize: '12px', color: '#64748b' }}>{row}</span>
                
                {/* Sol Taraf (A, B, C) */}
                {seatsLeft.map(letter => renderSeatButton(row, letter))}

                <div style={{ width: '28px', textAlign: 'center', fontSize: '10px', color: '#cbd5e1' }}>│ │</div>

                {/* Sağ Taraf (D, E, F) */}
                {seatsRight.map(letter => renderSeatButton(row, letter))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {selectedSeat && (
        <div style={{ marginTop: '24px', padding: '16px 22px', background: '#eff6ff', borderRadius: '14px', border: '1px solid #bfdbfe', display: 'flex', alignItems: 'center', gap: '12px', color: '#1e40af', width: 'fit-content', flexWrap: 'wrap' }}>
          <CheckCircle2 size={18} />
          <span style={{ fontSize: '14px' }}>
            Seçilen Koltuk: <strong>{selectedSeat.seat_number}</strong> ({selectedSeat.seat_class}) • Toplam Fiyat: <strong>{selectedSeat.calculatedPrice} TL</strong>
          </span>
        </div>
      )}
    </div>
  );
}