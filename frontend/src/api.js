import axios from 'axios';

// Backend sunucunun adresi (Burcu sunucuyu başlattığında port numarasını buraya yazacaksınız, örn: 5000 veya 8000)
const API_BASE_URL = 'http://localhost:5000/api';

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

// 5. PNR ile Bilet Sorgula
export const getBookingByPnr = async (pnr) => {
  try {
    const response = await api.get(`/bookings/pnr/${pnr}`);
    return response.data;
  } catch (error) {
    console.error('PNR sorgulama hatası:', error);
    throw error;
  }
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