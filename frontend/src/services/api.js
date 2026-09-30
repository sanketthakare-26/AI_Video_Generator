/**
 * Centralized API Service for AI Video Generator
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Standardized fetch wrapper with comprehensive error handling and optional timeout.
 */
async function request(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const defaultHeaders = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };

  const { timeoutMs = 600000, ...fetchOptions } = options;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  const config = {
    ...fetchOptions,
    signal: fetchOptions.signal || controller.signal,
    headers: {
      ...defaultHeaders,
      ...fetchOptions.headers,
    },
  };

  try {
    const response = await fetch(url, config);
    clearTimeout(timer);

    let data;
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      data = await response.json();
    } else {
      const text = await response.text();
      data = { message: text };
    }

    if (!response.ok) {
      const errorMessage = data?.message || data?.detail || `Request failed with status ${response.status}`;
      throw new Error(errorMessage);
    }

    return data;
  } catch (error) {
    clearTimeout(timer);
    if (error.name === 'AbortError') {
      throw new Error('Request timed out.');
    }
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      throw new Error('Unable to connect to the backend server. Please make sure the FastAPI backend is running on port 8000.');
    }
    throw error;
  }
}

/**
 * Check backend health status with a fast 5s timeout
 */
export async function checkHealth() {
  return request('/api/health', { timeoutMs: 5000 });
}

/**
 * Submit video generation request (foundation endpoint)
 */
export async function generateVideo(payload) {
  return request('/api/generate', {
    method: 'POST',
    body: JSON.stringify(payload),
    timeoutMs: 300000, // 5 min
  });
}
