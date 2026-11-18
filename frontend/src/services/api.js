import axios from 'axios';
import { getToken, removeToken } from '../utils/auth';

// Normalize the API base URL to always route correctly to /api/v1 endpoints
const rawUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const baseURL = rawUrl.endsWith('/api/v1') 
    ? rawUrl 
    : `${rawUrl.replace(/\/+$/, '')}/api/v1`;

const api = axios.create({
    baseURL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Request Interceptor: Attach the bearer token automatically
api.interceptors.request.use(
    (config) => {
        const token = getToken();
        if (token) {
            config.headers['Authorization'] = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// Response Interceptor: Handle 401 Unauthorized cleanly without refreshing auth pages
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response && error.response.status === 401) {
            removeToken();
            const currentPath = window.location.pathname;
            if (currentPath !== '/login' && currentPath !== '/register') {
                window.location.href = '/login'; 
            }
        }
        return Promise.reject(error);
    }
);

export default api;