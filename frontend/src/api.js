import axios from 'axios';

// Backend sunucunun adresi (backend: `python -m backend`, varsayılan port 5000)
const API_BASE_URL = 'http://localhost:5000/api';

// Backend hataları {"detail": {"code": "...", "message": "..."}} biçiminde döner.
// Ekranda gösterilecek Türkçe mesajı çıkarır; sunucuya ulaşılamazsa ona göre mesaj verir.
export const getErrorMessage = (error, fallback = 'Beklenmeyen bir hata oluştu.') => {
  if (!error?.response) {
    return 'Sunucuya ulaşılamadı. Backend çalışıyor mu? (python -m backend)';
  }
  return error.response.data?.detail?.message || fallback;
};

export const getErrorCode = (error) => error?.response?.data?.detail?.code;

// Giriş sistemi gelene kadar koltuk kilitleri bu tarayıcı sekmesine ait bir oturum kimliğiyle tutulur.
export const getSessionId = () => {
  let sessionId = sessionStorage.getItem('seatSessionId');
  if (!sessionId) {
    sessionId = crypto.randomUUID();
    sessionStorage.setItem('seatSessionId', sessionId);
  }
  return sessionId;
};

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 1. Havalimanlarını Getir
export const getAirports = async () => {
  try {
    const response = await api.get('/airports');
    return response.data;
  } catch (error) {
    console.error('Havalimanları çekilemedi:', error);
    throw error;
  }
};

// 2. Uçuşları Ara (Kalkış, Varış, Tarih)
export const searchFlights = async (origin, destination, date) => {
  try {
    const response = await api.get('/flights', {
      params: { from: origin, to: destination, date }
    });
    return response.data;
  } catch (error) {
    console.error('Uçuşlar aranırken hata oluştu:', error);
    throw error;
  }
};

// 3. Koltuk Durumlarını Getir
export const getSeatsByFlightId = async (flightId) => {
  try {
    const response = await api.get(`/flights/${flightId}/seats`);
    return response.data;
  } catch (error) {
    console.error('Koltuk bilgisi alınamadı:', error);
    throw error;
  }
};

// 4. Rezervasyon Oluştur (Bilet Satın Al)
export const createBooking = async (bookingData) => {
  try {
    const response = await api.post('/bookings', bookingData);
    return response.data;
  } catch (error) {
    console.error('Rezervasyon oluşturulamadı:', error);
    throw error;
  }
};

// 3b. Koltuğu Kilitle (10 dk boyunca bu oturuma ayrılır; aynı oturum tekrar isterse süre uzar)
export const lockSeat = async (seatId, expectedVersion) => {
  const body = { session_id: getSessionId() };
  if (expectedVersion != null) body.expected_version = expectedVersion;
  const response = await api.post(`/seats/${seatId}/lock`, body);
  return response.data;
};

// 3c. Koltuk Kilidini Bırak
export const releaseSeat = async (seatId) => {
  const response = await api.delete(`/seats/${seatId}/lock`, {
    params: { session_id: getSessionId() },
  });
  return response.data;
};

// 5. PNR ile Bilet Sorgula (soyad verilirse PNR ile birlikte kontrol edilir)
export const getBookingByPnr = async (pnr, lastName) => {
  try {
    const params = lastName ? { last_name: lastName } : undefined;
    const response = await api.get(`/bookings/pnr/${encodeURIComponent(pnr)}`, { params });
    return response.data;
  } catch (error) {
    console.error('PNR sorgulama hatası:', error);
    throw error;
  }
};

// 5b. Bilet PDF'inin indirme adresi (doğrudan <a href> ile kullanılır)
export const getTicketPdfUrl = (pnr, lastName) => {
  const query = lastName ? `?last_name=${encodeURIComponent(lastName)}` : '';
  return `${API_BASE_URL}/bookings/pnr/${encodeURIComponent(pnr)}/pdf${query}`;
};

// 6. Kullanıcı Girişi / Kayıt
export const loginUser = async (credentials) => {
  const response = await api.post('/auth/login', credentials);
  return response.data;
};

export const registerUser = async (userData) => {
  const response = await api.post('/auth/register', userData);
  return response.data;
};

export default api;