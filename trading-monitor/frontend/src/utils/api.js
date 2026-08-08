import axios from 'axios';

const getApiUrl = () => {
  return localStorage.getItem('api_url') || import.meta.env.VITE_API_URL || 'http://localhost:8000';
};

const getAuthHeader = () => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    return {
      'Authorization': 'Basic ' + token,
    };
  }
  return {};
};

export const apiClient = axios.create({
  baseURL: getApiUrl(),
  timeout: 10000,
});

// 請求攔截器：添加認證頭
apiClient.interceptors.request.use(
  (config) => {
    const auth = getAuthHeader();
    config.headers = { ...config.headers, ...auth };
    return config;
  },
  (error) => Promise.reject(error)
);

// 響應攔截器：處理401
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token');
      window.location.reload();
    }
    return Promise.reject(error);
  }
);

export default apiClient;
