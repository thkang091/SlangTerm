import axios from 'axios';

// For development, use your local IP address instead of localhost
const API_URL = 'http://192.168.1.X:8000'; // Replace with your computer's IP

// Types
export interface SlangTerm {
  id: number;
  term: string;
  meaning: string;
  examples?: string[];
  tags?: string[];
  similar_terms?: {
    id: number;
    term: string;
    similarity: number;
  }[];
}

// Create API client
const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000, // 10 second timeout
});

// Add request/response interceptors
apiClient.interceptors.request.use(
  (config) => {
    console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('[API Request Error]', error);
    return Promise.reject(error);
  }
);

apiClient.interceptors.response.use(
  (response) => {
    console.log(`[API Response] Status: ${response.status} from ${response.config.url}`);
    return response;
  },
  (error) => {
    if (error.response) {
      console.error(`[API Error] Status: ${error.response.status}`, error.response.data);
    } else if (error.request) {
      console.error('[API Error] No response received', error.request);
    } else {
      console.error('[API Error] Request setup error', error.message);
    }
    return Promise.reject(error);
  }
);

// API functions
export const searchSlang = async (query: string): Promise<SlangTerm[]> => {
  try {
    const response = await apiClient.get(`/search?q=${encodeURIComponent(query)}`);
    return response.data.results || [];
  } catch (error) {
    console.error('Search error:', error);
    throw error;
  }
};

export const getSlangDetails = async (id: number): Promise<SlangTerm> => {
  try {
    const response = await apiClient.get(`/slang/${id}`);
    return response.data;
  } catch (error) {
    console.error('Get slang details error:', error);
    throw error;
  }
};

export const submitNewSlang = async (slangData: Omit<SlangTerm, 'id'>): Promise<SlangTerm> => {
  try {
    const response = await apiClient.post('/slang', slangData);
    return response.data;
  } catch (error) {
    console.error('Submit slang error:', error);
    throw error;
  }
};

// Add health check to test the API connection
export const checkApiHealth = async (): Promise<boolean> => {
  try {
    const response = await apiClient.get('/health');
    return response.data.status === 'healthy';
  } catch (error) {
    console.error('API health check failed:', error);
    return false;
  }
};