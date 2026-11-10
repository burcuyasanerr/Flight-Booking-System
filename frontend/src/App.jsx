import { useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet';
import { Plane, Search, Calendar, User, CheckCircle2, BookmarkCheck, PhoneCall, HelpCircle, Compass, ShieldCheck, Route, Star, Globe, Award, Users, ArrowRightLeft, MapPin, LogIn, X, Lock, Mail, UserCheck, LogOut } from 'lucide-react';
import { mockAirports, mockFlights } from './mock';
import SeatSelection from './SeatSelection';

export default function App() {
  const [activeTab, setActiveTab] = useState('search');
  const [tripType, setTripType] = useState('oneWay');
  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [selectedFlight, setSelectedFlight] = useState(null);
  const [chosenSeat, setChosenSeat] = useState('');
  
  // Yolcu Bilgileri
  const [passengerName, setPassengerName] = useState('');
  const [docType, setDocType] = useState('TC');
  const [passengerIdentity, setPassengerIdentity] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [bookingSummary, setBookingSummary] = useState(null);

  // PNR Sorgulama State
  const [searchPnr, setSearchPnr] = useState('');
  const [pnrResult, setPnrResult] = useState(null);

  // Auth / Modal State
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const [authTab, setAuthTab] = useState('login');
  const [authName, setAuthName] = useState('');
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authError, setAuthError] = useState('');
  const [user, setUser] = useState(null);

  const handleSearch = (e) => {
    e.preventDefault();
    setHasSearched(true);
    setSelectedFlight(null);
    setChosenSeat('');
    setBookingSummary(null);
    setErrorMessage('');

    const filtered = mockFlights.filter(flight => {
      const originAirport = mockAirports.find(a => a.id === flight.origin_airport_id);
      const destAirport = mockAirports.find(a => a.id === flight.destination_airport_id);

      const matchesOrigin = !origin || originAirport?.code === origin;
      const matchesDest = !destination || destAirport?.code === destination;

      return matchesOrigin && matchesDest;
    });

    setSearchResults(filtered);
  };

  const handleBookingSubmit = (e) => {
    e.preventDefault();
    setErrorMessage('');

    const nameTrimmed = passengerName.trim();
    const nameRegex = /^[a-zA-ZğüşıöçĞÜŞİÖÇ\s]+$/;
    const nameParts = nameTrimmed.split(/\s+/);

    if (!nameRegex.test(nameTrimmed) || nameParts.length < 2) {
      setErrorMessage('Lütfen geçerli bir Ad ve Soyad giriniz.');
      return;
    }

    if (docType === 'TC') {
      const tcRegex = /^[1-9][0-9]{10}$/;
      if (!tcRegex.test(passengerIdentity)) {
        setErrorMessage('T.C. Kimlik Numarası 11 haneli olmalı ve 0 ile başlamamalıdır.');
        return;
      }
    } else if (docType === 'PASSPORT') {
      const passportRegex = /^[A-Z0-9]{7,9}$/i;
      if (!passportRegex.test(passengerIdentity)) {
        setErrorMessage('Geçerli bir Pasaport Numarası giriniz (7-9 karakter).');
        return;
      }
    }

    const orig = mockAirports.find(a => a.id === selectedFlight.origin_airport_id);
    const dest = mockAirports.find(a => a.id === selectedFlight.destination_airport_id);

    setBookingSummary({
      passengerName: nameTrimmed,
      docType: docType === 'TC' ? 'T.C. Kimlik No' : 'Pasaport No',
      passengerIdentity,
      flightNumber: selectedFlight.flight_number,
      origin: `${orig?.city} (${orig?.code})`,
      destination: `${dest?.city} (${dest?.code})`,
      departureTime: selectedFlight.departure_time,
      seat: chosenSeat,
      price: selectedFlight.price,
      pnr: Math.random().toString(36).substring(2, 8).toUpperCase()
    });
  };

  const handlePnrSearch = (e) => {
    e.preventDefault();
    if (bookingSummary && bookingSummary.pnr === searchPnr.trim().toUpperCase()) {
      setPnrResult(bookingSummary);
    } else {
      setPnrResult('NOT_FOUND');
    }
  };

  const handleAuthSubmit = (e) => {
    e.preventDefault();
    setAuthError('');

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(authEmail)) {
      setAuthError('Lütfen geçerli bir e-posta adresi giriniz.');
      return;
    }

    if (authPassword.length < 6) {
      setAuthError('Şifreniz en az 6 karakter olmalıdır.');
      return;
    }

    if (authTab === 'register') {
      const nameTrimmed = authName.trim();
      const nameParts = nameTrimmed.split(/\s+/);
      if (nameParts.length < 2) {
        setAuthError('Lütfen ad ve soyadınızı eksiksiz giriniz.');
        return;
      }
      setUser({ name: nameTrimmed, email: authEmail });
    } else {
      setUser({ name: authEmail, email: authEmail });
    }

    setIsAuthOpen(false);
    setAuthEmail('');
    setAuthPassword('');
    setAuthName('');
    setAuthError('');
  };

  const flightRoutes = (hasSearched && searchResults.length > 0 ? searchResults : mockFlights).map(flight => {
    const orig = mockAirports.find(a => a.id === flight.origin_airport_id);
    const dest = mockAirports.find(a => a.id === flight.destination_airport_id);
    return {
      id: flight.id,
      number: flight.flight_number,
      positions: [
        [orig.latitude, orig.longitude],
        [dest.latitude, dest.longitude]
      ]
    };
  });

  return (
    <div style={{ backgroundColor: '#f8fafc', color: '#1e293b', minHeight: '100vh', width: '100%', margin: 0, padding: 0, fontFamily: 'Inter, system-ui, sans-serif' }}>
      
      {/* HEADER */}
      <header style={{ backgroundColor: '#0f172a', color: 'white', padding: '0 40px', height: '76px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.1)', position: 'sticky', top: 0, zIndex: 1000 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer' }} onClick={() => setActiveTab('search')}>
          <div style={{ backgroundColor: '#2563eb', padding: '10px', borderRadius: '12px', display: 'flex' }}>
            <Plane size={24} color="white" />
          </div>
          <div>
            <span style={{ fontSize: '20px', fontWeight: '800', color: 'white', display: 'block', lineHeight: '1' }}>SkyWings</span>
            <span style={{ fontSize: '10px', color: '#60a5fa', letterSpacing: '1.5px', fontWeight: '700' }}>AIRLINES</span>
          </div>
        </div>

        <nav style={{ display: 'flex', gap: '8px', height: '100%', alignItems: 'center' }}>
          {[
            { id: 'search', label: 'Uçuş Arama', icon: Search },
            { id: 'pnr', label: 'Rezervasyonlarım (PNR)', icon: BookmarkCheck },
            { id: 'checkin', label: 'Online Check-in', icon: CheckCircle2 },
            { id: 'support', label: 'Destek & İletişim', icon: PhoneCall },
          ].map(tab => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: isActive ? '#60a5fa' : '#cbd5e1',
                  padding: '0 16px',
                  height: '100%',
                  fontSize: '14px',
                  fontWeight: isActive ? '700' : '600',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  borderBottom: isActive ? '3px solid #60a5fa' : '3px solid transparent'
                }}
              >
                <Icon size={16} color={isActive ? '#60a5fa' : '#cbd5e1'} /> {tab.label}
              </button>
            );
          })}

          {/* KULLANICI ALANI */}
          {user ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginLeft: '12px', backgroundColor: 'rgba(255,255,255,0.06)', padding: '6px 14px', borderRadius: '14px', border: '1px solid rgba(255,255,255,0.1)' }}>
              <div style={{ backgroundColor: '#2563eb', padding: '6px', borderRadius: '50%', display: 'flex' }}>
                <UserCheck size={14} color="white" />
              </div>
              <span style={{ fontSize: '13px', fontWeight: '600', color: '#f8fafc' }}>
                {user.email}
              </span>
              <button
                onClick={() => setUser(null)}
                title="Çıkış Yap"
                style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: '4px', display: 'flex', marginLeft: '4px' }}
              >
                <LogOut size={16} />
              </button>
            </div>
          ) : (
            <button
              onClick={() => { setAuthError(''); setIsAuthOpen(true); }}
              style={{
                backgroundColor: '#2563eb',
                color: 'white',
                border: 'none',
                padding: '9px 18px',
                borderRadius: '12px',
                fontSize: '13px',
                fontWeight: '700',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                marginLeft: '12px',
                boxShadow: '0 4px 12px rgba(37,99,235,0.3)'
              }}
            >
              <LogIn size={15} /> Giriş Yap / Kayıt Ol
            </button>
          )}
        </nav>
      </header>

      {/* AUTHENTICATION (GİRİŞ YAP / KAYIT OL) MODAL */}
      {isAuthOpen && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(15, 23, 42, 0.65)',
          backdropFilter: 'blur(6px)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 2000
        }}>
          <div style={{
            backgroundColor: '#ffffff',
            borderRadius: '24px',
            width: '100%',
            maxWidth: '440px',
            padding: '32px',
            boxShadow: '0 25px 50px -12px rgba(0,0,0,0.25)',
            position: 'relative'
          }}>
            <button
              onClick={() => setIsAuthOpen(false)}
              style={{ position: 'absolute', top: '20px', right: '20px', border: 'none', background: 'transparent', cursor: 'pointer', color: '#64748b' }}
            >
              <X size={20} />
            </button>

            {/* TAB SEÇİMİ (GİRİŞ / KAYIT) */}
            <div style={{ display: 'flex', backgroundColor: '#f1f5f9', padding: '4px', borderRadius: '14px', marginBottom: '24px' }}>
              <button
                type="button"
                onClick={() => { setAuthTab('login'); setAuthError(''); }}
                style={{
                  flex: 1,
                  padding: '10px',
                  borderRadius: '10px',
                  border: 'none',
                  background: authTab === 'login' ? '#ffffff' : 'transparent',
                  color: authTab === 'login' ? '#2563eb' : '#64748b',
                  fontWeight: '700',
                  fontSize: '14px',
                  cursor: 'pointer',
                  boxShadow: authTab === 'login' ? '0 2px 8px rgba(0,0,0,0.06)' : 'none'
                }}
              >
                Giriş Yap
              </button>
              <button
                type="button"
                onClick={() => { setAuthTab('register'); setAuthError(''); }}
                style={{
                  flex: 1,
                  padding: '10px',
                  borderRadius: '10px',
                  border: 'none',
                  background: authTab === 'register' ? '#ffffff' : 'transparent',
                  color: authTab === 'register' ? '#2563eb' : '#64748b',
                  fontWeight: '700',
                  fontSize: '14px',
                  cursor: 'pointer',
                  boxShadow: authTab === 'register' ? '0 2px 8px rgba(0,0,0,0.06)' : 'none'
                }}
              >
                Kayıt Ol
              </button>
            </div>

            <div style={{ textAlign: 'center', marginBottom: '20px' }}>
              <h3 style={{ margin: '0 0 6px 0', fontSize: '22px', fontWeight: '800', color: '#0f172a' }}>
                {authTab === 'login' ? 'SkyWings Hesabınıza Giriş Yapın' : 'Yeni Hesabınızı Oluşturun'}
              </h3>
              <p style={{ margin: 0, fontSize: '13px', color: '#64748b' }}>
                {authTab === 'login' ? 'Uçuşlarınızı yönetmek için e-postanızla giriş yapın.' : 'Ayrıcalıklı uçuş fırsatlarından yararlanmak için kaydolun.'}
              </p>
            </div>

            {/* HATA MESAJI */}
            {authError && (
              <div style={{ backgroundColor: '#fef2f2', color: '#b91c1c', padding: '12px', borderRadius: '12px', marginBottom: '16px', fontSize: '13px', border: '1px solid #fecaca', fontWeight: '600', textAlign: 'center' }}>
                {authError}
              </div>
            )}

            <form onSubmit={handleAuthSubmit} style={{ display: 'grid', gap: '16px' }}>
              {authTab === 'register' && (
                <div>
                  <label style={{ display: 'block', fontSize: '11px', fontWeight: '800', color: '#475569', marginBottom: '6px', letterSpacing: '0.5px' }}>AD SOYAD</label>
                  <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                    <User size={16} color="#94a3b8" style={{ position: 'absolute', left: '14px' }} />
                    <input
                      type="text"
                      required
                      placeholder="Ad ve Soyad"
                      value={authName}
                      onChange={(e) => setAuthName(e.target.value)}
                      style={{ width: '100%', padding: '12px 12px 12px 40px', borderRadius: '12px', border: '1px solid #cbd5e1', fontSize: '14px', outline: 'none', backgroundColor: '#f8fafc' }}
                    />
                  </div>
                </div>
              )}

              <div>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: '800', color: '#475569', marginBottom: '6px', letterSpacing: '0.5px' }}>E-POSTA ADRESİ</label>
                <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                  <Mail size={16} color="#94a3b8" style={{ position: 'absolute', left: '14px' }} />
                  <input
                    type="email"
                    required
                    placeholder="ornek@email.com"
                    value={authEmail}
                    onChange={(e) => setAuthEmail(e.target.value)}
                    style={{ width: '100%', padding: '12px 12px 12px 40px', borderRadius: '12px', border: '1px solid #cbd5e1', fontSize: '14px', outline: 'none', backgroundColor: '#f8fafc' }}
                  />
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: '800', color: '#475569', marginBottom: '6px', letterSpacing: '0.5px' }}>ŞİFRE</label>
                <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                  <Lock size={16} color="#94a3b8" style={{ position: 'absolute', left: '14px' }} />
                  <input
                    type="password"
                    required
                    placeholder="En az 6 karakter"
                    value={authPassword}
                    onChange={(e) => setAuthPassword(e.target.value)}
                    style={{ width: '100%', padding: '12px 12px 12px 40px', borderRadius: '12px', border: '1px solid #cbd5e1', fontSize: '14px', outline: 'none', backgroundColor: '#f8fafc' }}
                  />
                </div>
              </div>

              <button
                type="submit"
                style={{ backgroundColor: '#2563eb', color: 'white', border: 'none', padding: '14px', borderRadius: '12px', fontWeight: '700', fontSize: '15px', cursor: 'pointer', marginTop: '6px', boxShadow: '0 8px 16px rgba(37,99,235,0.25)' }}
              >
                {authTab === 'login' ? 'Giriş Yap' : 'Kayıt Ol ve Başla'}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* 1. UÇUŞ ARAMA SEKMESİ */}
      {activeTab === 'search' && (
        <>
          {/* BANNER */}
          <div style={{
            width: '100%',
            background: 'linear-gradient(to bottom, rgba(15, 23, 42, 0.35), rgba(15, 23, 42, 0.75)), url("https://images.unsplash.com/photo-1436491865332-7a61a109cc05?q=80&w=1920&auto=format&fit=crop")',
            backgroundSize: 'cover',
            backgroundPosition: 'right center',
            padding: '100px 40px 170px 40px',
            color: 'white'
          }}>
            <div style={{ maxWidth: '1240px', margin: '0 auto', textAlign: 'center' }}>
              <h1 style={{ fontSize: '44px', fontWeight: '800', margin: '0 0 16px 0', textShadow: '0 4px 20px rgba(0,0,0,0.5)', letterSpacing: '-0.5px' }}>Gökyüzünde Ayrıcalıklı Yolculuk</h1>
              <p style={{ fontSize: '18px', color: '#e2e8f0', margin: '0 auto', maxWidth: '600px', textShadow: '0 2px 8px rgba(0,0,0,0.5)' }}>Dünyanın 120+ noktasına en güvenli ve en uygun fiyatlı seferleri keşfedin.</p>
            </div>
          </div>

          <main style={{ maxWidth: '1240px', margin: '-100px auto 60px auto', padding: '0 24px', position: 'relative', zIndex: 10 }}>
            {bookingSummary ? (
              <div style={{ backgroundColor: '#ffffff', borderRadius: '24px', boxShadow: '0 20px 40px rgba(0,0,0,0.08)', overflow: 'hidden', border: '1px solid #e2e8f0', maxWidth: '800px', margin: '0 auto' }}>
                <div style={{ backgroundColor: '#0f172a', color: 'white', padding: '32px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                    <CheckCircle2 size={32} color="#10b981" />
                    <div>
                      <h2 style={{ margin: 0, fontSize: '22px', fontWeight: '700' }}>Rezervasyon Onaylandı</h2>
                      <span style={{ fontSize: '13px', color: '#94a3b8' }}>Elektronik Biniş Kartınız Başarıyla Üretildi</span>
                    </div>
                  </div>
                  <div style={{ backgroundColor: 'rgba(255,255,255,0.1)', padding: '10px 20px', borderRadius: '12px', textAlign: 'right' }}>
                    <span style={{ fontSize: '10px', color: '#94a3b8', display: 'block', letterSpacing: '1px' }}>PNR KODU</span>
                    <strong style={{ fontSize: '20px', color: '#60a5fa', letterSpacing: '2px' }}>{bookingSummary.pnr}</strong>
                  </div>
                </div>

                <div style={{ padding: '36px', backgroundColor: '#ffffff' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '24px', paddingBottom: '28px', borderBottom: '1px solid #f1f5f9' }}>
                    <div>
                      <span style={{ fontSize: '11px', color: '#64748b', display: 'block', fontWeight: '600' }}>YOLCU</span>
                      <strong style={{ fontSize: '16px', color: '#1e293b' }}>{bookingSummary.passengerName}</strong>
                    </div>
                    <div>
                      <span style={{ fontSize: '11px', color: '#64748b', display: 'block', fontWeight: '600' }}>KİMLİK NO</span>
                      <strong style={{ fontSize: '16px', color: '#1e293b' }}>{bookingSummary.passengerIdentity}</strong>
                    </div>
                    <div>
                      <span style={{ fontSize: '11px', color: '#64748b', display: 'block', fontWeight: '600' }}>UÇUŞ KODU</span>
                      <strong style={{ fontSize: '16px', color: '#2563eb' }}>{bookingSummary.flightNumber}</strong>
                    </div>
                    <div>
                      <span style={{ fontSize: '11px', color: '#64748b', display: 'block', fontWeight: '600' }}>KOLTUK</span>
                      <strong style={{ fontSize: '16px', color: '#10b981' }}>{bookingSummary.seat}</strong>
                    </div>
                  </div>

                  <div style={{ padding: '28px 0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <span style={{ fontSize: '12px', color: '#64748b', fontWeight: '600' }}>Parkur</span>
                      <span style={{ fontSize: '20px', fontWeight: '700', color: '#1e293b' }}>{bookingSummary.origin} ➔ {bookingSummary.destination}</span>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <span style={{ fontSize: '12px', color: '#64748b', fontWeight: '600' }}>Tarih / Saat</span>
                      <span style={{ fontSize: '16px', fontWeight: '600', color: '#1e293b' }}>{new Date(bookingSummary.departureTime).toLocaleString('tr-TR')}</span>
                    </div>
                  </div>

                  <div style={{ backgroundColor: '#f8fafc', padding: '24px', borderRadius: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', border: '1px solid #e2e8f0' }}>
                    <div>
                      <span style={{ fontSize: '12px', color: '#64748b', fontWeight: '600' }}>Ödenen Toplam Tutar</span>
                      <div style={{ fontSize: '26px', fontWeight: '800', color: '#1e293b' }}>{bookingSummary.price} <span style={{ fontSize: '15px', fontWeight: '500' }}>TL</span></div>
                    </div>
                    
                    <button 
                      onClick={() => {
                        setBookingSummary(null);
                        setSelectedFlight(null);
                        setChosenSeat('');
                        setPassengerName('');
                        setPassengerIdentity('');
                      }}
                      style={{ backgroundColor: '#2563eb', color: 'white', border: 'none', padding: '14px 28px', borderRadius: '12px', fontWeight: '600', cursor: 'pointer' }}
                    >
                      Yeni Arama Yap
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <>
                {/* UÇUŞ ARAMA BAR-I */}
                <div style={{ 
                  backgroundColor: 'rgba(255, 255, 255, 0.95)', 
                  backdropFilter: 'blur(16px)',
                  padding: '28px 32px', 
                  borderRadius: '24px', 
                  boxShadow: '0 25px 50px -12px rgba(15, 23, 42, 0.15), 0 0 0 1px rgba(255, 255, 255, 0.6) inset', 
                  marginBottom: '40px', 
                  border: '1px solid #e2e8f0' 
                }}>
                  
                  {/* SEFER TİPİ BUTONLARI */}
                  <div style={{ display: 'inline-flex', gap: '4px', backgroundColor: '#f1f5f9', padding: '4px', borderRadius: '14px', marginBottom: '24px' }}>
                    <button
                      type="button"
                      onClick={() => setTripType('oneWay')}
                      style={{
                        padding: '8px 20px',
                        borderRadius: '10px',
                        border: 'none',
                        background: tripType === 'oneWay' ? '#ffffff' : 'transparent',
                        color: tripType === 'oneWay' ? '#2563eb' : '#64748b',
                        fontWeight: '700',
                        fontSize: '13px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        boxShadow: tripType === 'oneWay' ? '0 2px 8px rgba(0,0,0,0.06)' : 'none',
                        transition: 'all 0.2s ease'
                      }}
                    >
                      <Plane size={15} /> Tek Yön
                    </button>
                    <button
                      type="button"
                      onClick={() => setTripType('roundTrip')}
                      style={{
                        padding: '8px 20px',
                        borderRadius: '10px',
                        border: 'none',
                        background: tripType === 'roundTrip' ? '#ffffff' : 'transparent',
                        color: tripType === 'roundTrip' ? '#2563eb' : '#64748b',
                        fontWeight: '700',
                        fontSize: '13px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        boxShadow: tripType === 'roundTrip' ? '0 2px 8px rgba(0,0,0,0.06)' : 'none',
                        transition: 'all 0.2s ease'
                      }}
                    >
                      <ArrowRightLeft size={15} /> Gidiş - Dönüş
                    </button>
                  </div>

                  {/* ARAMA FORM ALANLARI */}
                  <form onSubmit={handleSearch} style={{ display: 'grid', gridTemplateColumns: tripType === 'roundTrip' ? 'repeat(5, 1fr)' : 'repeat(4, 1fr)', gap: '16px', alignItems: 'center' }}>
                    
                    {/* KALKIŞ */}
                    <div style={{ backgroundColor: '#f8fafc', padding: '12px 16px', borderRadius: '16px', border: '1px solid #e2e8f0' }}>
                      <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', fontWeight: '800', color: '#94a3b8', letterSpacing: '0.5px', marginBottom: '4px' }}>
                        <MapPin size={13} color="#2563eb" /> KALKIŞ NOKTASI
                      </label>
                      <select value={origin} onChange={(e) => setOrigin(e.target.value)} style={{ width: '100%', border: 'none', backgroundColor: 'transparent', fontSize: '14px', color: '#0f172a', fontWeight: '700', outline: 'none', cursor: 'pointer', padding: 0 }}>
                        <option value="">Tüm Havalimanları</option>
                        {mockAirports.map(a => (
                          <option key={a.id} value={a.code}>{a.city} - {a.name} ({a.code})</option>
                        ))}
                      </select>
                    </div>

                    {/* VARIŞ */}
                    <div style={{ backgroundColor: '#f8fafc', padding: '12px 16px', borderRadius: '16px', border: '1px solid #e2e8f0' }}>
                      <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', fontWeight: '800', color: '#94a3b8', letterSpacing: '0.5px', marginBottom: '4px' }}>
                        <MapPin size={13} color="#10b981" /> VARIŞ NOKTASI
                      </label>
                      <select value={destination} onChange={(e) => setDestination(e.target.value)} style={{ width: '100%', border: 'none', backgroundColor: 'transparent', fontSize: '14px', color: '#0f172a', fontWeight: '700', outline: 'none', cursor: 'pointer', padding: 0 }}>
                        <option value="">Tüm Havalimanları</option>
                        {mockAirports.map(a => (
                          <option key={a.id} value={a.code}>{a.city} - {a.name} ({a.code})</option>
                        ))}
                      </select>
                    </div>

                    {/* GİDİŞ TARİHİ */}
                    <div style={{ backgroundColor: '#f8fafc', padding: '12px 16px', borderRadius: '16px', border: '1px solid #e2e8f0' }}>
                      <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', fontWeight: '800', color: '#94a3b8', letterSpacing: '0.5px', marginBottom: '4px' }}>
                        <Calendar size={13} color="#6366f1" /> GİDİŞ TARİHİ
                      </label>
                      <input type="date" defaultValue="2026-11-15" style={{ width: '100%', border: 'none', backgroundColor: 'transparent', fontSize: '14px', color: '#0f172a', fontWeight: '700', outline: 'none', cursor: 'pointer', padding: 0, fontFamily: 'inherit' }} />
                    </div>

                    {/* DÖNÜŞ TARİHİ */}
                    {tripType === 'roundTrip' && (
                      <div style={{ backgroundColor: '#f8fafc', padding: '12px 16px', borderRadius: '16px', border: '1px solid #e2e8f0' }}>
                        <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', fontWeight: '800', color: '#94a3b8', letterSpacing: '0.5px', marginBottom: '4px' }}>
                          <Calendar size={13} color="#ec4899" /> DÖNÜŞ TARİHİ
                        </label>
                        <input type="date" defaultValue="2026-11-20" style={{ width: '100%', border: 'none', backgroundColor: 'transparent', fontSize: '14px', color: '#0f172a', fontWeight: '700', outline: 'none', cursor: 'pointer', padding: 0, fontFamily: 'inherit' }} />
                      </div>
                    )}

                    {/* ARAMA BUTONU */}
                    <button type="submit" style={{ 
                      background: 'linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)', 
                      color: 'white', 
                      border: 'none', 
                      padding: '16px', 
                      borderRadius: '16px', 
                      fontWeight: '700', 
                      fontSize: '15px',
                      cursor: 'pointer', 
                      display: 'flex', 
                      justify: 'center', 
                      alignItems: 'center', 
                      gap: '8px', 
                      boxShadow: '0 10px 20px -5px rgba(37,99,235,0.4)', 
                      height: '56px'
                    }}>
                      <Search size={18} /> Uçuş Bul
                    </button>
                  </form>
                </div>

                {/* İSTATİSTİK BANDI */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '20px', marginBottom: '40px' }}>
                  {[
                    { icon: Globe, value: '120+', label: 'Direkt Destinasyon' },
                    { icon: Plane, value: '450+', label: 'Günlük Sefer Sayısı' },
                    { icon: Users, value: '5 Milyon+', label: 'Mutlu Yolcu' },
                    { icon: Award, value: '%99.8', label: 'Zamanında Kalkış Oranı' }
                  ].map((stat, idx) => {
                    const StatIcon = stat.icon;
                    return (
                      <div key={idx} style={{ backgroundColor: '#ffffff', padding: '20px', borderRadius: '16px', border: '1px solid #e2e8f0', boxShadow: '0 4px 12px rgba(0,0,0,0.02)', display: 'flex', alignItems: 'center', gap: '16px' }}>
                        <div style={{ backgroundColor: '#eff6ff', padding: '12px', borderRadius: '12px' }}>
                          <StatIcon size={24} color="#2563eb" />
                        </div>
                        <div>
                          <strong style={{ fontSize: '20px', color: '#0f172a', display: 'block', fontWeight: '800' }}>{stat.value}</strong>
                          <span style={{ fontSize: '12px', color: '#64748b', fontWeight: '600' }}>{stat.label}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* UÇUŞ SONUÇLARI */}
                {hasSearched && (
                  <div style={{ marginBottom: '40px' }}>
                    <h3 style={{ fontSize: '20px', fontWeight: '700', marginBottom: '20px', color: '#0f172a' }}>Müsait Seferler</h3>
                    {searchResults.length === 0 ? (
                      <div style={{ backgroundColor: '#ffffff', padding: '40px', borderRadius: '16px', textAlign: 'center', color: '#64748b', border: '1px solid #e2e8f0', fontWeight: '500' }}>Seçtiğiniz kriterlere uygun uçuş bulunamadı.</div>
                    ) : (
                      <div style={{ display: 'grid', gap: '20px' }}>
                        {searchResults.map(flight => {
                          const orig = mockAirports.find(a => a.id === flight.origin_airport_id);
                          const dest = mockAirports.find(a => a.id === flight.destination_airport_id);
                          const isSelected = selectedFlight?.id === flight.id;

                          return (
                            <div key={flight.id} style={{ backgroundColor: '#ffffff', padding: '28px', borderRadius: '20px', border: isSelected ? '2px solid #2563eb' : '1px solid #e2e8f0', boxShadow: '0 4px 12px rgba(0,0,0,0.03)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '24px' }}>
                              <div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '10px' }}>
                                  <span style={{ backgroundColor: '#eff6ff', color: '#2563eb', padding: '6px 12px', borderRadius: '8px', fontSize: '13px', fontWeight: '700' }}>{flight.flight_number}</span>
                                  <span style={{ fontSize: '14px', color: '#64748b', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                    <Calendar size={16} /> {new Date(flight.departure_time).toLocaleString('tr-TR')}
                                  </span>
                                </div>
                                <div style={{ fontSize: '20px', fontWeight: '700', color: '#0f172a', display: 'flex', alignItems: 'center', gap: '12px' }}>
                                  {orig?.city} ({orig?.code}) <Plane size={20} color="#94a3b8" /> {dest?.city} ({dest?.code})
                                </div>
                              </div>

                              <div style={{ display: 'flex', alignItems: 'center', gap: '28px' }}>
                                <div style={{ textAlign: 'right' }}>
                                  <span style={{ fontSize: '24px', fontWeight: '800', color: '#0f172a' }}>{flight.price} TL</span>
                                  <small style={{ display: 'block', color: '#64748b', fontSize: '12px', fontWeight: '600' }}>Tek Yön</small>
                                </div>
                                <button 
                                  onClick={() => {
                                    setSelectedFlight(flight);
                                    setChosenSeat('');
                                    setErrorMessage('');
                                  }}
                                  style={{ backgroundColor: isSelected ? '#1d4ed8' : '#2563eb', color: 'white', border: 'none', padding: '14px 28px', borderRadius: '12px', fontWeight: '600', cursor: 'pointer' }}
                                >
                                  {isSelected ? 'Seçildi' : 'Koltuk Seç'}
                                </button>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}

                {/* KOLTUK VE YOLCU FORMU */}
                {selectedFlight && (
                  <div>
                    <SeatSelection 
                      flight={selectedFlight} 
                      onSeatSelect={(seat) => {
                        setChosenSeat(seat);
                        setErrorMessage('');
                      }} 
                    />

                    {chosenSeat && (
                      <div style={{ backgroundColor: '#ffffff', padding: '36px', borderRadius: '24px', border: '1px solid #e2e8f0', boxShadow: '0 20px 40px rgba(0,0,0,0.04)', marginTop: '40px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '24px' }}>
                          <User size={22} color="#2563eb" />
                          <h3 style={{ margin: 0, fontSize: '20px', fontWeight: '700', color: '#0f172a' }}>Yolcu Detayları</h3>
                        </div>

                        {errorMessage && (
                          <div style={{ backgroundColor: '#fef2f2', color: '#b91c1c', padding: '16px', borderRadius: '12px', marginBottom: '24px', fontSize: '14px', border: '1px solid #fecaca', fontWeight: '600' }}>
                            {errorMessage}
                          </div>
                        )}

                        <form onSubmit={handleBookingSubmit} style={{ display: 'grid', gap: '24px', maxWidth: '600px' }}>
                          <div>
                            <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: '600', color: '#475569' }}>Ad Soyad</label>
                            <input 
                              type="text" 
                              required 
                              value={passengerName} 
                              onChange={(e) => setPassengerName(e.target.value)} 
                              placeholder="Örn: Melike Yılmaz" 
                              style={{ width: '100%', padding: '14px', borderRadius: '12px', border: '1px solid #cbd5e1', fontSize: '14px', fontWeight: '500', color: '#1e293b', backgroundColor: '#ffffff' }} 
                            />
                          </div>

                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '20px' }}>
                            <div>
                              <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: '600', color: '#475569' }}>Belge Tipi</label>
                              <select value={docType} onChange={(e) => { setDocType(e.target.value); setPassengerIdentity(''); }} style={{ width: '100%', padding: '14px', borderRadius: '12px', border: '1px solid #cbd5e1', fontSize: '14px', fontWeight: '500', color: '#1e293b', backgroundColor: '#ffffff' }}>
                                <option value="TC">T.C. Kimlik</option>
                                <option value="PASSPORT">Pasaport</option>
                              </select>
                            </div>
                            <div>
                              <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: '600', color: '#475569' }}>{docType === 'TC' ? 'T.C. Kimlik Numarası' : 'Pasaport Numarası'}</label>
                              <input 
                                type="text" 
                                required 
                                maxLength={docType === 'TC' ? 11 : 9}
                                value={passengerIdentity} 
                                onChange={(e) => setPassengerIdentity(e.target.value)} 
                                placeholder={docType === 'TC' ? '11 Haneli T.C. No' : 'Pasaport Seri No'} 
                                style={{ width: '100%', padding: '14px', borderRadius: '12px', border: '1px solid #cbd5e1', fontSize: '14px', fontWeight: '500', color: '#1e293b', backgroundColor: '#ffffff' }} 
                              />
                            </div>
                          </div>

                          <button type="submit" style={{ backgroundColor: '#10b981', color: 'white', border: 'none', padding: '18px', borderRadius: '14px', fontWeight: '700', fontSize: '16px', cursor: 'pointer', marginTop: '10px' }}>
                            Rezervasyonu Onayla ve Tamamla ({selectedFlight.price} TL)
                          </button>
                        </form>
                      </div>
                    )}
                  </div>
                )}

                {/* YEREL GÖRSELLER İLE POPÜLER ROTALAR */}
                <div style={{ marginTop: '50px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '24px' }}>
                    <Compass size={22} color="#2563eb" />
                    <h3 style={{ margin: 0, fontSize: '20px', fontWeight: '700', color: '#0f172a' }}>Popüler Uçuş Rotaları ve Şehirler</h3>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '24px' }}>
                    {[
                      { 
                        city: 'İstanbul ➔ Ankara', 
                        price: '1.250 TL', 
                        desc: 'Başkente gün içi sık sefer avantajı', 
                        img: '/ankara.jpg'
                      },
                      { 
                        city: 'İstanbul ➔ İzmir', 
                        price: '1.400 TL', 
                        desc: 'Ege’nin kalbine konforlu uçuş', 
                        img: '/izmir.jpg'
                      },
                      { 
                        city: 'İstanbul ➔ Antalya', 
                        price: '1.650 TL', 
                        desc: 'Akdeniz tatiline hızlı başlangıç', 
                        img: '/antalya.jpg'
                      },
                      { 
                        city: 'Ankara ➔ İstanbul', 
                        price: '1.180 TL', 
                        desc: 'Direkt bağlantılı günlük seferler', 
                        img: '/istanbul.jpg'
                      }
                    ].map((route, idx) => (
                      <div key={idx} style={{ backgroundColor: '#ffffff', borderRadius: '20px', overflow: 'hidden', border: '1px solid #e2e8f0', boxShadow: '0 8px 20px rgba(0,0,0,0.04)' }}>
                        <div style={{ height: '160px', width: '100%', backgroundImage: `url(${route.img})`, backgroundSize: 'cover', backgroundPosition: 'center', position: 'relative', backgroundColor: '#e2e8f0' }}>
                          <span style={{ position: 'absolute', bottom: '12px', right: '12px', backgroundColor: '#2563eb', color: 'white', padding: '6px 14px', borderRadius: '12px', fontSize: '14px', fontWeight: '800' }}>
                            {route.price}
                          </span>
                        </div>
                        <div style={{ padding: '20px' }}>
                          <div style={{ fontSize: '16px', fontWeight: '700', color: '#0f172a', marginBottom: '6px' }}>{route.city}</div>
                          <div style={{ fontSize: '13px', color: '#64748b' }}>{route.desc}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* YOLCU DEĞERLENDİRMELERİ */}
                <div style={{ marginTop: '50px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '24px' }}>
                    <Star size={22} color="#f59e0b" fill="#f59e0b" />
                    <h3 style={{ margin: 0, fontSize: '20px', fontWeight: '700', color: '#0f172a' }}>Yolcu Deneyimleri ve Değerlendirmeler</h3>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px' }}>
                    {[
                      { name: 'Ayşe K.', flight: 'İstanbul - İzmir Seferi', text: 'Koltuk seçimi ve online check-in süreci inanılmaz hızlıydı. Zamanında kalkış için teşekkürler.', rating: 5 },
                      { name: 'Mehmet B.', flight: 'Ankara - Antalya Seferi', text: 'Uçak içi ikramlar mükemmeldi. Sistem üzerinden koltuğumu kolayca seçebilmem büyük kolaylık.', rating: 5 },
                      { name: 'Selin T.', flight: 'İstanbul - Ankara Seferi', text: 'Kullanıcı dostu bir biletleme ekranı var. PNR kodum ile biletime saniyeler içinde eriştim.', rating: 5 }
                    ].map((review, idx) => (
                      <div key={idx} style={{ backgroundColor: '#ffffff', padding: '24px', borderRadius: '20px', border: '1px solid #e2e8f0', boxShadow: '0 4px 12px rgba(0,0,0,0.02)' }}>
                        <div style={{ display: 'flex', gap: '4px', marginBottom: '12px' }}>
                          {[...Array(review.rating)].map((_, i) => (
                            <Star key={i} size={16} color="#f59e0b" fill="#f59e0b" />
                          ))}
                        </div>
                        <p style={{ fontSize: '14px', color: '#334155', fontStyle: 'italic', marginBottom: '16px', lineHeight: '1.5' }}>"{review.text}"</p>
                        <div style={{ borderTop: '1px solid #f1f5f9', paddingTop: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ fontSize: '14px', fontWeight: '700', color: '#0f172a' }}>{review.name}</span>
                          <span style={{ fontSize: '12px', color: '#94a3b8' }}>{review.flight}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* HARİTA */}
                <div style={{ marginTop: '50px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
                    <Route size={22} color="#2563eb" />
                    <h3 style={{ margin: 0, fontSize: '20px', fontWeight: '700', color: '#0f172a' }}>Uçuş Rotaları ve Havalimanları Haritası</h3>
                  </div>
                  <div style={{ height: '520px', width: '100%', borderRadius: '24px', overflow: 'hidden', boxShadow: '0 15px 35px rgba(0,0,0,0.06)', border: '1px solid #e2e8f0' }}>
                    <MapContainer center={[39.0, 35.0]} zoom={6} style={{ height: '100%', width: '100%' }}>
                      <TileLayer
                        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                        attribution='&copy; OpenStreetMap'
                      />
                      
                      {mockAirports.map((airport) => (
                        <Marker key={airport.id} position={[airport.latitude, airport.longitude]}>
                          <Popup>
                            <strong>{airport.name} ({airport.code})</strong><br />
                            {airport.city}
                          </Popup>
                        </Marker>
                      ))}

                      {flightRoutes.map(route => (
                        <Polyline 
                          key={route.id} 
                          positions={route.positions} 
                          pathOptions={{ color: '#2563eb', weight: 3, dashArray: '6, 6' }} 
                        />
                      ))}
                    </MapContainer>
                  </div>
                </div>
              </>
            )}
          </main>
        </>
      )}

      {/* PNR SEKMESİ */}
      {activeTab === 'pnr' && (
        <main style={{ maxWidth: '900px', margin: '60px auto', padding: '0 20px' }}>
          <div style={{ backgroundColor: '#ffffff', padding: '48px', borderRadius: '24px', border: '1px solid #e2e8f0', boxShadow: '0 20px 40px rgba(0,0,0,0.05)' }}>
            <h2 style={{ margin: '0 0 10px 0', fontSize: '26px', fontWeight: '800', color: '#0f172a' }}>PNR Sorgulama</h2>
            <p style={{ color: '#64748b', fontSize: '15px', marginBottom: '32px' }}>Biletinize ait 6 haneli PNR kodunu girerek uçuş detaylarınızı anında görüntüleyebilirsiniz.</p>

            <form onSubmit={handlePnrSearch} style={{ display: 'flex', gap: '16px', marginBottom: '32px' }}>
              <input 
                type="text" 
                required
                placeholder="Örn: X7K9L2"
                value={searchPnr}
                onChange={(e) => setSearchPnr(e.target.value)}
                style={{ flex: 1, padding: '16px', borderRadius: '14px', border: '1px solid #cbd5e1', fontSize: '16px', textTransform: 'uppercase', letterSpacing: '2px', fontWeight: '700', color: '#1e293b', backgroundColor: '#ffffff' }}
              />
              <button type="submit" style={{ backgroundColor: '#2563eb', color: 'white', border: 'none', padding: '0 32px', borderRadius: '14px', fontWeight: '700', fontSize: '15px', cursor: 'pointer' }}>
                Sorgula
              </button>
            </form>

            {pnrResult === 'NOT_FOUND' && (
              <div style={{ backgroundColor: '#fef2f2', color: '#b91c1c', padding: '18px', borderRadius: '14px', border: '1px solid #fecaca', fontWeight: '600' }}>
                Girdiğiniz PNR koduna ait aktif bir rezervasyon bulunamadı.
              </div>
            )}

            {pnrResult && pnrResult !== 'NOT_FOUND' && (
              <div style={{ backgroundColor: '#f8fafc', padding: '28px', borderRadius: '18px', border: '1px solid #e2e8f0' }}>
                <h4 style={{ margin: '0 0 18px 0', color: '#2563eb', fontSize: '18px', fontWeight: '700' }}>Rezervasyon Bilgileriniz</h4>
                <div style={{ display: 'grid', gap: '12px', fontSize: '15px', color: '#1e293b' }}>
                  <p style={{ margin: 0 }}><strong>Yolcu Ad Soyad:</strong> {pnrResult.passengerName}</p>
                  <p style={{ margin: 0 }}><strong>Kimlik No:</strong> {pnrResult.passengerIdentity}</p>
                  <p style={{ margin: 0 }}><strong>Uçuş Seferi:</strong> {pnrResult.flightNumber} ({pnrResult.origin} ➔ {pnrResult.destination})</p>
                  <p style={{ margin: 0 }}><strong>Koltuk Numarası:</strong> <span style={{ color: '#10b981', fontWeight: '700' }}>{pnrResult.seat}</span></p>
                  <p style={{ margin: 0 }}><strong>Tutar:</strong> {pnrResult.price} TL</p>
                </div>
              </div>
            )}
          </div>
        </main>
      )}

      {/* CHECK-IN SEKMESİ */}
      {activeTab === 'checkin' && (
        <main style={{ maxWidth: '900px', margin: '60px auto', padding: '0 20px' }}>
          <div style={{ backgroundColor: '#ffffff', padding: '48px', borderRadius: '24px', border: '1px solid #e2e8f0', boxShadow: '0 20px 40px rgba(0,0,0,0.05)', textAlign: 'center' }}>
            <CheckCircle2 size={56} color="#2563eb" style={{ marginBottom: '20px' }} />
            <h2 style={{ margin: '0 0 14px 0', fontSize: '28px', fontWeight: '800', color: '#0f172a' }}>Online Check-in Portalı</h2>
            <p style={{ color: '#475569', fontSize: '16px', lineHeight: '1.6', marginBottom: '32px' }}>Uçuşunuza 24 saat kala online check-in yapabilir, biniş kartınızı mobil cihazınıza indirebilirsiniz.</p>
            <div style={{ backgroundColor: '#eff6ff', padding: '24px', borderRadius: '18px', color: '#1e40af', border: '1px solid #bfdbfe', fontSize: '15px', fontWeight: '600' }}>
              Bilet satın alma adımını tamamladıktan sonra size verilen 6 haneli PNR kodu ile uçuşunuza check-in yapabilirsiniz.
            </div>
          </div>
        </main>
      )}

      {/* DESTEK SEKMESİ */}
      {activeTab === 'support' && (
        <main style={{ maxWidth: '900px', margin: '60px auto', padding: '0 20px' }}>
          <div style={{ backgroundColor: '#ffffff', padding: '48px', borderRadius: '24px', border: '1px solid #e2e8f0', boxShadow: '0 20px 40px rgba(0,0,0,0.05)' }}>
            <h2 style={{ margin: '0 0 28px 0', fontSize: '28px', fontWeight: '800', color: '#0f172a' }}>Müşteri Destek & İletişim</h2>
            <div style={{ display: 'grid', gap: '24px' }}>
              <div style={{ backgroundColor: '#f8fafc', padding: '24px', borderRadius: '18px', border: '1px solid #e2e8f0', display: 'flex', alignItems: 'center', gap: '20px' }}>
                <PhoneCall color="#2563eb" size={28} />
                <div>
                  <h4 style={{ margin: 0, fontSize: '18px', fontWeight: '700', color: '#0f172a' }}>7/24 Çağrı Merkezi</h4>
                  <p style={{ margin: '4px 0 0 0', color: '#64748b', fontSize: '15px' }}>+90 850 123 45 67 — Kesintisiz Müşteri Hizmetleri</p>
                </div>
              </div>
              <div style={{ backgroundColor: '#f8fafc', padding: '24px', borderRadius: '18px', border: '1px solid #e2e8f0', display: 'flex', alignItems: 'center', gap: '20px' }}>
                <HelpCircle color="#2563eb" size={28} />
                <div>
                  <h4 style={{ margin: 0, fontSize: '18px', fontWeight: '700', color: '#0f172a' }}>Sıkça Sorulan Sorular</h4>
                  <p style={{ margin: '4px 0 0 0', color: '#64748b', fontSize: '15px' }}>Bilet değişikliği, bagaj hakları ve rezervasyon kuralları.</p>
                </div>
              </div>
            </div>
          </div>
        </main>
      )}

      {/* FOOTER */}
      <footer style={{ backgroundColor: '#0f172a', color: '#94a3b8', padding: '60px 40px 30px 40px', marginTop: '80px', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
        <div style={{ maxWidth: '1240px', margin: '0 auto', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '40px', paddingBottom: '40px', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'white', marginBottom: '16px' }}>
              <Plane size={20} color="#60a5fa" />
              <span style={{ fontWeight: '800', fontSize: '18px' }}>SkyWings</span>
            </div>
            <p style={{ fontSize: '13px', lineHeight: '1.6' }}>Güvenli ve konforlu uçuş deneyimi sunan global havalimanı rezervasyon platformu.</p>
          </div>
          <div>
            <h4 style={{ color: 'white', fontSize: '15px', marginBottom: '16px' }}>Hızlı Bağlantılar</h4>
            <div style={{ display: 'grid', gap: '10px', fontSize: '13px' }}>
              <span>Uçuş Seferleri</span>
              <span>Online Check-in</span>
              <span>PNR Sorgulama</span>
            </div>
          </div>
          <div>
            <h4 style={{ color: 'white', fontSize: '15px', marginBottom: '16px' }}>Yasal & Güvenlik</h4>
            <div style={{ display: 'grid', gap: '10px', fontSize: '13px' }}>
              <span>Gizlilik Politikası</span>
              <span>Kullanım Koşulları</span>
              <span>KVKK Aydınlatma Metni</span>
            </div>
          </div>
          <div>
            <h4 style={{ color: 'white', fontSize: '15px', marginBottom: '16px' }}>Güvenli Ödeme</h4>
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
              <ShieldCheck color="#10b981" size={28} />
              <span style={{ fontSize: '12px' }}>256-Bit SSL Şifreleme ile %100 Güvenli Ödeme Altyapısı</span>
            </div>
          </div>
        </div>
        <div style={{ maxWidth: '1240px', margin: '20px auto 0 auto', textAlign: 'center', fontSize: '12px', color: '#64748b' }}>
          © 2026 SkyWings Airlines. Tüm hakları saklıdır.
        </div>
      </footer>
    </div>
  );
}